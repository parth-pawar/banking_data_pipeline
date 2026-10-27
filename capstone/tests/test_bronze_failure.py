import sqlite3
from capstone.src.init_test_bronze_db import main as init_test_bronze_db
from capstone.orchestration.run_pipeline import run_pipeline
from capstone.src.init_test_silver_db import main as init_test_silver_db
from capstone.src.init_test_gold_db import main as init_test_gold_db

def test_bronze_failure_stops_pipeline(tmp_path):
    # Arrange: create isolated test directories.
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

    # Create a CSV with an incorrect header.
    bad_file = landing_dir / "BR001_20260908_TRANSACTION.csv"
    bad_file.write_text(
        "transaction_id,account_id,wrong_column\n"
        "T9001,A1001,100\n",
        encoding="utf-8",
    )

    # The runner requires the account reference file to exist.
    account_reference = input_dir / "account_reference.csv"
    account_reference.write_text(
        "account_id,branch_id,account_status\n"
        "A1001,BR001,ACTIVE\n",
        encoding="utf-8",
    )

    # Act: run the pipeline with isolated paths.
    result = run_pipeline(
        landing_dir=landing_dir,
        database_dir=database_dir,
        account_reference=account_reference,
        gold_output=gold_output,
    )

    # Assert: Bronze fails and later stages do not run.
    assert result["status"] == "FAILED"
    assert result["error_stage"] == "bronze"
    assert result["stage_statuses"]["bronze"] == "FAILED"
    assert result["stage_statuses"]["silver"] == "NOT_RUN"
    assert result["stage_statuses"]["gold"] == "NOT_RUN"

    # Verify that Bronze recorded the failed file.
    with sqlite3.connect(database_dir / "bronze.db") as connection:
        audit_row = connection.execute(
                """
                SELECT status, error_message
                FROM bronze_file_audit
                WHERE source_filename = ? AND status = 'FAILED'
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (bad_file.name,),
        ).fetchone()

    assert audit_row is not None
    assert audit_row[0] == "FAILED"
    assert "unexpected columns" in audit_row[1]

    # Verify the overall orchestration audit.
    with sqlite3.connect(database_dir / "orchestration.db") as connection:
        pipeline_row = connection.execute(
            """
            SELECT overall_status, bronze_status,
                   silver_status, gold_status, error_stage
            FROM pipeline_run_audit
            WHERE run_id = ?
            """,
            (result["run_id"],),
        ).fetchone()

    assert pipeline_row == (
        "FAILED", "FAILED", "NOT_RUN", "NOT_RUN", "bronze"
    )