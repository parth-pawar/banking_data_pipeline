import sqlite3
from pathlib import Path

def test_nonexistent_account(connection):
    """Test that a transaction cannot reference a nonexistent account."""
    try:
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

        connection.commit()

    except sqlite3.IntegrityError as error:
        print("Test 1: Transaction with nonexistent account")
        print("Expected: FOREIGN KEY constraint failure")
        print("Actual:", error)


def test_nonexistent_customer(connection):
    """Test that an account cannot reference a nonexistent customer."""
    try:
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
                "TEST002",
                "C9999",
                "BR001",
                "CHECKING",
                "ACTIVE",
            ),
        )

        connection.commit()

    except sqlite3.IntegrityError as error:
        print("Test 2: Account with nonexistent customer")
        print("Expected: FOREIGN KEY constraint failure")
        print("Actual:", error)


def test_duplicate_primary_key(connection):
    """Test that duplicate account IDs are rejected."""
    try:
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

        connection.commit()

    except sqlite3.IntegrityError as error:
        print("Test 3: Duplicate account primary key")
        print("Expected: PRIMARY KEY constraint failure")
        print("Actual:", error)


def test_invalid_amount(connection):
    """Test that transaction amounts must be greater than zero."""
    try:
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

        connection.commit()

    except sqlite3.IntegrityError as error:
        print("Test 4: Invalid transaction amount")
        print("Expected: CHECK constraint failure")
        print("Actual:", error)


def test_missing_required_value(connection):
    """Test that required customer fields cannot be NULL."""
    try:
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
                "TEST005",
                None,
                "test@example.com",
                "RETAIL",
            ),
        )

        connection.commit()

    except sqlite3.IntegrityError as error:
        print("Test 5: Missing required customer name")
        print("Expected: NOT NULL constraint failure")
        print("Actual:", error)


def main():
    connection = sqlite3.connect(
    Path(__file__).resolve().parents[2] / "database" / "banking.db"
)
    connection.execute("PRAGMA foreign_keys = ON")

    test_nonexistent_account(connection)
    test_nonexistent_customer(connection)
    test_duplicate_primary_key(connection)
    test_invalid_amount(connection)
    test_missing_required_value(connection)

    connection.close()


if __name__ == "__main__":
    main()