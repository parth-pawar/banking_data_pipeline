
import dagster as dg

from orchestration.jobs import banking_pipeline_job
from orchestration.schedules import daily_banking_schedule


defs = dg.Definitions(
    jobs=[banking_pipeline_job],
    schedules=[daily_banking_schedule],
)
