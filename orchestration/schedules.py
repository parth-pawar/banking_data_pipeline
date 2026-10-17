
import dagster as dg

from orchestration.jobs import banking_pipeline_job


daily_banking_schedule = dg.ScheduleDefinition(
    job=banking_pipeline_job,
    cron_schedule="0 0 * * *",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)
