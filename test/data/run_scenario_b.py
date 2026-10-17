import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.jobs import banking_pipeline_job


def main():
    result = banking_pipeline_job.execute_in_process(
        raise_on_error=False,
        run_config={
            "ops": {
                "extract_sqlite": {
                    "config": {
                        "db_path": "test/data/scenario_b.db"
                    }
                }
            }
        },
    )

    print("\n========== SCENARIO B RESULTS ==========")
    print(f"Overall run successful: {result.success}")
    print(f"Failed steps: {result.get_failed_step_keys()}")

    successful_steps = [
        event.step_key
        for event in result.all_events
        if event.is_step_success
    ]
    print(f"Successful steps: {successful_steps}")

    publish_started = any(
        event.is_step_start and event.step_key == "publish_reports"
        for event in result.all_events
    )
    print(f"Publish step started: {publish_started}")


if __name__ == "__main__":
    main()
