
import sqlite3

import pytest

from capstone.orchestration.run_pipeline import run_pipeline
from capstone.src.init_test_bronze_db import main as init_test_bronze_db
from capstone.src.init_test_silver_db import main as init_test_silver_db
from capstone.src.init_test_gold_db import main as init_test_gold_db


def test_gold_failure_preserves_previous_gold(tmp_path):
    """Verify a Gold failure preserves previously published Gold data."""

    landing_dir = tmp_path / "landing"
    database_dir = tmp_path / "database"
    input_dir = tmp_path / "input"
    gold_output = tmp_path / "output" / "gold"

    landing_dir.mkdir(parents=True)
    database_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)

    init_test_bronze_db(tmp_path)
    init_test_silver_db(tmp_path)
    init_test_gold_db(tmp_path)

    transaction_file = landing_dir / "BR001_20260907_TRANSACTION.csv"
    transaction_file.write_text(
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T2001,A1001,2026-09-07,CREDIT,250.00,USD\n"
        "T2002,A1002,2026-09-07,DEBIT,75.00,USD\n",
        encoding="utf-8",
    )

    account_reference = input_dir / "account_reference.csv"
    account_reference.write_text(
        "account_id,branch_id,account_status\n"
        "A1001,BR001,ACTIVE\n"
        "A1002,BR001,ACTIVE\n",
        encoding="utf-8",
    )

    # First run: create a valid Gold baseline.
    baseline_result = run_pipeline(
        landing_dir=landing_dir,
        database_dir=database_dir,
        account_reference=account_reference,
        gold_output=gold_output,
    )

    assert baseline_result["status"] == "SUCCESS"

    gold_csv = gold_output / "gold_branch_daily.csv"
    assert gold_csv.exists()
    original_csv = gold_csv.read_bytes()

    with sqlite3.connect(database_dir / "gold.db") as connection:
        original_gold_rows = connection.execute(
            """
            SELECT branch_id, transaction_date, transaction_type,
                   transaction_count, total_amount
            FROM gold_branch_daily
            ORDER BY branch_id, transaction_date, transaction_type
            """
        ).fetchall()

    assert len(original_gold_rows) == 2

    # Trigger a Gold failure without deleting any published Gold output.
    with sqlite3.connect(database_dir / "silver.db") as connection:
        connection.execute("DELETE FROM silver_transactions")

    failed_result = run_pipeline(
        landing_dir=landing_dir,
        database_dir=database_dir,
        account_reference=account_reference,
        gold_output=gold_output,
    )

    assert failed_result["status"] == "FAILED"
    assert failed_result["error_stage"] == "gold"

    # The previously published Gold CSV must remain byte-for-byte unchanged.
    assert gold_csv.read_bytes() == original_csv

    # The previously published Gold database results must remain unchanged.
    with sqlite3.connect(database_dir / "gold.db") as connection:
        current_gold_rows = connection.execute(
            """
            SELECT branch_id, transaction_date, transaction_type,
                   transaction_count, total_amount
            FROM gold_branch_daily
            ORDER BY branch_id, transaction_date, transaction_type
            """
        ).fetchall()

        failed_gold_audit = connection.execute(
            """
            SELECT status
            FROM gold_run_audit
            WHERE status = 'FAILED'
            ORDER BY rowid DESC
            LIMIT 1
            """
        ).fetchone()

    assert current_gold_rows == original_gold_rows
    assert failed_gold_audit is not None

    with sqlite3.connect(database_dir / "orchestration.db") as connection:
        pipeline_audit = connection.execute(
            """
            SELECT overall_status, bronze_status,
                   silver_status, gold_status, error_stage
            FROM pipeline_run_audit
            WHERE run_id = ?
            """,
            (failed_result["run_id"],),
        ).fetchone()

    assert pipeline_audit is not None
    assert pipeline_audit[0] == "FAILED"
    assert pipeline_audit[1] == "SUCCESS"
    assert pipeline_audit[2] == "SUCCESS"
    assert pipeline_audit[4] == "gold"
