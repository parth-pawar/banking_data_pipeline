import sqlite3
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent

SCHEMA_FILE = CAPSTONE_DIR / "database" / "silver_schema.sql"
DB_FILE = CAPSTONE_DIR / "database" / "silver.db"


def initialize_database():
    schema = SCHEMA_FILE.read_text(encoding="utf-8")

    with sqlite3.connect(DB_FILE) as connection:
        connection.execute("DROP TABLE IF EXISTS transaction_exceptions")
        connection.execute("DROP TABLE IF EXISTS silver_transactions")
        connection.execute("DROP TABLE IF EXISTS silver_file_audit")
        connection.executescript(schema)

    print(f"Silver database initialized: {DB_FILE}")

if __name__ == "__main__":
    initialize_database()