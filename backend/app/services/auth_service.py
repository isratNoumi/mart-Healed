import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..config import settings
from ..models import User, UserSession

SESSION_COOKIE = "bm_session"
# Absolute lifetime of a session; it can never be extended past this.
SESSION_LIFETIME = timedelta(hours=12)
# Sessions expire after this much inactivity; each authenticated request slides it forward.
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
SECURE_COOKIES = settings.secure_cookies
# Per-account failures after which login attempts for that account are slowed.
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60
# Per-client (IP) throttle so credential spraying across many accounts is limited too.
MAX_FAILED_LOGINS_PER_CLIENT = 20
# Process-wide failed-login volume; used only to add a small delay (no lockout).
MAX_FAILED_LOGINS_GLOBAL = 500
# Per-account failures add an exponentially growing delay (bounded).
LOGIN_DELAY_STEP_SECONDS = 0.25
MAX_LOGIN_DELAY_SECONDS = 4.0
# Per-account "lock" state: once an account accrues this many failures inside the
# window it is flagged, with the flag duration doubling on each successive lock
# (capped). A flagged account gets the maximum per-attempt slowdown; it is never
# hard-blocked, so attackers cannot deny the owner access just by knowing an email.
ACCOUNT_LOCKOUT_THRESHOLD = 10
ACCOUNT_LOCKOUT_BASE_SECONDS = 60
ACCOUNT_LOCKOUT_MAX_SECONDS = 60 * 60
ACCOUNT_LOCKOUT_HISTORY_SECONDS = 24 * 60 * 60
# Registration throttles (account-enumeration oracle / abuse).
MAX_REGISTRATIONS_PER_CLIENT = 20
MAX_DUPLICATE_REGISTRATIONS_PER_CLIENT = 5
REGISTRATION_WINDOW_SECONDS = 15 * 60
# Throttled login attempts are serialized per account (and per client once the
# client is throttled): each attempt reserves the next time slot, so N parallel
# connections get no more guesses per unit time than one. Attempts that would
# have to queue longer than this are rejected with 429 instead of tying up workers.
MAX_LOGIN_QUEUE_WAIT_SECONDS = 30.0

_hasher = PasswordHasher()
# Checked for unknown emails so response time doesn't reveal which accounts exist.
_DUMMY_HASH = _hasher.hash("buildmart-dummy-password")
# In-memory, so limits reset on restart and aren't shared across worker processes.
_failed_logins: dict[str, deque[float]] = defaultdict(deque)
_failed_logins_by_client: dict[str, deque[float]] = defaultdict(deque)
_failed_logins_global: deque[float] = deque()
_registrations_by_client: dict[str, deque[float]] = defaultdict(deque)
_duplicate_registrations_by_client: dict[str, deque[float]] = defaultdict(deque)
# email -> monotonic time the current lock expires
_account_locked_until: dict[str, float] = {}
# email -> count of locks applied recently (drives escalation)
_account_lock_count: dict[str, int] = {}
_account_last_lock: dict[str, float] = {}
# email -> client ids that have successfully authenticated to that account
_trusted_clients: dict[str, set[str]] = defaultdict(set)
# throttle key -> monotonic time at which the next throttled attempt may run
_next_login_slot: dict[str, float] = {}
_throttle_lock = threading.RLock()


