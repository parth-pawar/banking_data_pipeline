
import pytest

from src.spark.data_quality import (
    run_checks,
    validate_data_quality,
)
from src.spark.load_data import (
    load_accounts,
    load_branches,
    load_customers,
    load_transactions,
)
import csv
import orchestration.ops as pipeline_ops
from orchestration.jobs import banking_pipeline_job


def test_week7_valid_banking_data_passes(spark, test_database):
    """Valid isolated banking data should pass production validation."""
    transactions = load_transactions(spark, test_database)
    accounts = load_accounts(spark, test_database)
    customers = load_customers(spark, test_database)
    branches = load_branches(spark, test_database)

    results = run_checks(
        transactions,
        accounts,
        customers,
        branches,
    )

    assert len(results) == 8
    assert all(bad_count == 0 for _, bad_count in results)

    # Production validation should not raise an exception.
    validate_data_quality(results)


def test_week7_bad_banking_data_fails(spark, test_database):
    """A transaction referencing a nonexistent account should fail."""
    import sqlite3

    # Insert deliberately invalid test data into the isolated database.
    # Foreign-key enforcement is disabled only for this connection
    # so the orphan transaction can be created for the test.
    with sqlite3.connect(test_database) as connection:
        connection.execute(
            "PRAGMA foreign_keys = OFF"
        )
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
                "T_BAD_ACCOUNT",
                "A_MISSING",
                "2026-01-05",
                "CREDIT",
                75.0,
                "USD",
                "week7_test.csv",
            ),
        )

    transactions = load_transactions(spark, test_database)
    accounts = load_accounts(spark, test_database)
    customers = load_customers(spark, test_database)
    branches = load_branches(spark, test_database)

    results = run_checks(
        transactions,
        accounts,
        customers,
        branches,
    )

    # Confirm the production orphan-account check detected the problem.
    orphan_count = dict(results)[
        "Transactions with nonexistent accounts"
    ]
    assert orphan_count == 1

    # The production validator must reject the bad data.
    with pytest.raises(ValueError, match="Data-quality validation failed"):
        validate_data_quality(results)


def test_week7_safe_rerun_does_not_duplicate_reports(
    test_database, tmp_path, monkeypatch
):
    report_dir = tmp_path / "week7_reports"

    # Redirect all reports and logs to temporary test locations.
    monkeypatch.setattr(pipeline_ops, "REPORT_DIR", report_dir)
    monkeypatch.setattr(pipeline_ops, "LOAD_REPORT_DIR", report_dir / "load")
    monkeypatch.setattr(
        pipeline_ops, "TRANSFORM_REPORT_DIR", report_dir / "transformations"
    )
    monkeypatch.setattr(
        pipeline_ops, "ANALYTICS_REPORT_DIR", report_dir / "analytics"
    )
    monkeypatch.setattr(pipeline_ops, "LOG_FILE", tmp_path / "week7_test.log")

    run_config = {
        "ops": {
            "extract_sqlite": {
                "config": {"db_path": str(test_database)}
            }
        }
    }

    # First run.
    first_result = banking_pipeline_job.execute_in_process(
        run_config=run_config
    )
    assert first_result.success

    def snapshot_reports():
        snapshots = {}
        for path in sorted(report_dir.rglob("*.csv")):
            with path.open("r", newline="", encoding="utf-8-sig") as file:
                snapshots[str(path.relative_to(report_dir))] = list(
                    csv.reader(file)
                )
        return snapshots

    first_snapshot = snapshot_reports()

    # Second run with exactly the same source database.
    second_result = banking_pipeline_job.execute_in_process(
        run_config=run_config
    )
    assert second_result.success

    second_snapshot = snapshot_reports()

    # Same report files, rows, and totals after rerunning.
    assert first_snapshot == second_snapshot
    assert len(second_snapshot) == 15



def test_week7_validation_failure_skips_report_publishing(
    test_database, tmp_path, monkeypatch
):
    import sqlite3
    import orchestration.ops as pipeline_ops
    from orchestration.jobs import banking_pipeline_job

    # Keep reports and logs inside pytest's temporary directory.
    report_dir = tmp_path / "failure_reports"

    monkeypatch.setattr(pipeline_ops, "REPORT_DIR", report_dir)
    monkeypatch.setattr(
        pipeline_ops, "LOAD_REPORT_DIR", report_dir / "load"
    )
    monkeypatch.setattr(
        pipeline_ops, "TRANSFORM_REPORT_DIR",
        report_dir / "transformations"
    )
    monkeypatch.setattr(
        pipeline_ops, "ANALYTICS_REPORT_DIR", report_dir / "analytics"
    )
    monkeypatch.setattr(
        pipeline_ops, "LOG_FILE", tmp_path / "failure_test.log"
    )

    # Insert a transaction referencing an account that does not exist.
    with sqlite3.connect(test_database) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
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
                "2026-01-05",
                "CREDIT",
                75.0,
                "USD",
                "week7_failure_test.csv",
            ),
        )

    run_config = {
        "ops": {
            "extract_sqlite": {
                "config": {"db_path": str(test_database)}
            }
        }
    }

    result = banking_pipeline_job.execute_in_process(
        run_config=run_config,
        raise_on_error=False,
    )

    # The job should fail at validation.
    assert not result.success

    # Confirm that the validation op failed.
    assert result.is_node_failed("validate_banking_data")
    # Publishing should not start.
    assert not result.events_for_node("publish_reports")

    # No report CSV files should have been created.
    assert not list(report_dir.rglob("*.csv"))
