import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import orchestration.ops as pipeline_ops
from orchestration.jobs import banking_pipeline_job


def main():
    test_report_dir = (
        PROJECT_ROOT / "output" / "dagster" / "scenario_c_reports"
    ).resolve()

    # Save the normal report paths.
    original_paths = {
        "REPORT_DIR": pipeline_ops.REPORT_DIR,
        "LOAD_REPORT_DIR": pipeline_ops.LOAD_REPORT_DIR,
        "TRANSFORM_REPORT_DIR": pipeline_ops.TRANSFORM_REPORT_DIR,
        "ANALYTICS_REPORT_DIR": pipeline_ops.ANALYTICS_REPORT_DIR,
    }

    try:
        # Redirect only report output for this test run.
        pipeline_ops.REPORT_DIR = test_report_dir
        pipeline_ops.LOAD_REPORT_DIR = test_report_dir / "load"
        pipeline_ops.TRANSFORM_REPORT_DIR = (
            test_report_dir / "transformations"
        )
        pipeline_ops.ANALYTICS_REPORT_DIR = test_report_dir / "analytics"

        result = banking_pipeline_job.execute_in_process(
            raise_on_error=False,
            run_config={
                "ops": {
                    "extract_sqlite": {
                        "config": {
                            "db_path": str(
                                PROJECT_ROOT
                                / "test"
                                / "data"
                                / "scenario_c.db"
                            )
                        }
                    }
                }
            },
        )

        print("\n========== SCENARIO C RESULTS ==========")
        print(f"Overall run successful: {result.success}")
        print(f"Failed steps: {result.get_failed_step_keys()}")
        print(f"Test report directory: {test_report_dir}")

    finally:
        # Restore the normal paths even if the job fails.
        for name, original_value in original_paths.items():
            setattr(pipeline_ops, name, original_value)


if __name__ == "__main__":
    main()
