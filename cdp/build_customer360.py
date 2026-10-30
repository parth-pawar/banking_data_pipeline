from asyncio import exceptions
import csv
import sqlite3
from collections import Counter
from pathlib import Path


# Location of the CDP project folder
CDP_DIR = Path(__file__).resolve().parent

# Input files containing synthetic reference data
INPUT_DIR = CDP_DIR / "input"
CUSTOMERS_CSV = INPUT_DIR / "customers.csv"
ACCOUNTS_CSV = INPUT_DIR / "accounts.csv"

# Existing Silver database (source of trusted transactions)
SILVER_DB = CDP_DIR.parent / "capstone" / "database" / "silver.db"

# Separate database for the CDP extension
CDP_DB = CDP_DIR / "database" / "cdp.db"


def validate_transactions(transactions, valid_account_ids):
    """Reject every transaction row whose ID occurs more than once."""

    transaction_id_counts = Counter(
        transaction["transaction_id"]
        for transaction in transactions
        if transaction.get("transaction_id")
    )

    duplicate_ids = {
        transaction_id
        for transaction_id, count in transaction_id_counts.items()
        if count > 1
    }
    
    valid_account_ids = set(valid_account_ids)
    valid_transactions = []
    exceptions = []

    for transaction in transactions:
        transaction_id = transaction.get("transaction_id")

        if transaction_id in duplicate_ids:
            exceptions.append(
            (
                "transaction",
                transaction_id,
                "Duplicate transaction_id",
            )
        )
        elif transaction.get("account_id") not in valid_account_ids:
            exceptions.append(
                    (
                        "transaction",
                        transaction_id,
                        "Unknown account_id",
                    )
                )
        else:
            valid_transactions.append(transaction)

    return valid_transactions, exceptions


def record_transaction_exceptions(connection, exceptions):
    """Save transaction validation exceptions to the CDP database."""

    connection.executemany(
        """
        INSERT INTO exceptions (entity_type, entity_id, reason)
        VALUES (?, ?, ?)
        """,
        exceptions,
    )

    print(f"Recorded {len(exceptions)} transaction exceptions.")



def initialize_database():
    """Create the CDP tables from schema.sql."""
    schema_path = CDP_DIR / "database" / "schema.sql"

    with sqlite3.connect(CDP_DB) as connection:
        schema_sql = schema_path.read_text(encoding="utf-8")
        connection.executescript(schema_sql)

    print("CDP database initialized successfully.")




def load_reference_data(
    customers_file=CUSTOMERS_CSV,
    accounts_file=ACCOUNTS_CSV,
):
    """Validate and load synthetic customers and account mappings."""

    with customers_file.open("r", newline="", encoding="utf-8") as file:
        customers = list(csv.DictReader(file))

    with accounts_file.open("r", newline="", encoding="utf-8") as file:
        accounts = list(csv.DictReader(file))

    exceptions = []
    valid_customers = []
    valid_accounts = []

    # Validate customer records.
    seen_customer_ids = set()

    for row_number, row in enumerate(customers, start=2):
        customer_id = (row.get("customer_id") or "").strip()
        customer_name = (row.get("customer_name") or "").strip()

        if not customer_id or not customer_name:
            exceptions.append(
                ("customer", customer_id or None,
                 f"Missing required field at CSV row {row_number}")
            )
        elif customer_id in seen_customer_ids:
            exceptions.append(
                ("customer", customer_id,
                 f"Duplicate customer_id at CSV row {row_number}")
            )
        else:
            seen_customer_ids.add(customer_id)
            valid_customers.append((customer_id, customer_name))

    valid_customer_ids = {row[0] for row in valid_customers}

    # Validate account records.
    seen_account_ids = set()

    for row_number, row in enumerate(accounts, start=2):
        account_id = (row.get("account_id") or "").strip()
        customer_id = (row.get("customer_id") or "").strip()

        if not account_id or not customer_id:
            exceptions.append(
                ("account", account_id or None,
                 f"Missing required field at CSV row {row_number}")
            )
        elif account_id in seen_account_ids:
            exceptions.append(
                ("account", account_id,
                 f"Duplicate account_id at CSV row {row_number}")
            )
        elif customer_id not in valid_customer_ids:
            exceptions.append(
                ("account", account_id,
                 f"Unknown customer_id: {customer_id}")
            )
        else:
            seen_account_ids.add(account_id)
            valid_accounts.append((account_id, customer_id))

    # Record validation results and load valid records.
    
    with sqlite3.connect(CDP_DB) as connection:
        # Remove old Gold results before rebuilding reference data.
        connection.execute("DELETE FROM customer_360")
        connection.execute("DELETE FROM accounts")
        connection.execute("DELETE FROM customers")
        connection.execute("DELETE FROM exceptions")

        connection.executemany(
            """
            INSERT INTO exceptions (entity_type, entity_id, reason)
            VALUES (?, ?, ?)
            """,
            exceptions,
        )

        connection.executemany(
            """
            INSERT INTO customers (customer_id, customer_name)
            VALUES (?, ?)
            """,
            valid_customers,
        )

        connection.executemany(
            """
            INSERT INTO accounts (account_id, customer_id)
            VALUES (?, ?)
            """,
            valid_accounts,
        )

    print(f"Loaded {len(valid_customers)} valid customers.")
    print(f"Loaded {len(valid_accounts)} valid accounts.")
    print(f"Recorded {len(exceptions)} input exceptions.")




