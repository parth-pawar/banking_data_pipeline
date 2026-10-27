import sqlite3
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
DATABASE_DIR = TEST_DIR / "database"

SILVER_DB = DATABASE_DIR / "silver.db"
GOLD_DB = DATABASE_DIR / "gold.db"


def test_silver_count():
    with sqlite3.connect(SILVER_DB) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM silver_transactions"
        ).fetchone()[0]

    assert count == 4, f"Expected 4 Silver transactions, got {count}"


def test_gold_totals():
    expected = [
        ("BR001", "2026-09-07", "CREDIT", 1, 250.0),
        ("BR001", "2026-09-07", "DEBIT", 1, 75.0),
        ("BR002", "2026-09-05", "CREDIT", 1, 400.0),
        ("BR002", "2026-09-05", "DEBIT", 1, 125.0),
    ]

    with sqlite3.connect(GOLD_DB) as connection:
        actual = connection.execute(
            """
            SELECT branch_id, transaction_date, transaction_type,
                   transaction_count, total_amount
            FROM gold_branch_daily
            ORDER BY branch_id, transaction_date, transaction_type
            """
        ).fetchall()

    assert actual == expected, (
        f"Gold results do not match.\nExpected: {expected}\nActual: {actual}"
    )


if __name__ == "__main__":
    test_silver_count()
    test_gold_totals()
    print("PASS: Silver count and Gold totals match expected results.")