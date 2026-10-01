import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_analytics_connection():
    connection = sqlite3.connect(
        PROJECT_ROOT / "database" / "analytics.db"
    )
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_fact_rows_reference_valid_dimensions():
    connection = create_analytics_connection()

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
    connection = create_analytics_connection()

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
    connection = create_analytics_connection()

    row = connection.execute(
        """
        SELECT
            b.branch_id,
            COUNT(f.transaction_id) AS transaction_count,
            SUM(f.amount) AS total_amount
        FROM fact_transaction f
        JOIN dim_account a
            ON f.account_id = a.account_id
        JOIN dim_branch b
            ON a.branch_id = b.branch_id
        WHERE b.branch_id = ?
        GROUP BY b.branch_id
        """,
        ("BR003",)
    ).fetchone()

    connection.close()

    assert row == ("BR003", 8, 2450.0)