import sqlite3

from src.operational.incremental_load import load_daily_file


def test_new_transaction_is_inserted(tmp_path):
    db_path = tmp_path / "test_banking.db"

    connection = sqlite3.connect(db_path)

    connection.execute("""
        CREATE TABLE transactions (
            transaction_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            source_file TEXT
        )
    """)

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
            "T1001",
            "A1001",
            "2026-09-06",
            "CREDIT",
            500.0,
            "USD",
            "initial.csv",
        ),
    )

    connection.commit()
    connection.close()

    daily_file = tmp_path / "daily.csv"

    daily_file.write_text(
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T4001,A1001,2026-09-07,CREDIT,120,USD\n"
    )

    load_daily_file(daily_file, db_path)

    connection = sqlite3.connect(db_path)

    row = connection.execute(
        """
        SELECT transaction_id, amount
        FROM transactions
        WHERE transaction_id = ?
        """,
        ("T4001",)
    ).fetchone()

    connection.close()

    assert row == ("T4001", 120.0)



def test_existing_transaction_correction_updates_value(tmp_path):
    db_path = tmp_path / "test_banking.db"

    connection = sqlite3.connect(db_path)

    connection.execute("""
        CREATE TABLE transactions (
            transaction_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            source_file TEXT
        )
    """)

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
            "T1001",
            "A1001",
            "2026-09-06",
            "CREDIT",
            500.0,
            "USD",
            "initial.csv",
        ),
    )

    connection.commit()
    connection.close()

    daily_file = tmp_path / "correction.csv"

    daily_file.write_text(
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T1001,A1001,2026-09-06,CREDIT,550,USD\n"
    )

    load_daily_file(daily_file, db_path)

    connection = sqlite3.connect(db_path)

    row = connection.execute(
        """
        SELECT amount
        FROM transactions
        WHERE transaction_id = ?
        """,
        ("T1001",)
    ).fetchone()

    connection.close()

    assert row == (550.0,)





def test_rerunning_same_batch_does_not_increase_transaction_count(tmp_path):
    db_path = tmp_path / "test_banking.db"

    connection = sqlite3.connect(db_path)

    connection.execute("""
        CREATE TABLE transactions (
            transaction_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            source_file TEXT
        )
    """)

    connection.commit()
    connection.close()

    daily_file = tmp_path / "daily.csv"

    daily_file.write_text(
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T4001,A1001,2026-09-07,CREDIT,120,USD\n"
    )

    # First run
    load_daily_file(daily_file, db_path)

    connection = sqlite3.connect(db_path)

    first_count = connection.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    connection.close()

    # Second run
    load_daily_file(daily_file, db_path)

    connection = sqlite3.connect(db_path)

    second_count = connection.execute(
        "SELECT COUNT(*) FROM transactions"
    ).fetchone()[0]

    connection.close()

    assert first_count == 1
    assert second_count == 1