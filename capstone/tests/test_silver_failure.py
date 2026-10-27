import sqlite3

from capstone.orchestration.run_pipeline import run_pipeline
from capstone.src.init_test_bronze_db import main as init_test_bronze_db
from capstone.src.init_test_silver_db import main as init_test_silver_db
from capstone.src.init_test_gold_db import main as init_test_gold_db


def test_silver_failure_stops_pipeline(tmp_path):
    """Verify a Silver processing error fails the pipeline and prevents Gold."""

    # Arrange: create isolated test directories.
    landing_dir = tmp_path / "landing"
    database_dir = tmp_path / "database"
    input_dir = tmp_path / "input"
    gold_output = tmp_path / "output" / "gold"

    landing_dir.mkdir(parents=True)
    database_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)

    # Initialize the real schemas in temporary databases.
    init_test_bronze_db(tmp_path)
    init_test_silver_db(tmp_path)
    init_test_gold_db(tmp_path)

    # Supply a valid transaction file so Bronze succeeds.
    transaction_file = landing_dir / "BR001_20260908_TRANSACTION.csv"
    transaction_file.write_text(
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T9101,A1001,2026-09-08,CREDIT,100.00,USD\n",
        encoding="utf-8",
    )

    # Deliberately omit the required account_id column.
    account_reference = input_dir / "account_reference.csv"
    account_reference.write_text(
        "wrong_column,branch_id,account_status\n"
        "A1001,BR001,ACTIVE\n",
        encoding="utf-8",
    )

    # Act: run the actual pipeline.
    result = run_pipeline(
        landing_dir=landing_dir,
        database_dir=database_dir,
        account_reference=account_reference,
        gold_output=gold_output,
    )

    # Assert: Bronze succeeds, Silver fails, and Gold does not run.
    assert result["status"] == "FAILED"
    assert result["error_stage"] == "silver"
    assert result["stage_statuses"]["bronze"] == "SUCCESS"
    assert result["stage_statuses"]["silver"] == "NOT_RUN"
    assert result["stage_statuses"]["gold"] == "NOT_RUN"

    # Verify Bronze ingested the valid transaction.
    with sqlite3.connect(database_dir / "bronze.db") as connection:
        bronze_count = connection.execute(
            "SELECT COUNT(*) FROM bronze_transactions"
        ).fetchone()[0]

    assert bronze_count == 1

    # Verify the orchestration audit recorded the failure.
    with sqlite3.connect(database_dir / "orchestration.db") as connection:
        pipeline_row = connection.execute(
            """
            SELECT overall_status, bronze_status,
                   silver_status, gold_status, error_stage, error_message
            FROM pipeline_run_audit
            WHERE run_id = ?
            """,
            (result["run_id"],),
        ).fetchone()

    assert pipeline_row is not None
    assert pipeline_row[:5] == (
        "FAILED", "SUCCESS", "NOT_RUN", "NOT_RUN", "silver"
    )
    assert "account_id" in pipeline_row[5]