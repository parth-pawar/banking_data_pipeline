
import dagster as dg
import pytest

import orchestration.ops as ops
import src.spark.load_data as load_data


def test_extract_sqlite_retries_after_temporary_failure(
    spark,
    test_database,
    monkeypatch,
):
    original_loader = load_data.load_table_from_sqlite
    attempts = {"count": 0}

    def fail_once_then_load(spark_session, table_name, db_path):
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise RuntimeError("Simulated temporary SQLite read failure")

        return original_loader(spark_session, table_name, db_path)

    monkeypatch.setattr(
        load_data,
        "load_table_from_sqlite",
        fail_once_then_load,
    )

    # The production loader functions resolve load_table_from_sqlite
    # from their own module, so patch that shared function there.
    # The imports in orchestration.ops reference the loader wrappers.
    # We also use the real Spark session and isolated test database.

    @dg.job
    def retry_extraction_job():
        ops.extract_sqlite()

    result = retry_extraction_job.execute_in_process(
        run_config={
            "ops": {
                "extract_sqlite": {
                    "config": {"db_path": str(test_database)}
                }
            }
        },
        raise_on_error=False,
    )

    assert result.success
    assert attempts["count"] > 1
