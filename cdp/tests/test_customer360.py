import sqlite3
from pathlib import Path
import json
import threading
from http.server import HTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError


import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_customer360 as cdp
import api_server as api

C001_TRANSACTIONS = [
    {
        "transaction_id": "TX001",
        "account_id": "A1001",
        "amount": 250.0,
        "transaction_date": "2026-09-07",
        "transaction_type": "CREDIT",
    },
    {
        "transaction_id": "TX002",
        "account_id": "A1001",
        "amount": 75.0,
        "transaction_date": "2026-09-07",
        "transaction_type": "DEBIT",
    },
    {
        "transaction_id": "TX003",
        "account_id": "A1002",
        "amount": 400.0,
        "transaction_date": "2026-09-08",
        "transaction_type": "CREDIT",
    },
    {
        "transaction_id": "TX004",
        "account_id": "A1002",
        "amount": 125.0,
        "transaction_date": "2026-09-08",
        "transaction_type": "DEBIT",
    },
]



def test_c001_customer_summary(tmp_path, monkeypatch):
    # Use temporary databases so normal project data stays untouched.
    monkeypatch.setattr(cdp, "CDP_DB", tmp_path / "cdp.db")
    monkeypatch.setattr(cdp, "SILVER_DB", tmp_path / "silver.db")

    cdp.initialize_database()

    cdp.load_reference_data(
        customers_file=Path(__file__).parent / "fixtures" / "customers_c001.csv",
        accounts_file=Path(__file__).parent / "fixtures" / "accounts_c001.csv",
    )

    cdp.build_customer_360(transactions=C001_TRANSACTIONS)

    with sqlite3.connect(tmp_path / "cdp.db") as connection:
        # Independently calculate expected metrics from the test transactions.
        connection.execute(
            """
            CREATE TABLE test_transactions (
                transaction_id TEXT,
                account_id TEXT,
                amount REAL
            )
            """
        )

        connection.executemany(
            """
            INSERT INTO test_transactions
                (transaction_id, account_id, amount)
            VALUES (?, ?, ?)
            """,
            [
                (row["transaction_id"], row["account_id"], row["amount"])
                for row in C001_TRANSACTIONS
            ],
        )

        expected = connection.execute(
            """
            SELECT
                COUNT(DISTINCT a.account_id),
                COUNT(t.transaction_id),
                SUM(t.amount)
            FROM test_transactions AS t
            JOIN accounts AS a
                ON a.account_id = t.account_id
            WHERE a.customer_id = ?
            """,
            ("C001",),
        ).fetchone()

        actual = connection.execute(
            """
            SELECT account_count, transaction_count, total_transaction_amount
            FROM customer_360
            WHERE customer_id = ?
            """,
            ("C001",),
        ).fetchone()

    assert actual == expected, (
        f"Expected {expected}, got {actual}"
    )







