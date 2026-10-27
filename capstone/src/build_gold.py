
import os
import sys
import sqlite3
import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


CAPSTONE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_SILVER_DB = CAPSTONE_DIR / "database" / "silver.db"
DEFAULT_GOLD_DB = CAPSTONE_DIR / "database" / "gold.db"
DEFAULT_GOLD_OUTPUT = CAPSTONE_DIR / "output" / "gold"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def record_failed_run(
    run_id,
    started_at,
    error_message,
    source_rows=0,
    gold_db=DEFAULT_GOLD_DB,
):
    """Record a failed run without changing the published Gold table."""
    with sqlite3.connect(gold_db) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO gold_run_audit (
                run_id, status, started_at, completed_at,
                source_rows, gold_groups, error_message
            )
            VALUES (?, 'FAILED', ?, ?, ?, 0, ?)
            """,
            (
                run_id,
                started_at,
                utc_now(),
                source_rows,
                error_message,
            ),
        )

def main(
    silver_db=DEFAULT_SILVER_DB,
    gold_db=DEFAULT_GOLD_DB,
    gold_output=DEFAULT_GOLD_OUTPUT,
):
    gold_csv = Path(gold_output) / "gold_branch_daily.csv"
    run_id = str(uuid.uuid4())
    started_at = utc_now()
    source_rows = 0
    spark = None
    temp_csv = None

    try:
        # Read only accepted transactions from Silver.
        with sqlite3.connect(
            f"{Path(silver_db).resolve().as_uri()}?mode=ro",
            uri=True,
        ) as connection:
            rows = connection.execute(
                """
                SELECT
                    branch_id,
                    transaction_date,
                    transaction_type,
                    transaction_id,
                    amount
                FROM silver_transactions
                ORDER BY transaction_id
                """
            ).fetchall()

            columns = [
                description[0]
                for description in connection.execute(
                    """
                    SELECT
                        branch_id,
                        transaction_date,
                        transaction_type,
                        transaction_id,
                        amount
                    FROM silver_transactions
                    LIMIT 0
                    """
                ).description
            ]

        source_rows = len(rows)

        # Never replace a previously published report with an empty result.
        if not rows:
            raise ValueError(
                "No accepted Silver transactions found; "
                "existing Gold data will be preserved."
            )

        spark = (
            SparkSession.builder
            .appName("BankingCapstoneGold")
            .master("local[*]")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")

        transactions_df = spark.createDataFrame(rows, columns)

        gold_df = (
            transactions_df
            .groupBy(
                "branch_id",
                "transaction_date",
                "transaction_type",
            )
            .agg(
                F.count("transaction_id").alias("transaction_count"),
                F.sum("amount").alias("total_amount"),
            )
            .orderBy(
                "branch_id",
                "transaction_date",
                "transaction_type",
            )
        )

        gold_rows = gold_df.collect()

        # Validate the complete result before publishing it.
        if not gold_rows:
            raise ValueError("Gold aggregation produced no groups.")

        if sum(row["transaction_count"] for row in gold_rows) != source_rows:
            raise ValueError(
                "Validation failed: Gold transaction counts "
                "do not reconcile with Silver."
            )

        for row in gold_rows:
            if (
                not row["branch_id"]
                or not row["transaction_date"]
                or row["transaction_type"] not in ("CREDIT", "DEBIT")
                or row["transaction_count"] <= 0
                or row["total_amount"] is None
                or not row["total_amount"] >= 0
            ):
                raise ValueError(
                    f"Invalid Gold group detected: {row}"
                )

        print("\nValidated Gold aggregation:")
        gold_df.show(truncate=False)

        gold_output = Path(gold_output)
        gold_output.mkdir(parents=True, exist_ok=True)

        # Stage the CSV first. It is not the published file yet.
        temp_csv = gold_output / f".gold_{run_id}.tmp"
        csv_columns = [
            "branch_id",
            "transaction_date",
            "transaction_type",
            "transaction_count",
            "total_amount",
            "published_run_id",
        ]

        with temp_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(csv_columns)

            for row in gold_rows:
                writer.writerow([
                    row["branch_id"],
                    row["transaction_date"],
                    row["transaction_type"],
                    row["transaction_count"],
                    round(float(row["total_amount"]), 2),
                    run_id,
                ])

        # Replace the Gold table atomically within SQLite.
        # Any database error rolls back the table replacement.
        with sqlite3.connect(gold_db) as connection:
            connection.execute("BEGIN IMMEDIATE")

            connection.execute("DELETE FROM gold_branch_daily")

            connection.executemany(
                """
                INSERT INTO gold_branch_daily (
                    branch_id,
                    transaction_date,
                    transaction_type,
                    transaction_count,
                    total_amount,
                    published_run_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["branch_id"],
                        row["transaction_date"],
                        row["transaction_type"],
                        row["transaction_count"],
                        float(row["total_amount"]),
                        run_id,
                    )
                    for row in gold_rows
                ],
            )

            connection.execute(
                """
                INSERT INTO gold_run_audit (
                    run_id, status, started_at, completed_at,
                    source_rows, gold_groups, error_message
                )
                VALUES (?, 'SUCCESS', ?, ?, ?, ?, NULL)
                """,
                (
                    run_id,
                    started_at,
                    utc_now(),
                    source_rows,
                    len(gold_rows),
                ),
            )

            # Publish the staged CSV before committing the DB transaction.
            # If this fails, SQLite rolls back the table replacement.
            os.replace(temp_csv, gold_csv)
            temp_csv = None

            connection.commit()

        print(f"\nGold publication successful.")
        print(f"Run ID: {run_id}")
        print(f"Silver transactions: {source_rows}")
        print(f"Gold groups: {len(gold_rows)}")
        print(f"Gold database: {gold_db}")
        print(f"Gold CSV: {gold_csv}")

        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "source_rows": source_rows,
            "gold_groups": len(gold_rows),
        }

    except Exception as error:
        if temp_csv is not None and temp_csv.exists():
            temp_csv.unlink()

        try:
            record_failed_run(
                run_id,
                started_at,
                str(error),
                source_rows,
                gold_db,
            )
        except Exception as audit_error:
            print(f"Could not record failed run: {audit_error}")

        print(f"Gold publication failed: {error}")
        raise

    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    main()
