import sqlite3
from pathlib import Path

from .config import PROJECT_ROOT, settings
from .services.auth_service import hash_password


SCHEMA_PATH = PROJECT_ROOT / "schema.sql"
DATABASE_PATH = PROJECT_ROOT / "ecommerce.db"


def initialize_database(database_path: Path = DATABASE_PATH, demo_password: str | None = None) -> int:
    """Rebuild the database from schema.sql and return how many demo users received a password."""
    database = sqlite3.connect(database_path)
    try:
        database.execute("PRAGMA foreign_keys = ON")
        database.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        updated = 0
        if demo_password:
            user_ids = [row[0] for row in database.execute("SELECT id FROM users WHERE password_hash IS NULL")]
            for user_id in user_ids:
                database.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(demo_password), user_id))
            updated = len(user_ids)
        database.commit()
    finally:
        database.close()
    return updated


def main() -> None:
    updated = initialize_database(demo_password=settings.demo_password)
    print(f"Initialized {DATABASE_PATH}")
    if updated:
        print(f"Demo password applied to {updated} seeded users.")
    else:
        print("No demo password set; seeded users cannot sign in. Set BUILDMART_DEMO_PASSWORD in .env and re-run.")


if __name__ == "__main__":
    main()