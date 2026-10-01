import sqlite3
from src.operational import database
import pytest


def test_expected_tables():
    connection = sqlite3.connect(":memory:")

    database.create_schema(connection)

    tables = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    table_names = {row[0] for row in tables}

    assert {"customer", "branch", "account", "transactions"} <= table_names

    connection.close()



def test_foreign_keys_enabled():
    connection = database.create_connection(":memory:")

    foreign_keys = connection.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    assert foreign_keys == 1

    connection.close()



def test_expected_row_counts():
    connection = database.create_connection(":memory:")

    database.create_schema(connection)
    database.load_customers(connection)
    database.load_branches(connection)
    database.load_accounts(connection)
    database.load_transactions(connection)

    assert connection.execute(
        "SELECT COUNT(*) FROM customer"
    ).fetchone()[0] == 6

    assert connection.execute(
        "SELECT COUNT(*) FROM branch"
    ).fetchone()[0] == 3

    assert connection.execute(
        "SELECT COUNT(*) FROM account"
    ).fetchone()[0] == 10

    assert connection.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0] == 10

    connection.close()




def test_duplicate_primary_key_rejected():
    connection = database.create_connection(":memory:")

    database.create_schema(connection)
    database.load_customers(connection)
    database.load_branches(connection)
    database.load_accounts(connection)
    database.load_transactions(connection)

    with pytest.raises(sqlite3.IntegrityError):
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
                "A1001",
                "C1001",
                "BR001",
                "CHECKING",
                "ACTIVE",
            ),
        )

    connection.close()



def test_invalid_foreign_key_rejected():
    connection = database.create_connection(":memory:")

    database.create_schema(connection)
    database.load_customers(connection)
    database.load_branches(connection)
    database.load_accounts(connection)
    database.load_transactions(connection)

    with pytest.raises(sqlite3.IntegrityError):
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
                "TEST001",
                "A9999",
                "2026-09-06",
                "CREDIT",
                100.0,
                "USD",
                "integrity_test",
            ),
        )

    connection.close()



def test_invalid_amount_rejected():
    connection = database.create_connection(":memory:")

    database.create_schema(connection)
    database.load_customers(connection)
    database.load_branches(connection)
    database.load_accounts(connection)
    database.load_transactions(connection)

    with pytest.raises(sqlite3.IntegrityError):
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
                "TEST004",
                "A1001",
                "2026-09-06",
                "CREDIT",
                -50,
                "USD",
                "integrity_test",
            ),
        )

    connection.close()




def test_highest_transaction_branch():
    connection = database.create_connection(":memory:")

    database.create_schema(connection)
    database.load_customers(connection)
    database.load_branches(connection)
    database.load_accounts(connection)
    database.load_transactions(connection)

    result = connection.execute(
        """
        SELECT
            b.branch_id,
            b.branch_name,
            SUM(t.amount) AS total_transaction_value
        FROM branch b
        JOIN account a
            ON b.branch_id = a.branch_id
        JOIN transactions t
            ON a.account_id = t.account_id
        GROUP BY b.branch_id, b.branch_name
        ORDER BY total_transaction_value DESC
        LIMIT 1
        """
    ).fetchone()

    assert result == ("BR003", "Lake Branch", 1575.0)

    connection.close()





def test_rerun_rebuilds_database(tmp_path):
    db_path = tmp_path / "test_banking.db"

    database.build_database(str(db_path))

    connection = sqlite3.connect(db_path)

    first_count = connection.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    connection.close()

    database.build_database(str(db_path))

    connection = sqlite3.connect(db_path)

    second_count = connection.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    connection.close()

    assert first_count == 10
    assert second_count == 10