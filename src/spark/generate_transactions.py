
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
START_DATE = date(2026, 1, 1)
NUMBER_OF_DAYS = 365

FIELDNAMES = [
    "transaction_id",
    "account_id",
    "transaction_date",
    "transaction_type",
    "amount",
    "currency",
    "source_file",
]


def load_account_ids(db_path=DATABASE_FILE):
    """Load valid account IDs from the banking database."""
    database_path = Path(db_path).resolve()

    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database file not found: {database_path}"
        )

    database_uri = f"{database_path.as_uri()}?mode=ro"

    with sqlite3.connect(database_uri, uri=True) as connection:
        account_ids = [
            row[0]
            for row in connection.execute(
                "SELECT account_id FROM account"
            ).fetchall()
        ]

    return account_ids


def generate_transactions(
    account_ids,
    transaction_count=TRANSACTION_COUNT,
    seed=RANDOM_SEED,
):
    """Generate reproducible synthetic banking transactions."""
    if not account_ids:
        raise ValueError("At least one account ID is required.")

    if transaction_count < 0:
        raise ValueError("Transaction count cannot be negative.")

    rng = random.Random(seed)

    for number in range(1, transaction_count + 1):
        transaction_id = f"SYN{number:06d}"
        account_id = rng.choice(account_ids)
        transaction_type = rng.choice(["CREDIT", "DEBIT"])
        amount = round(rng.uniform(10, 2000), 2)

        transaction_date = START_DATE + timedelta(
            days=rng.randrange(NUMBER_OF_DAYS)
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


def write_transactions(transactions, output_file=OUTPUT_FILE):
    """Write generated transactions to a CSV file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    row_count = 0

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()

        for transaction in transactions:
            writer.writerow(transaction)
            row_count += 1

    return row_count


def main():
    account_ids = load_account_ids()

    if not account_ids:
        raise RuntimeError(
            "No account IDs were found in banking.db."
        )

    transactions = generate_transactions(account_ids)
    generated_count = write_transactions(transactions)

    print("Generated transaction count:", generated_count)
    print("Account IDs used:", len(account_ids))
    print("Output file:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
