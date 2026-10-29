import re
import secrets
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..clock import today

PROVIDER = "MOCK_GATEWAY"
SUPPORTED_BRANDS_MESSAGE = "We accept Visa, Mastercard, American Express and Discover."

# Outcome is chosen by the card's last 4 digits; any other card succeeds.
TEST_CARD_OUTCOMES = {
    "0002": "DECLINED",
    "9995": "INSUFFICIENT_FUNDS",
    "0127": "INVALID_CARD",
    "0069": "EXPIRED_CARD",
    "0119": "TIMEOUT",
    "0259": "GATEWAY_ERROR",
    "0341": "RETRY_SUCCESS",
}

# outcome: (attempt status, payment status, failure code, customer message, issues a transaction ID)
_FAILURES = {
    "DECLINED": ("DECLINED", "DECLINED", "CARD_DECLINED", "Your card was declined. Please try another payment method.", True),
    "INSUFFICIENT_FUNDS": ("DECLINED", "DECLINED", "INSUFFICIENT_FUNDS", "Your card has insufficient funds. Please use another payment method.", True),
    "INVALID_CARD": ("DECLINED", "DECLINED", "INVALID_CARD", "Your card details could not be verified. Please check them or use another card.", True),
    "EXPIRED_CARD": ("DECLINED", "DECLINED", "EXPIRED_CARD", "Your card issuer reports this card as expired. Please use another card.", True),
    "TIMEOUT": ("TIMEOUT", "FAILED", "TIMEOUT", "The payment timed out and you were not charged. Please try again.", False),
    "GATEWAY_ERROR": ("FAILED", "FAILED", "GATEWAY_ERROR", "The payment service is temporarily unavailable. Please try again shortly.", False),
}


@dataclass(frozen=True)
class CardCheck:
    brand: str | None
    last4: str | None
    errors: dict[str, str]

    @property
    def valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class GatewayResult:
    succeeded: bool
    attempt_status: str
    payment_status: str
    transaction_id: str | None
    failure_code: str | None = None
    failure_message: str | None = None


def luhn_valid(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def detect_brand(digits: str) -> str | None:
    if digits.startswith("4"):
        return "VISA"
    if 51 <= int(digits[:2]) <= 55 or 2221 <= int(digits[:4]) <= 2720:
        return "MASTERCARD"
    if digits[:2] in ("34", "37"):
        return "AMEX"
    if digits.startswith(("6011", "65")) or 644 <= int(digits[:3]) <= 649:
        return "DISCOVER"
    return None


def is_expired(expiry_month: int, expiry_year: int, on: date | None = None) -> bool:
    current = on or today()
    return (expiry_year, expiry_month) < (current.year, current.month)


def check_card(card_number: str, expiry_month: int, expiry_year: int, cvv: str) -> CardCheck:
    errors: dict[str, str] = {}
    digits = re.sub(r"[\s-]", "", card_number)
    brand = last4 = None
    if not digits.isdigit() or not 12 <= len(digits) <= 19 or not luhn_valid(digits):
        errors["card_number"] = "Enter a valid card number."
    else:
        brand = detect_brand(digits)
        last4 = digits[-4:]
        if brand is None:
            errors["card_number"] = SUPPORTED_BRANDS_MESSAGE

    if is_expired(expiry_month, expiry_year):
        errors["expiry"] = "This card has expired."
    elif expiry_year > today().year + 20:
        errors["expiry"] = "Enter a valid expiration date."

    cvv_length = 4 if brand == "AMEX" else 3
    if not (cvv.isdigit() and len(cvv) == cvv_length):
        errors["cvv"] = f"Enter the {cvv_length}-digit security code."
    return CardCheck(brand, last4, errors)


def card_display(brand: str | None, last4: str | None) -> str | None:
    return f"{brand} •••• {last4}" if brand and last4 else None


def _transaction_id() -> str:
    return f"MOCK-TXN-{secrets.token_hex(4).upper()}"


def charge(card_last4: str, amount: Decimal, attempt_number: int) -> GatewayResult:
    """Simulate a card charge. Card numbers never reach this function, only the last 4 digits."""
    if amount <= 0:
        raise ValueError("Charge amount must be positive.")
    outcome = TEST_CARD_OUTCOMES.get(card_last4, "SUCCESS")
    if outcome == "RETRY_SUCCESS":
        outcome = "DECLINED" if attempt_number == 1 else "SUCCESS"
    if outcome == "SUCCESS":
        return GatewayResult(True, "SUCCEEDED", "SUCCEEDED", _transaction_id())
    attempt_status, payment_status, code, message, has_transaction = _FAILURES[outcome]
    return GatewayResult(False, attempt_status, payment_status, _transaction_id() if has_transaction else None, code, message)
