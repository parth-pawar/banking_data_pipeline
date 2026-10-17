import sqlite3

from create_scenario_b import TEST_DATABASE


def insert_test_data():
    with sqlite3.connect(TEST_DATABASE) as connection:
        # Keep the test data controlled and repeatable.
        connection.execute("PRAGMA foreign_keys = OFF")

        connection.execute(
            """
            INSERT INTO customer (
                customer_id, customer_name, email, customer_segment
            )
            VALUES (?, ?, ?, ?)
            """,
            ("C_TEST", "Test Customer", "test@example.com", "STANDARD"),
        )

        connection.execute(
            """
            INSERT INTO branch (
                branch_id, branch_name, city, state
            )
            VALUES (?, ?, ?, ?)
            """,
            ("B_TEST", "Test Branch", "Pune", "Maharashtra"),
        )

        connection.execute(
            """
            INSERT INTO account (
                account_id, customer_id, branch_id,
                account_type, account_status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("A_TEST", "C_TEST", "B_TEST", "CHECKING", "ACTIVE"),
        )
        connection.execute(
            """
            INSERT INTO transactions (
                transaction_id, account_id, transaction_date,
                transaction_type, amount, currency, source_file
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "T_VALID_001",
                "A_TEST",
                "2026-10-15",
                "CREDIT",
                50.0,
                "USD",
                "scenario_b_test.csv",
            ),
        )
        # Deliberately invalid: A_MISSING is not in the account table.
        connection.execute(
            """
            INSERT INTO transactions (
                transaction_id, account_id, transaction_date,
                transaction_type, amount, currency, source_file
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "T_BAD_ACCOUNT",
                "A_MISSING",
                "2026-10-15",
                "CREDIT",
                100.0,
                "USD",
                "scenario_b_test.csv",
            ),
        )

        connection.commit()

        account_count = connection.execute(
            "SELECT COUNT(*) FROM account"
        ).fetchone()[0]

        transaction_count = connection.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        orphan_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions AS t
            LEFT JOIN account AS a ON t.account_id = a.account_id
            WHERE a.account_id IS NULL
            """
        ).fetchone()[0]

    print(f"Accounts inserted: {account_count}")
    print(f"Transactions inserted: {transaction_count}")
    print(f"Orphan transactions: {orphan_count}")


if __name__ == "__main__":
    insert_test_data()