def _prune(attempts: deque[float], window: int) -> deque[float]:
    cutoff = time.monotonic() - window
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def reset_rate_limits() -> None:
    _failed_logins.clear()
    _failed_logins_by_client.clear()
    _failed_logins_global.clear()
    _registrations_by_client.clear()
    _duplicate_registrations_by_client.clear()
    _account_locked_until.clear()
    _account_lock_count.clear()
    _account_last_lock.clear()
    _trusted_clients.clear()
    _next_login_slot.clear()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(user: User | None, password: str) -> bool:
    if user is None or not user.password_hash:
        try:
            _hasher.verify(_DUMMY_HASH, password)
        except VerificationError:
            pass
        return False
    try:
        _hasher.verify(user.password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(password)
    return True


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    now = utc_now()
    db.add(UserSession(user_id=user.id, token_hash=_hash_token(token), created_at=now, expires_at=now + SESSION_IDLE_TIMEOUT))
    return token


def get_session_user(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.query(UserSession).filter(UserSession.token_hash == _hash_token(token)).first()
    if session is None:
        return None
    now = utc_now()
    absolute_expiry = session.created_at + SESSION_LIFETIME
    if session.expires_at <= now or absolute_expiry <= now:
        db.delete(session)
        db.commit()
        return None
    # Sliding idle timeout, capped by the absolute lifetime.
    new_expiry = min(now + SESSION_IDLE_TIMEOUT, absolute_expiry)
    if new_expiry - session.expires_at > timedelta(seconds=60):
        session.expires_at = new_expiry
        db.commit()
    return db.get(User, session.user_id)


def delete_session(db: Session, token: str | None) -> None:
    if token:
        db.query(UserSession).filter(UserSession.token_hash == _hash_token(token)).delete()


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_login_rate_limited(email: str, client_id: str | None = None) -> bool:
    """True when the client or the account has exceeded its failure budget.

    Informational only: the login endpoint must NOT reject requests based on
    this (doing so lets anyone lock out any known email, or every user behind a
    shared IP). Use ``login_throttle_delay`` to slow attempts instead.
    """
    if client_id is not None and len(_prune(_failed_logins_by_client[client_id], FAILED_LOGIN_WINDOW_SECONDS)) >= MAX_FAILED_LOGINS_PER_CLIENT:
        return True
    return is_account_locked(email, client_id)


def is_account_locked(email: str, client_id: str | None = None) -> bool:
    """True while the account is in a temporary (escalating) lockout.

    Applied by email regardless of whether the account exists, so it doesn't
    reveal account existence. Applies to all clients; no IP-based exemption.
    """
    key = _normalize_email(email)
    until = _account_locked_until.get(key)
    if until is None:
        return False
    if time.monotonic() >= until:
        _account_locked_until.pop(key, None)
        return False
    # No per-client (IP) exemption: an IP address is not a credential, and in
    # NAT/proxy deployments many users share one, so exempting "trusted" IPs
    # would let an attacker behind the same address bypass the lockout.
    return True


def login_throttle_delay(email: str, client_id: str | None = None) -> float:
    """Seconds to wait before checking credentials for this account.

    Grows with recent failures against the account, with the account's
    escalating lockout state, with failures from the requesting client and with
    global failure volume -- but is always capped. Throttling state never causes
    a request to be rejected outright: the credentials are always evaluated, so
    an attacker who merely knows an email address (or shares an IP address with
    a victim) cannot lock the legitimate owner out of their account.
    """
    delay = 0.0
    account_failures = len(_prune(_failed_logins[_normalize_email(email)], FAILED_LOGIN_WINDOW_SECONDS))
    if account_failures >= MAX_FAILED_LOGINS:
        delay += LOGIN_DELAY_STEP_SECONDS * (2 ** min(account_failures - MAX_FAILED_LOGINS, 8))
    if is_account_locked(email):
        # Account under sustained attack: apply the maximum slowdown.
        delay = MAX_LOGIN_DELAY_SECONDS
    if client_id is not None and len(_prune(_failed_logins_by_client[client_id], FAILED_LOGIN_WINDOW_SECONDS)) >= MAX_FAILED_LOGINS_PER_CLIENT:
        delay += LOGIN_DELAY_STEP_SECONDS * 4
    if len(_prune(_failed_logins_global, FAILED_LOGIN_WINDOW_SECONDS)) >= MAX_FAILED_LOGINS_GLOBAL:
        delay += LOGIN_DELAY_STEP_SECONDS
    return min(delay, MAX_LOGIN_DELAY_SECONDS)


def reserve_login_slot(email: str, client_id: str | None = None) -> float | None:
    """Reserve a serialized time slot for a login attempt.

    Returns the number of seconds the caller must wait before evaluating the
    credentials, or ``None`` if the per-account/per-client queue is already
    saturated (the caller should respond 429). Concurrent attempts against a
    throttled account are spaced ``delay`` seconds apart from each other rather
    than all sleeping in parallel, so parallelism does not multiply throughput.
    """
    with _throttle_lock:
        delay = login_throttle_delay(email, client_id)
        if delay <= 0:
            return 0.0
        now = time.monotonic()
        # Drop stale reservations so the map doesn't grow without bound.
        for stale in [k for k, t in _next_login_slot.items() if t <= now]:
            _next_login_slot.pop(stale, None)
        keys = ["acct:" + _normalize_email(email)]
        if client_id is not None and len(_prune(_failed_logins_by_client[client_id], FAILED_LOGIN_WINDOW_SECONDS)) >= MAX_FAILED_LOGINS_PER_CLIENT:
            keys.append("client:" + client_id)
        start = max([now] + [_next_login_slot.get(k, now) for k in keys])
        run_at = start + delay
        wait = run_at - now
        if wait > MAX_LOGIN_QUEUE_WAIT_SECONDS:
            return None
        for k in keys:
            _next_login_slot[k] = run_at
        return wait


def record_failed_login(email: str, client_id: str | None = None) -> None:
    with _throttle_lock:
        _record_failed_login(email, client_id)


def _record_failed_login(email: str, client_id: str | None = None) -> None:
    now = time.monotonic()
    key = _normalize_email(email)
    attempts = _failed_logins[key]
    attempts.append(now)
    if client_id is not None:
        _failed_logins_by_client[client_id].append(now)
    _failed_logins_global.append(now)
    if len(_prune(attempts, FAILED_LOGIN_WINDOW_SECONDS)) >= ACCOUNT_LOCKOUT_THRESHOLD:
        last = _account_last_lock.get(key)
        if last is None or now - last > ACCOUNT_LOCKOUT_HISTORY_SECONDS:
            _account_lock_count[key] = 0
        count = _account_lock_count.get(key, 0)
        duration = min(ACCOUNT_LOCKOUT_BASE_SECONDS * (2 ** min(count, 16)), ACCOUNT_LOCKOUT_MAX_SECONDS)
        _account_locked_until[key] = now + duration
        _account_lock_count[key] = count + 1
        _account_last_lock[key] = now
        # Start a fresh failure window after locking so each lock escalates.
        attempts.clear()


def is_registration_rate_limited(client_id: str) -> bool:
    # Throttle on total attempts only; a duplicate-specific limit would itself leak
    # (via when the 429 appears) how many submitted emails were already registered.
    return len(_prune(_registrations_by_client[client_id], REGISTRATION_WINDOW_SECONDS)) >= MAX_REGISTRATIONS_PER_CLIENT


def record_registration_attempt(client_id: str, duplicate: bool) -> None:
    now = time.monotonic()
    _registrations_by_client[client_id].append(now)
    if duplicate:
        _duplicate_registrations_by_client[client_id].append(now)


def clear_failed_logins(email: str, client_id: str | None = None) -> None:
    key = _normalize_email(email)
    with _throttle_lock:
        _failed_logins.pop(key, None)
