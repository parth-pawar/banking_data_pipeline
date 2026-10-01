import sqlite3
import csv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def create_connection(db_path):
    """Create a SQLite connection and enable foreign-key enforcement."""
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")


    print(
        "Foreign-key enforcement:",
        connection.execute("PRAGMA foreign_keys").fetchone()[0]
    )

    return connection




def create_schema(connection):
    """Create the database tables using schema.sql."""
    with open(Path(__file__).parent / "schema.sql", "r") as file:
        schema = file.read()

    connection.executescript(schema)

    print("Database schema created.")






def load_customers(connection):
    """Load customer records from customers.csv."""
    with open(PROJECT_ROOT / "data" / "reference" / "customers.csv", "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            connection.execute(
                """
                INSERT INTO customer (
                    customer_id,
                    customer_name,
                    email,
                    customer_segment
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    row["customer_id"],
                    row["customer_name"],
                    row["email"],
                    row["customer_segment"],
                ),
            )

    connection.commit()

    print("Customers loaded.")





def load_branches(connection):
    """Load branch records from branches.csv."""
    with open(PROJECT_ROOT / "data" / "reference" / "branches.csv", "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            connection.execute(
                """
                INSERT INTO branch (
                    branch_id,
                    branch_name,
                    city,
                    state
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    row["branch_id"],
                    row["branch_name"],
                    row["city"],
                    row["state"],
                ),
            )

    connection.commit()

    print("Branches loaded.")






def load_accounts(connection):
    """Load account records from accounts.csv."""
    with open(PROJECT_ROOT / "data" / "reference" / "accounts.csv", "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            connection.execute(
                """
                INSERT INTO account (
                    account_id,
                    customer_id,
                    branch_id,
                    account_type,
                    account_status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row["account_id"],
                    row["customer_id"],
                    row["branch_id"],
                    row["account_type"],
                    row["account_status"],
                ),
            )

    connection.commit()

    print("Accounts loaded.")







def load_transactions(connection):
    """Load transaction records from valid_transactions.csv."""
    with open(
    PROJECT_ROOT / "data" / "validated" / "valid_transactions.csv",
    "r",
    newline=""
) as file:
        
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
                """,
                (
                    row["transaction_id"],
                    row["account_id"],
                    row["transaction_date"],
                    row["transaction_type"],
                    float(row["amount"]),
                    row["currency"],
                    row["source_file"],
                ),
            )

    connection.commit()

    print("Transactions loaded.")



def show_row_counts(connection):
    """Display the final number of rows in each database table."""
    print("\nFinal row counts:")

    for table in ["customer", "branch", "account", "transactions"]:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count}")


def build_database(db_path):
    if os.path.exists(db_path):
        print("Database already exists. Skipping full load.")
        return

    connection = create_connection(db_path)
    create_schema(connection)
    load_customers(connection)
    load_branches(connection)
    load_accounts(connection)
    load_transactions(connection)
    show_row_counts(connection)
    connection.close()


def rebuild_database(db_path):
    if os.path.exists(db_path):
        os.remove(db_path)

    build_database(db_path)


def main():
    os.makedirs(PROJECT_ROOT / "database", exist_ok=True)
    build_database(PROJECT_ROOT / "database" / "banking.db")


if __name__ == "__main__":
    main()