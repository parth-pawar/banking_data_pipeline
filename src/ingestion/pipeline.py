import glob
import pandas as pd
import os
import logging

from config.config import REQUIRED_COLUMNS
from src.ingestion.validation import validate_transactions
from src.ingestion.dq_metrics import create_dq_summary

os.makedirs("output/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="output/logs/pipeline.log"
)

logger = logging.getLogger(__name__)


def run_pipeline(
    input_dir="data/raw",
    validated_dir="data/validated",
    output_dir="output"
):

    logger.info("Pipeline started")
    os.makedirs(validated_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/dq", exist_ok=True)
    os.makedirs(f"{output_dir}/summaries", exist_ok=True)
    files_discovered = 0
    files_read = 0
    files_skipped = 0
    
    # 1. Extract

    files = glob.glob(f"{input_dir}/*.csv")
    files_discovered = len(files)

    if files_discovered == 0:
        logger.warning("No CSV files found in input directory: %s", input_dir)

    dataframes = []

    for file in files:
        logger.info("Reading file: %s", file)

        try:
            df = pd.read_csv(file)
        except (
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            UnicodeDecodeError,
            OSError
        ) as exc:
            logger.error(
                "Could not read file %s: %s. Skipping this file.",
                file,
                exc
            )
            files_skipped += 1
            continue

        missing_columns = REQUIRED_COLUMNS - set(df.columns)

        if missing_columns:
            logger.warning(
                "File %s is missing required columns: %s. Skipping this file.",
                file,
                missing_columns
            )
            files_skipped += 1
            continue

        
        files_read += 1
        logger.info("Successfully read file: %s", file)

        if df.empty:
            logger.warning("File %s contains no transactions.", file)

        df["source_file"] = file
        dataframes.append(df)

    if not dataframes:
        logger.warning("No valid input files to process.")
        
        daily_data = pd.DataFrame(
            columns=list(REQUIRED_COLUMNS) + ["source_file"]
        )
    else:
        daily_data = pd.concat(
            dataframes,
            ignore_index=True
        )

    # 2. Transform

    daily_data = validate_transactions(daily_data)

    # 3. Separate valid / invalid

    valid_transactions = daily_data[
        daily_data["error_reason"] == ""
    ].copy()

    invalid_transactions = daily_data[
        daily_data["error_reason"] != ""
    ].copy()

    valid_transactions = valid_transactions.drop(
        columns=["error_reason"]
    )

    # 4. Load

    valid_transactions.to_csv(
    f"{validated_dir}/valid_transactions.csv",
    index=False
    )

    invalid_transactions.to_csv(
    f"{validated_dir}/invalid_transactions.csv",
    index=False
    )

    

    # 5. Summary

    summary = pd.DataFrame({
        "metric": [
            "total input records",
            "valid records",
            "invalid records"
        ],
        "count": [
            len(daily_data),
            len(valid_transactions),
            len(invalid_transactions)
        ]
    })

    summary.to_csv(
        f"{output_dir}/summaries/summary.csv",
        index=False
    )

    dq_summary = create_dq_summary(
    daily_data,
    files_discovered,
    files_read,
    files_skipped
    )

    dq_summary.to_csv(
    f"{output_dir}/dq/dq_summary.csv",
    index=False
    )


    logger.info("Pipeline completed successfully.")
    print("Pipeline completed successfully.")
    print(f"Total records: {len(daily_data)}")
    print(f"Valid records: {len(valid_transactions)}")
    print(f"Invalid records: {len(invalid_transactions)}")


if __name__ == "__main__":
    run_pipeline()