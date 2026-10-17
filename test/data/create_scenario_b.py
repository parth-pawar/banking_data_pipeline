import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = PROJECT_ROOT / "src" / "operational" / "schema.sql"
TEST_DATABASE = PROJECT_ROOT / "test" / "data" / "scenario_b.db"


def create_test_database():
    if TEST_DATABASE.exists():
        raise FileExistsError(
            f"Test database already exists: {TEST_DATABASE}. "
            "Delete it manually if you want to recreate it."
        )

    schema = SCHEMA_FILE.read_text(encoding="utf-8")

    with sqlite3.connect(TEST_DATABASE) as connection:
        connection.executescript(schema)

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

    print(f"Created test database: {TEST_DATABASE}")
    print("Tables:", [table[0] for table in tables])


if __name__ == "__main__":
    create_test_database()