def test_c002_api_returns_requested_customer(tmp_path, monkeypatch):
    db_path = tmp_path / "api_test.db"
    monkeypatch.setattr(api, "CDP_DB", db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE customer_360 (
                customer_id TEXT PRIMARY KEY,
                customer_name TEXT,
                account_count INTEGER,
                transaction_count INTEGER,
                total_transaction_amount REAL,
                last_transaction_date TEXT
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO customer_360 VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("C001", "Synthetic Customer One", 3, 3, 665.5, "2026-09-06"),
                ("C002", "Synthetic Customer Two", 7, 7, 2760.0, "2026-09-06"),
            ],
        )

    server = HTTPServer(("127.0.0.1", 0), api.CustomerSummaryHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        url = f"http://127.0.0.1:{server.server_port}/customers/C002/summary"

        with urlopen(url) as response:
            actual = json.loads(response.read().decode("utf-8"))
            assert response.status == 200

        assert actual["customer_id"] == "C002"
        assert actual["customer_name"] == "Synthetic Customer Two"
        assert actual["total_transaction_amount"] == 2760.0

    finally:
        server.shutdown()
        server.server_close()
        thread.join()





def test_c003_customer_with_no_transactions(tmp_path, monkeypatch):
    monkeypatch.setattr(cdp, "CDP_DB", tmp_path / "cdp.db")
    monkeypatch.setattr(cdp, "SILVER_DB", tmp_path / "silver.db")

    customers_file = tmp_path / "customers.csv"
    accounts_file = tmp_path / "accounts.csv"

    customers_file.write_text(
        "customer_id,customer_name\nC003,Synthetic Customer Three\n"
    )
    accounts_file.write_text(
        "account_id,customer_id\nA9001,C003\n"
    )

    cdp.initialize_database()
    cdp.load_reference_data(customers_file, accounts_file)
    cdp.build_customer_360(transactions=[])

    with sqlite3.connect(tmp_path / "cdp.db") as connection:
        actual = connection.execute(
            """
            SELECT customer_id, account_count, transaction_count,
                   total_transaction_amount, last_transaction_date
            FROM customer_360
            WHERE customer_id = ?
            """,
            ("C003",),
        ).fetchone()

    expected = ("C003", 1, 0, 0.0, None)
    assert actual == expected, (
        f"Expected {expected}, got {actual}"
    )



def test_c999_unknown_customer_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "api_test.db"
    monkeypatch.setattr(api, "CDP_DB", db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE customer_360 (
                customer_id TEXT PRIMARY KEY,
                customer_name TEXT,
                account_count INTEGER,
                transaction_count INTEGER,
                total_transaction_amount REAL,
                last_transaction_date TEXT
            )
            """
        )

    server = HTTPServer(("127.0.0.1", 0), api.CustomerSummaryHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        url = f"http://127.0.0.1:{server.server_port}/customers/C999/summary"

        try:
            urlopen(url)
            assert False, "Expected HTTP 404 for unknown customer"
        except HTTPError as error:
            assert error.code == 404
            actual = json.loads(error.read().decode("utf-8"))

        assert actual == {"error": "Customer not found"}

    finally:
        server.shutdown()
        server.server_close()
        thread.join()





def test_build_customer360_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(cdp, "CDP_DB", tmp_path / "cdp.db")
    monkeypatch.setattr(cdp, "SILVER_DB", tmp_path / "silver.db")

    cdp.initialize_database()
    cdp.load_reference_data(
        customers_file=Path(__file__).parent / "fixtures" / "customers_c001.csv",
        accounts_file=Path(__file__).parent / "fixtures" / "accounts_c001.csv",
    )

    # First build
    cdp.build_customer_360(transactions=C001_TRANSACTIONS)

    with sqlite3.connect(tmp_path / "cdp.db") as connection:
        first_result = connection.execute(
            """
            SELECT customer_id, customer_name, account_count,
                   transaction_count, total_transaction_amount,
                   last_transaction_date
            FROM customer_360
            ORDER BY customer_id
            """
        ).fetchall()

    # Second build using the same input
    cdp.build_customer_360(transactions=C001_TRANSACTIONS)

    with sqlite3.connect(tmp_path / "cdp.db") as connection:
        second_result = connection.execute(
            """
            SELECT customer_id, customer_name, account_count,
                   transaction_count, total_transaction_amount,
                   last_transaction_date
            FROM customer_360
            ORDER BY customer_id
            """
        ).fetchall()

    assert second_result == first_result





def test_invalid_transactions_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(cdp, "CDP_DB", tmp_path / "cdp.db")
    monkeypatch.setattr(cdp, "SILVER_DB", tmp_path / "silver.db")

    customers_file = tmp_path / "customers.csv"
    accounts_file = tmp_path / "accounts.csv"

    customers_file.write_text(
        "customer_id,customer_name\nC001,Synthetic Customer One\n"
    )
    accounts_file.write_text(
        "account_id,customer_id\n"
        "A1001,C001\n"
        "A9999,C999\n"
    )

    transactions = [
        {
            "transaction_id": "TX001",
            "account_id": "A1001",
            "amount": 100.0,
            "transaction_date": "2026-09-07",
            "transaction_type": "CREDIT",
        },
        {
            "transaction_id": "TX002",
            "account_id": "A1001",
            "amount": 200.0,
            "transaction_date": "2026-09-07",
            "transaction_type": "CREDIT",
        },
        {
            "transaction_id": "TX002",
            "account_id": "A1001",
            "amount": 200.0,
            "transaction_date": "2026-09-07",
            "transaction_type": "CREDIT",
        },
        {
            "transaction_id": "TX003",
            "account_id": "A8888",
            "amount": 500.0,
            "transaction_date": "2026-09-07",
            "transaction_type": "CREDIT",
        },
    ]

    cdp.initialize_database()
    cdp.load_reference_data(customers_file, accounts_file)
    cdp.build_customer_360(transactions=transactions)

    with sqlite3.connect(tmp_path / "cdp.db") as connection:
        actual = connection.execute(
            """
            SELECT account_count, transaction_count, total_transaction_amount
            FROM customer_360
            WHERE customer_id = ?
            """,
            ("C001",),
        ).fetchone()

        exceptions = connection.execute(
            """
            SELECT entity_type, entity_id, reason
            FROM exceptions
            ORDER BY entity_type, entity_id
            """
        ).fetchall()

    assert actual == (1, 1, 100.0)

    assert ("transaction", "TX002", "Duplicate transaction_id") in exceptions
    assert ("transaction", "TX003", "Unknown account_id") in exceptions
    assert ("account", "A9999", "Unknown customer_id: C999") in exceptions