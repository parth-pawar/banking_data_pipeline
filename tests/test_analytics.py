import sqlite3
from pathlib import Path
from src.analytics import analytics

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_analytics_connection():
    connection = sqlite3.connect(
        PROJECT_ROOT / "database" / "analytics.db"
    )
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_fact_rows_reference_valid_dimensions():
    connection = sqlite3.connect(":memory:")
    analytics.create_analytics_schema(connection)

    connection.execute(
        """
        INSERT INTO dim_account (
            account_id,
            customer_id,
            branch_id,
            account_type,
            account_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        ("A001", "C001", "BR001", "CHECKING", "ACTIVE")
    )

    connection.execute(
        """
        INSERT INTO dim_date (
            date,
            year,
            month,
            day
        )
        VALUES (?, ?, ?, ?)
        """,
        ("2026-09-01", 2026, 9, 1)
    )

    connection.execute(
        """
        INSERT INTO fact_transaction (
            transaction_id,
            customer_id,
            account_id,
            branch_id,
            transaction_date,
            transaction_type,
            amount,
            currency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "T001",
            "C001",
            "A001",
            "BR001",
            "2026-09-01",
            "CREDIT",
            100.0,
            "USD",
        )
    )

    connection.commit()

    invalid_accounts = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_transaction f
        LEFT JOIN dim_account a
            ON f.account_id = a.account_id
        WHERE a.account_id IS NULL
        """
    ).fetchone()[0]

    invalid_dates = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_transaction f
        LEFT JOIN dim_date d
            ON f.transaction_date = d.date
        WHERE d.date IS NULL
        """
    ).fetchone()[0]

    connection.close()

    assert invalid_accounts == 0
    assert invalid_dates == 0


def test_fact_transaction_has_unique_transaction_ids():
    connection = sqlite3.connect(":memory:")
    analytics.create_analytics_schema(connection)

    connection.execute(
        """
        INSERT INTO dim_customer (
            customer_id,
            customer_name,
            email,
            customer_segment
        )
        VALUES (?, ?, ?, ?)
        """,
        ("C001", "Test Customer", "test@example.com", "RETAIL")
    )

    connection.execute(
        """
        INSERT INTO dim_branch (
            branch_id,
            branch_name,
            city,
            state
        )
        VALUES (?, ?, ?, ?)
        """,
        ("BR001", "Test Branch", "Pune", "Maharashtra")
    )

    connection.execute(
        """
        INSERT INTO dim_account (
            account_id,
            customer_id,
            branch_id,
            account_type,
            account_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        ("A001", "C001", "BR001", "CHECKING", "ACTIVE")
    )

    connection.execute(
        """
        INSERT INTO dim_date (
            date,
            year,
            month,
            day
        )
        VALUES (?, ?, ?, ?)
        """,
        ("2026-09-01", 2026, 9, 1)
    )

    connection.execute(
        """
        INSERT INTO fact_transaction (
            transaction_id,
            customer_id,
            account_id,
            branch_id,
            transaction_date,
            transaction_type,
            amount,
            currency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "T001",
            "C001",
            "A001",
            "BR001",
            "2026-09-01",
            "CREDIT",
            100.0,
            "USD",
        )
    )

    connection.execute(
        """
        INSERT INTO fact_transaction (
            transaction_id,
            customer_id,
            account_id,
            branch_id,
            transaction_date,
            transaction_type,
            amount,
            currency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "T002",
            "C001",
            "A001",
            "BR001",
            "2026-09-01",
            "DEBIT",
            50.0,
            "USD",
        )
    )

    connection.commit()

    duplicate_ids = connection.execute(
        """
        SELECT transaction_id
        FROM fact_transaction
        GROUP BY transaction_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()

    connection.close()

    assert duplicate_ids == []



def test_branch_transaction_summary_returns_known_result():
    connection = sqlite3.connect(":memory:")
    analytics.create_analytics_schema(connection)

    connection.execute(
        """
        INSERT INTO dim_customer (
            customer_id,
            customer_name,
            email,
            customer_segment
        )
        VALUES (?, ?, ?, ?)
        """,
        ("C001", "Test Customer", "test@example.com", "RETAIL")
    )

    connection.execute(
        """
        INSERT INTO dim_branch (
            branch_id,
            branch_name,
            city,
            state
        )
        VALUES (?, ?, ?, ?)
        """,
        ("BR003", "Test Lake Branch", "Pune", "Maharashtra")
    )

    connection.execute(
        """
        INSERT INTO dim_account (
            account_id,
            customer_id,
            branch_id,
            account_type,
            account_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        ("A001", "C001", "BR003", "CHECKING", "ACTIVE")
    )

    connection.execute(
        """
        INSERT INTO dim_date (
            date,
            year,
            month,
            day
        )
        VALUES (?, ?, ?, ?)
        """,
        ("2026-09-01", 2026, 9, 1)
    )

    connection.execute(
        """
        INSERT INTO fact_transaction (
            transaction_id,
            customer_id,
            account_id,
            branch_id,
            transaction_date,
            transaction_type,
            amount,
            currency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "T001",
            "C001",
            "A001",
            "BR003",
            "2026-09-01",
            "CREDIT",
            100.0,
            "USD",
        )
    )

    connection.execute(
        """
        INSERT INTO fact_transaction (
            transaction_id,
            customer_id,
            account_id,
            branch_id,
            transaction_date,
            transaction_type,
            amount,
            currency
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "T002",
            "C001",
            "A001",
            "BR003",
            "2026-09-01",
            "DEBIT",
            200.0,
            "USD",
        )
    )

    connection.commit()

    row = connection.execute(
        """
        SELECT
            b.branch_id,
            COUNT(f.transaction_id) AS transaction_count,
            SUM(f.amount) AS total_amount
        FROM fact_transaction f
        JOIN dim_branch b
            ON f.branch_id = b.branch_id
        WHERE b.branch_id = ?
        GROUP BY b.branch_id
        """,
        ("BR003",)
    ).fetchone()

    connection.close()

    assert row == ("BR003", 2, 300.0)