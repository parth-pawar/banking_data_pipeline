
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from src.spark.load_data import (
    create_spark_session,
    load_accounts,
    load_transactions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = PROJECT_ROOT / "src" / "operational" / "schema.sql"


@pytest.fixture(scope="module")
def spark():
    """Create one Spark session for all tests in the module."""
    spark_session = create_spark_session("BankingSparkTests")

    yield spark_session

    spark_session.stop()


@pytest.fixture
def test_database(tmp_path):
    """Create an isolated temporary SQLite database for testing."""
    database_path = tmp_path / "test_banking.db"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        with SCHEMA_FILE.open("r", encoding="utf-8") as schema_file:
            schema = schema_file.read()

        connection.executescript(schema)

        connection.executemany(
            "INSERT INTO customer VALUES (?, ?, ?, ?)",
            [
                ("C001", "Alice", "alice@example.com", "REGULAR"),
                ("C002", "Bob", "bob@example.com", "PREMIUM"),
            ],
        )

        connection.executemany(
            "INSERT INTO branch VALUES (?, ?, ?, ?)",
            [
                ("BR001", "Test Branch", "Pune", "Maharashtra"),
            ],
        )

        connection.executemany(
            "INSERT INTO account VALUES (?, ?, ?, ?, ?)",
            [
                ("A001", "C001", "BR001", "CHECKING", "ACTIVE"),
                ("A002", "C002", "BR001", "SAVINGS", "ACTIVE"),
            ],
        )

        connection.executemany(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("T001", "A001", "2026-01-01", "CREDIT", 100.0, "USD", "test.csv"),
                ("T002", "A001", "2026-01-02", "DEBIT", 50.0, "USD", "test.csv"),
                ("T003", "A002", "2026-01-03", "CREDIT", 200.0, "USD", "test.csv"),
                ("T004", "A002", "2026-01-04", "DEBIT", 25.0, "USD", "test.csv"),
            ],
        )

        connection.commit()

    return database_path


@pytest.fixture
def banking_data(spark, test_database):
    """Load test data using the project's production loaders."""
    transactions_df = load_transactions(spark, test_database)
    accounts_df = load_accounts(spark, test_database)

    return transactions_df, accounts_df
