
import sqlite3

from capstone.orchestration.run_pipeline import run_pipeline
from capstone.src.init_test_bronze_db import main as init_test_bronze_db
from capstone.src.init_test_silver_db import main as init_test_silver_db
from capstone.src.init_test_gold_db import main as init_test_gold_db


def test_pipeline_recovers_after_bronze_failure(tmp_path):
    """Verify a failed pipeline can recover without resetting its databases."""

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

    account_reference = input_dir / "account_reference.csv"
    account_reference.write_text(
        "account_id,branch_id,account_status\n"
        "A1001,BR001,ACTIVE\n"
        "A1002,BR001,ACTIVE\n",
        encoding="utf-8",
    )

    # Establish a valid Gold report first.
    baseline_file = landing_dir / "BR001_20260907_TRANSACTION.csv"
    baseline_file.write_text(
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T2001,A1001,2026-09-07,CREDIT,250.00,USD\n",
        encoding="utf-8",
    )

    baseline_result = run_pipeline(
        landing_dir=landing_dir,
        database_dir=database_dir,
        account_reference=account_reference,
        gold_output=gold_output,
    )
    assert baseline_result["status"] == "SUCCESS"

    gold_csv = gold_output / "gold_branch_daily.csv"
    original_gold_csv = gold_csv.read_bytes()

    # Introduce a malformed header to cause a Bronze failure.
    problem_file = landing_dir / "BR001_20260908_TRANSACTION.csv"
    problem_file.write_text(
        "transaction_id,account_id,wrong_column\n"
        "T9001,A1001,100\n",
        encoding="utf-8",
    )

    failed_result = run_pipeline(
        landing_dir=landing_dir,
        database_dir=database_dir,
        account_reference=account_reference,
        gold_output=gold_output,
    )

    assert failed_result["status"] == "FAILED"
    assert failed_result["error_stage"] == "bronze"
    assert gold_csv.read_bytes() == original_gold_csv

    # Fix the same file; do not reset databases or delete Gold output.
    problem_file.write_text(
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T9001,A1001,2026-09-08,DEBIT,100.00,USD\n",
        encoding="utf-8",
    )

    recovery_result = run_pipeline(
        landing_dir=landing_dir,
        database_dir=database_dir,
        account_reference=account_reference,
        gold_output=gold_output,
    )

    assert recovery_result["status"] == "SUCCESS"

    # Check the corrected transaction is included in Gold.
    with sqlite3.connect(database_dir / "gold.db") as connection:
        gold_rows = connection.execute(
            """
            SELECT branch_id, transaction_date, transaction_type,
                   transaction_count, total_amount
            FROM gold_branch_daily
            ORDER BY branch_id, transaction_date, transaction_type
            """
        ).fetchall()

    assert gold_rows == [
        ("BR001", "2026-09-07", "CREDIT", 1, 250.0),
        ("BR001", "2026-09-08", "DEBIT", 1, 100.0),
    ]

    # Verify the failure and recovery are both recorded.
    with sqlite3.connect(database_dir / "orchestration.db") as connection:
        statuses = connection.execute(
            """
            SELECT overall_status
            FROM pipeline_run_audit
            ORDER BY started_at
            """
        ).fetchall()

    assert [row[0] for row in statuses] == [
        "SUCCESS",
        "FAILED",
        "SUCCESS",
    ]
