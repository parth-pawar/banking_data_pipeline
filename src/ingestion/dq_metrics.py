
import pandas as pd
from config.config import ALLOWED_TRANSACTION_TYPES


# create_dq_summary is a function that creates a summary of data quality metrics based on the provided DataFrame and file processing statistics. 
# The function returns a DataFrame containing the summary metrics.
def create_dq_summary(data, files_discovered, files_read, files_skipped):

    total_rows = len(data)
    invalid_rows = (data["error_reason"] != "").sum()

    rejection_rate = (
        round(invalid_rows / total_rows * 100, 2)
        if total_rows > 0
        else 0
    )

    # We explicitly wrote regex=True to make it clear that the | is being used as a regex OR operator.
    summary = {
        "total rows read": total_rows,
        "valid rows": (data["error_reason"] == "").sum(),
        "invalid rows": invalid_rows,
        "rejection rate": rejection_rate,
        "missing transaction_id": data["transaction_id"].isna().sum(),
        "missing account_id": data["account_id"].isna().sum(),
        "invalid transaction_type": (~data["transaction_type"].isin(ALLOWED_TRANSACTION_TYPES)).sum(),
        "invalid amount": data["error_reason"].str.contains("amount is missing or not numeric|amount must be greater than 0", regex=True).sum(),
        "invalid transaction_date": data["error_reason"].str.contains("invalid transaction_date").sum(),
        "invalid currency": data["error_reason"].str.contains("currency must be USD").sum(),
        "duplicate transaction_id": (data["transaction_id"].notna() & data["transaction_id"].duplicated(keep=False)).sum(),
        "files discovered": files_discovered,
        "files successfully read": files_read,
        "files skipped": files_skipped,
    }

    result = pd.DataFrame(
        summary.items(),
        columns=["metric", "count"]
    )

    result["count"] = result["count"].apply(
        lambda value: f"{value:g}"
    )

    return result