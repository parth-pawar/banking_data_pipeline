
import sqlite3
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = CAPSTONE_DIR / "database" / "bronze_schema.sql"
DB_FILE = CAPSTONE_DIR / "database" / "bronze.db"


def initialize_database():
    schema = SCHEMA_FILE.read_text(encoding="utf-8")

    with sqlite3.connect(DB_FILE) as connection:
        connection.executescript(schema)

    print(f"Bronze database initialized: {DB_FILE}")


if __name__ == "__main__":
    initialize_database()
