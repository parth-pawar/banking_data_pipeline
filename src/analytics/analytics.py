import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_analytics_connection():
    """Create a connection to the analytics database."""
    connection = sqlite3.connect(
        PROJECT_ROOT / "database" / "analytics.db"
    )
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_analytics_schema(connection):
    """Create the analytical tables."""
    schema_path = (
        Path(__file__).parent / "analytics_schema.sql"
    )

    with open(schema_path, "r") as file:
        schema = file.read()

    connection.executescript(schema)
    print("Analytics schema created.")



def show_tables(connection):
    """Display the tables in the analytics database."""
    tables = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    print("Analytics tables:")
    for table in tables:
        print(table[0])



def create_operational_connection():
    """Create a connection to the operational database."""
    connection = sqlite3.connect(
        PROJECT_ROOT / "database" / "banking.db"
    )
    return connection

def load_customers(analytics_connection, operational_connection):
    """Load customers from banking.db into dim_customer."""
    rows = operational_connection.execute(
        """
        SELECT
            customer_id,
            customer_name,
            email,
            customer_segment
        FROM customer
        """
    ).fetchall()

    analytics_connection.executemany(
        """
        INSERT OR REPLACE INTO dim_customer (
            customer_id,
            customer_name,
            email,
            customer_segment
        )
        VALUES (?, ?, ?, ?)
        """,
        rows
    )


def load_branches(analytics_connection, operational_connection):
    """Load branches from banking.db into dim_branch."""
    rows = operational_connection.execute(
        """
        SELECT
            branch_id,
            branch_name,
            city,
            state
        FROM branch
        """
    ).fetchall()

    analytics_connection.executemany(
        """
        INSERT OR REPLACE INTO dim_branch (
            branch_id,
            branch_name,
            city,
            state
        )
        VALUES (?, ?, ?, ?)
        """,
        rows
    )


def load_accounts(analytics_connection, operational_connection):
    """Load accounts from banking.db into dim_account."""
    rows = operational_connection.execute(
        """
        SELECT
            account_id,
            customer_id,
            branch_id,
            account_type,
            account_status
        FROM account
        """
    ).fetchall()

    analytics_connection.executemany(
        """
        INSERT OR REPLACE INTO dim_account (
            account_id,
            customer_id,
            branch_id,
            account_type,
            account_status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows
    )

def load_dates(analytics_connection, operational_connection):
    """Load normalized transaction dates into dim_date."""
    rows = operational_connection.execute(
        """
        SELECT DISTINCT transaction_date
        FROM transactions
        """
    ).fetchall()

    for row in rows:
        raw_date = row[0]

        parsed_date = None

        for date_format in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                parsed_date = datetime.strptime(
                    raw_date,
                    date_format
                )
                break
            except ValueError:
                continue

        if parsed_date is None:
            raise ValueError(
                f"Unsupported transaction date: {raw_date}"
            )

        normalized_date = parsed_date.strftime("%Y-%m-%d")

        analytics_connection.execute(
            """
            INSERT OR REPLACE INTO dim_date (
                date,
                year,
                month,
                day
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                normalized_date,
                parsed_date.year,
                parsed_date.month,
                parsed_date.day,
            )
        )



def load_transactions(analytics_connection, operational_connection):
    """Load transactions from banking.db into fact_transaction."""

    rows = operational_connection.execute(
        """
        SELECT
            t.transaction_id,
            a.customer_id,
            t.account_id,
            a.branch_id,
            t.transaction_date,
            t.transaction_type,
            t.amount,
            t.currency
        FROM transactions t
        JOIN account a
            ON t.account_id = a.account_id
        """
    ).fetchall()

    for row in rows:
        raw_date = row[4]

        parsed_date = None

        for date_format in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                parsed_date = datetime.strptime(
                    raw_date,
                    date_format
                )
                break
            except ValueError:
                continue

        if parsed_date is None:
            raise ValueError(
                f"Unsupported transaction date: {raw_date}"
            )

        normalized_date = parsed_date.strftime("%Y-%m-%d")

        analytics_connection.execute(
            """
            INSERT OR REPLACE INTO fact_transaction (
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
                row[0],
                row[1],
                row[2],
                row[3],
                normalized_date,
                row[5],
                row[6],
                row[7],
            )
        )



def show_dimension_counts(connection):
    """Display row counts for the dimension tables."""
    for table in [
        "dim_customer",
        "dim_branch",
        "dim_account",
        "dim_date",
        "fact_transaction"
    ]:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count}")




def main():
    analytics_connection = create_analytics_connection()
    operational_connection = create_operational_connection()

    create_analytics_schema(analytics_connection)

    load_customers(
        analytics_connection,
        operational_connection
    )

    load_branches(
        analytics_connection,
        operational_connection
    )

    load_accounts(
        analytics_connection,
        operational_connection
    )

    load_dates(
        analytics_connection,
        operational_connection
    )

    load_transactions(
    analytics_connection,
    operational_connection
    )

    analytics_connection.commit()

    show_tables(analytics_connection)
    show_dimension_counts(analytics_connection)
  
    operational_connection.close()
    analytics_connection.close()





if __name__ == "__main__":
    main()