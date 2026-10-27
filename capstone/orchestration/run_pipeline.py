
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys
import uuid
import argparse

# Project directories
CAPSTONE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAPSTONE_DIR))

from src import ingest_bronze, process_silver, build_gold


DEFAULT_LANDING_DIR = CAPSTONE_DIR / "landing"
DEFAULT_DATABASE_DIR = CAPSTONE_DIR / "database"
DEFAULT_ACCOUNT_REFERENCE = CAPSTONE_DIR / "input" / "account_reference.csv"
DEFAULT_GOLD_OUTPUT = CAPSTONE_DIR / "output" / "gold"
DEFAULT_ORCHESTRATION_SCHEMA = DEFAULT_DATABASE_DIR / "orchestration_schema.sql"


def initialize_audit_db(orchestration_db, orchestration_schema):
    """Create the orchestration audit table if it does not exist."""
    orchestration_db.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(orchestration_db) as connection:
        schema = orchestration_schema.read_text(encoding="utf-8")
        connection.executescript(schema)


def save_run_audit(
    run_id,
    started_at,
    overall_status,
    stage_statuses,
    counts,
    orchestration_db,
    error_stage=None,
    error_message=None,
):
    """Record the overall pipeline result."""
    completed_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(orchestration_db) as connection:
        connection.execute(
            """
            INSERT INTO pipeline_run_audit (
                run_id, started_at, completed_at, overall_status,
                bronze_status, silver_status, gold_status,
                bronze_ingested_files, bronze_skipped_files,
                bronze_failed_files, silver_source_rows,
                error_stage, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                started_at,
                completed_at,
                overall_status,
                stage_statuses["bronze"],
                stage_statuses["silver"],
                stage_statuses["gold"],
                counts["ingested"],
                counts["skipped"],
                counts["failed"],
                counts["silver_rows"],
                error_stage,
                error_message,
            ),
        )


def run_pipeline(
    landing_dir=DEFAULT_LANDING_DIR,
    database_dir=DEFAULT_DATABASE_DIR,
    account_reference=DEFAULT_ACCOUNT_REFERENCE,
    gold_output=DEFAULT_GOLD_OUTPUT,
):
    bronze_db = database_dir / "bronze.db"
    silver_db = database_dir / "silver.db"
    gold_db = database_dir / "gold.db"
    orchestration_db = database_dir / "orchestration.db"

    """Run Bronze ingestion, Silver processing, and Gold publication."""
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    stage_statuses = {
        "bronze": "NOT_RUN",
        "silver": "NOT_RUN",
        "gold": "NOT_RUN",
    }
    counts = {
        "ingested": 0,
        "skipped": 0,
        "failed": 0,
        "silver_rows": 0,
    }

    error_stage = None
    error_message = None
    overall_status = "FAILED"

    try:
        initialize_audit_db(orchestration_db, DEFAULT_ORCHESTRATION_SCHEMA)

        # Stage 1: Discover and ingest files into Bronze.
        print("\n=== Stage 1: Bronze ingestion ===")
        bronze_result = ingest_bronze.main(
            landing_dir=landing_dir,
            db_file=bronze_db,
        )

        if not isinstance(bronze_result, dict):
            raise RuntimeError(
                "Bronze ingestion returned no result. "
                "Check that the Landing directory contains CSV files."
            )

        counts["ingested"] = bronze_result.get("ingested_files", 0)
        counts["skipped"] = bronze_result.get("skipped_files", 0)
        counts["failed"] = bronze_result.get("failed_files", 0)

        if (
            bronze_result.get("status") != "SUCCESS"
            or counts["failed"] > 0
        ):
            stage_statuses["bronze"] = "FAILED"
            error_stage = "bronze"
            raise RuntimeError("Bronze ingestion failed.")

        stage_statuses["bronze"] = "SUCCESS"

        # Stage 2: Validate, standardize, and apply corrections.
        print("\n=== Stage 2: Silver processing ===")
        silver_result = process_silver.process_silver(
            bronze_db=bronze_db,
            silver_db=silver_db,
            account_reference=account_reference,
        )

        if not isinstance(silver_result, dict):
            raise RuntimeError("Silver processing returned no result.")

        counts["silver_rows"] = silver_result.get("source_rows", 0)

        if silver_result.get("status") != "SUCCESS":
            stage_statuses["silver"] = "FAILED"
            error_stage = "silver"
            raise RuntimeError("Silver processing failed.")

        stage_statuses["silver"] = "SUCCESS"

        # Stage 3: Rebuild and publish Gold from accepted Silver data.
        print("\n=== Stage 3: Gold publication ===")
        gold_result = build_gold.main(
            silver_db=silver_db,
            gold_db=gold_db,
            gold_output=gold_output,
        )
        if isinstance(gold_result, dict):
            if gold_result.get("status") != "SUCCESS":
                stage_statuses["gold"] = "FAILED"
                error_stage = "gold"
                raise RuntimeError("Gold publication failed.")
        # Until build_gold.main() returns a result, reaching this point
        # means it completed without raising an exception.

        stage_statuses["gold"] = "SUCCESS"
        overall_status = "SUCCESS"

    except Exception as exc:
        if error_stage is None:
            for stage in ("bronze", "silver", "gold"):
                if stage_statuses[stage] == "NOT_RUN":
                    error_stage = stage
                    break

        error_message = str(exc)
        print(f"\nPipeline failed at {error_stage}: {error_message}")

    finally:
        if DEFAULT_ORCHESTRATION_SCHEMA.exists():
            try:
                save_run_audit(
                    run_id=run_id,
                    started_at=started_at,
                    overall_status=overall_status,
                    stage_statuses=stage_statuses,
                    counts=counts,
                    orchestration_db=orchestration_db,
                    error_stage=error_stage,
                    error_message=error_message,
                )
            except Exception as audit_error:
                print(f"Could not save orchestration audit: {audit_error}")

    print(f"\nOverall status: {overall_status}")
    print(f"Pipeline run ID: {run_id}")

    return {
        "run_id": run_id,
        "status": overall_status,
        "stage_statuses": stage_statuses,
        "error_stage": error_stage,
        "error_message": error_message,
    }

def get_pipeline_paths(test_name=None):
    """Return pipeline paths for either the normal run or a test scenario."""

    if test_name is None:
        return {
            "landing_dir": DEFAULT_LANDING_DIR,
            "database_dir": DEFAULT_DATABASE_DIR,
            "account_reference": DEFAULT_ACCOUNT_REFERENCE,
            "gold_output": DEFAULT_GOLD_OUTPUT,
        }

    test_dir = CAPSTONE_DIR / "test" / test_name

    if not test_dir.is_dir():
        raise ValueError(f"Unknown test scenario: {test_name}")

    return {
        "landing_dir": test_dir / "landing",
        "database_dir": test_dir / "database",
        "account_reference": test_dir / "input" / "account_reference.csv",
        "gold_output": test_dir / "output" / "gold",
    }



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the banking data pipeline.")
    parser.add_argument(
        "--test",
        metavar="SCENARIO",
        help="Run using an isolated test scenario, such as normal_input.",
    )
    args = parser.parse_args()

    try:
        paths = get_pipeline_paths(args.test)
    except ValueError as error:
        parser.error(str(error))

    result = run_pipeline(**paths)

    if result["status"] != "SUCCESS":
        raise SystemExit(1)