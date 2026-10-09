import csv
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_FILE = PROJECT_ROOT / "database" / "banking.db"
OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "synthetic_transactions.csv"
)

TRANSACTION_COUNT = 100_000
RANDOM_SEED = 42


def load_account_ids():
    """Load valid account IDs from the banking database."""
    connection = sqlite3.connect(DATABASE_FILE)

    account_ids = [
        row[0]
        for row in connection.execute(
            "SELECT account_id FROM account"
        ).fetchall()
    ]

    connection.close()

    return account_ids


def generate_transactions(account_ids):
    """Generate reproducible synthetic banking transactions."""
    random.seed(RANDOM_SEED)

    start_date = date(2026, 1, 1)
    number_of_days = 365

    for number in range(1, TRANSACTION_COUNT + 1):
        transaction_id = f"SYN{number:06d}"

        account_id = random.choice(account_ids)

        transaction_type = random.choice(
            ["CREDIT", "DEBIT"]
        )

        amount = round(
            random.uniform(10, 2000),
            2,
        )

        transaction_date = (
            start_date
            + timedelta(
                days=random.randrange(number_of_days)
            )
        )

        yield {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "transaction_date": transaction_date.isoformat(),
            "transaction_type": transaction_type,
            "amount": amount,
            "currency": "USD",
            "source_file": "synthetic_transactions.csv",
        }


def main():
    account_ids = load_account_ids()

    if not account_ids:
        raise RuntimeError(
            "No account IDs were found in banking.db."
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "transaction_id",
        "account_id",
        "transaction_date",
        "transaction_type",
        "amount",
        "currency",
        "source_file",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for transaction in generate_transactions(account_ids):
            writer.writerow(transaction)

    print("Generated transaction count:", TRANSACTION_COUNT)
    print("Account IDs used:", len(account_ids))
    print("Output file:", OUTPUT_FILE)


if __name__ == "__main__":
    main()