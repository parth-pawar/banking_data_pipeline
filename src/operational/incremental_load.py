
import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_connection(db_path=None):
    """Connect to the operational database."""
    if db_path is None:
        db_path = PROJECT_ROOT / "database" / "banking.db"

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

# excluded means: the new row that SQLite tried to insert but couldn't because of the conflict.
def load_daily_file(file_path, db_path=None):
    """Read one daily transaction CSV file."""
    connection = create_connection(db_path)

    with open(file_path, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            
            connection.execute(
                """
                INSERT INTO transactions (
                    transaction_id,
                    account_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    source_file
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(transaction_id) DO UPDATE SET
                    account_id = excluded.account_id,
                    transaction_date = excluded.transaction_date,
                    transaction_type = excluded.transaction_type,
                    amount = excluded.amount,
                    currency = excluded.currency,
                    source_file = excluded.source_file
                """,
                (
                    row["transaction_id"],
                    row["account_id"],
                    row["transaction_date"],
                    row["transaction_type"],
                    float(row["amount"]),
                    row["currency"],
                    Path(file_path).name,
                ),
            )

            print(f"Processed {row['transaction_id']}")
            connection.commit()

    connection.close()


if __name__ == "__main__":
    load_daily_file(
        PROJECT_ROOT / "data" / "daily" / "transactions_20260909.csv"
    )