def build_customer_360(transactions=None):
    """Rebuild customer-level Gold metrics from Silver transactions."""
    with sqlite3.connect(CDP_DB) as cdp_connection:
        cdp_connection.row_factory = sqlite3.Row
        # Attach the existing Silver database for read-only querying.
        cdp_connection.execute(
            "ATTACH DATABASE ? AS silver",
            (str(SILVER_DB),),
        )

        if transactions is None:
            cursor = cdp_connection.execute(
                """
                SELECT transaction_id, account_id, amount,
                       transaction_date, transaction_type
                FROM silver.silver_transactions
                """
            )

            transactions = [
                dict(row)
                for row in cursor.fetchall()
            ]

        account_rows = cdp_connection.execute(
            "SELECT account_id FROM accounts"
        ).fetchall()

        valid_account_ids = {row["account_id"] for row in account_rows}

        account_rows = cdp_connection.execute(
            "SELECT account_id FROM accounts"
        ).fetchall()

        valid_account_ids = {row["account_id"] for row in account_rows}

        valid_transactions, transaction_exceptions = validate_transactions(
            transactions,
            valid_account_ids,
        )

        cdp_connection.execute(
            "DELETE FROM exceptions WHERE entity_type = 'transaction'"
        )
        
        record_transaction_exceptions(
            cdp_connection,
            transaction_exceptions,
        )

        cdp_connection.execute(
            """
            CREATE TEMP TABLE valid_transactions (
                transaction_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_date TEXT NOT NULL,
                transaction_type TEXT NOT NULL
            )
            """
        )

        cdp_connection.executemany(
            """
            INSERT INTO valid_transactions (
                transaction_id,
                account_id,
                amount,
                transaction_date,
                transaction_type
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    transaction["transaction_id"],
                    transaction["account_id"],
                    transaction["amount"],
                    transaction["transaction_date"],
                    transaction["transaction_type"],
                )
                for transaction in valid_transactions
            ],
        )


        cdp_connection.execute("DELETE FROM customer_360")

        cdp_connection.execute(
            """
            INSERT INTO customer_360 (
                customer_id,
                customer_name,
                account_count,
                transaction_count,
                total_transaction_amount,
                last_transaction_date
            )
            SELECT
                c.customer_id,
                c.customer_name,
                COUNT(DISTINCT a.account_id) AS account_count,
                COUNT(t.transaction_id) AS transaction_count,
                COALESCE(SUM(t.amount), 0) AS total_transaction_amount,
                MAX(t.transaction_date) AS last_transaction_date
            FROM customers AS c
            LEFT JOIN accounts AS a
                ON a.customer_id = c.customer_id
            LEFT JOIN valid_transactions AS t
                ON t.account_id = a.account_id
            GROUP BY c.customer_id, c.customer_name
            ORDER BY c.customer_id
            """
        )

        

    print("Customer 360 Gold table rebuilt successfully.")



def export_customer_360_csv(output_file=None):
    """Export the Gold customer_360 table to a CSV snapshot."""
    output_dir = CDP_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_file is None:
        output_file = output_dir / "customer_360.csv"
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)


    with sqlite3.connect(CDP_DB) as connection:
        cursor = connection.execute(
            """
            SELECT customer_id, customer_name, account_count,
                   transaction_count, total_transaction_amount,
                   last_transaction_date
            FROM customer_360
            ORDER BY customer_id
            """
        )

        headers = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Gold CSV snapshot exported to: {output_file}")


if __name__ == "__main__":
    initialize_database()
    load_reference_data()
    build_customer_360()
    export_customer_360_csv()
    print("CDP build completed.")