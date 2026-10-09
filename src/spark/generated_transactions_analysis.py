from pathlib import Path

from pyspark.sql.functions import avg, col, count, sum, to_date

from src.spark.load_data import (
    create_spark_session,
    load_table_from_sqlite,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSACTIONS_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "synthetic_transactions.csv"
)


def main():
    spark = create_spark_session("BankingLargerDataAnalysis")

    # Step 1: Load the 100,000 generated transactions.
    transactions_df = (
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
        .csv(str(TRANSACTIONS_FILE))
    )

    # Convert the transaction date from a string to a Spark date.
    transactions_df = transactions_df.withColumn(
        "transaction_date",
        to_date(col("transaction_date"), "yyyy-MM-dd"),
    )

    print("\nLarger Dataset")
    print("Transaction count:", transactions_df.count())

    print(
    "Transaction partitions:",
    transactions_df.rdd.getNumPartitions(),
    )

    print("\nSample Transactions:")
    transactions_df.show(5, truncate=False)

    # Step 2: Filter transactions of USD 500 or more.
    high_value_df = transactions_df.filter(
        col("amount") >= 500
    )

    print("\nHigh-Value Transactions")
    print("Threshold: USD 500 or more")
    print("High-value count:", high_value_df.count())

    # Step 3: Aggregate transactions by transaction type.
    transaction_summary_df = transactions_df.groupBy(
        "transaction_type"
    ).agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_amount"),
        avg("amount").alias("average_amount"),
    )

    print("\nSummary by Transaction Type:")
    transaction_summary_df.show()

    # Step 4: Load the existing account reference data.
    accounts_df = load_table_from_sqlite(
        spark,
        "account",
        [
            "account_id",
            "customer_id",
            "branch_id",
            "account_type",
            "account_status",
        ],
    )

    # Step 5: Join generated transactions with real account records.
    joined_df = transactions_df.join(
        accounts_df,
        "account_id",
        "inner",
    )

    # Step 6: Analyse generated transactions by account type.
    account_type_summary_df = joined_df.groupBy(
        "account_type"
    ).agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_amount"),
        avg("amount").alias("average_amount"),
    )

    print("\nSummary by Account Type:")
    account_type_summary_df.show()

    print(
        "Joined transaction count:",
        joined_df.count(),
    )

    spark.stop()


if __name__ == "__main__":
    main()