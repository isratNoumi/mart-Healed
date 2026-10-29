from datetime import date, datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today() -> date:
    return date.today()
