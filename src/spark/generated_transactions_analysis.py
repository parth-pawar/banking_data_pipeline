
from pathlib import Path

from pyspark.sql import functions as F

from src.spark.load_data import (
    create_spark_session,
    load_accounts,
)

from src.spark.transformations import high_value_transactions


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSACTIONS_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "synthetic_transactions.csv"
)

HIGH_VALUE_THRESHOLD = 500.0


def load_generated_transactions(spark, file_path=TRANSACTIONS_FILE):
    """Load generated transactions from CSV into a Spark DataFrame."""
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Generated transactions file not found: {file_path}"
        )

    transactions = (
        spark.read
        .option("header", True)
        .schema(
            """
            transaction_id STRING,
            account_id STRING,
            transaction_date STRING,
            transaction_type STRING,
            amount DOUBLE,
            currency STRING,
            source_file STRING
            """
        )
        .csv(str(file_path))
    )

    return transactions.withColumn(
        "transaction_date",
        F.to_date(F.col("transaction_date"), "yyyy-MM-dd"),
    )


def summary_by_transaction_type(transactions):
    """Summarize transaction counts and amounts by transaction type."""
    return (
        transactions.groupBy("transaction_type")
        .agg(
            F.count("transaction_id").alias("transaction_count"),
            F.sum("amount").alias("total_amount"),
            F.avg("amount").alias("average_amount"),
        )
        .orderBy("transaction_type")
    )


def join_with_accounts(transactions, accounts):
    """Join generated transactions with their account reference data."""
    return transactions.join(
        accounts,
        on="account_id",
        how="inner",
    )


def summary_by_account_type(joined_transactions):
    """Summarize transactions by account type."""
    return (
        joined_transactions.groupBy("account_type")
        .agg(
            F.count("transaction_id").alias("transaction_count"),
            F.sum("amount").alias("total_amount"),
            F.avg("amount").alias("average_amount"),
        )
        .orderBy("account_type")
    )


def main():
    spark = create_spark_session("BankingLargerDataAnalysis")

    try:
        # Step 1: Load the generated transactions.
        transactions = load_generated_transactions(spark)

        print("\nLarger Dataset")
        print("Transaction count:", transactions.count())
        print(
            "Transaction partitions:",
            transactions.rdd.getNumPartitions(),
        )

        print("\nSample Transactions:")
        transactions.show(5, truncate=False)

        # Step 2: Identify high-value transactions.
        high_value = high_value_transactions(transactions)

        print("\nHigh-Value Transactions")
        print(f"Threshold: USD {HIGH_VALUE_THRESHOLD:.2f} or more")
        print("High-value count:", high_value.count())

        # Step 3: Summarize transactions by transaction type.
        print("\nSummary by Transaction Type:")
        summary_by_transaction_type(transactions).show()

        # Step 4: Load account reference data from SQLite.
        accounts = load_accounts(spark)

        # Step 5: Join transactions with account records.
        joined = join_with_accounts(transactions, accounts)

        # Step 6: Summarize transactions by account type.
        print("\nSummary by Account Type:")
        summary_by_account_type(joined).show()

        print("Joined transaction count:", joined.count())

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
