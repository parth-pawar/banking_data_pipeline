
import sqlite3
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = CAPSTONE_DIR / "database"

GOLD_DB = DATABASE_DIR / "gold.db"
GOLD_SCHEMA = DATABASE_DIR / "gold_schema.sql"


def main():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    schema = GOLD_SCHEMA.read_text(encoding="utf-8")

    with sqlite3.connect(GOLD_DB) as connection:
        connection.executescript(schema)

    print(f"Gold database initialized: {GOLD_DB}")


if __name__ == "__main__":
    main()
