
import sqlite3
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = CAPSTONE_DIR / "database" / "bronze_schema.sql"


def main(test_dir):
    test_database_dir = Path(test_dir) / "database"
    test_database_dir.mkdir(parents=True, exist_ok=True)

    test_db = test_database_dir / "bronze.db"
    schema = SCHEMA_FILE.read_text(encoding="utf-8")

    with sqlite3.connect(test_db) as connection:
        connection.executescript(schema)

    print(f"Test Bronze database initialized: {test_db}")


if __name__ == "__main__":
    main(CAPSTONE_DIR / "test" / "late_arrival")
