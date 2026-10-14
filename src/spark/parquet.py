from pathlib import Path

from pyspark.sql import functions as F

from src.spark.load_data import (
    create_spark_session,
    load_accounts,
    load_branches,
    load_transactions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARQUET_PATH = (
    PROJECT_ROOT
    / "output"
    / "spark"
    / "parquet"
    / "branch_summary"
)


def create_branch_summary(transactions, accounts, branches):
    """Create a summary of transactions grouped by branch."""
    transactions_accounts = transactions.join(
        accounts,
        on="account_id",
        how="inner",
    )

    joined = transactions_accounts.join(
        branches,
        on="branch_id",
        how="inner",
    )

    return (
        joined.groupBy("branch_id", "branch_name")
        .agg(
            F.count("transaction_id").alias("transaction_count"),
            F.sum("amount").alias("total_transaction_amount"),
            F.avg("amount").alias("average_transaction_amount"),
        )
        .orderBy("branch_id")
    )


def write_parquet(dataframe, output_path=PARQUET_PATH):
    """Write a DataFrame to Parquet, replacing existing output."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe.write.mode("overwrite").parquet(str(output_path))


def validate_parquet(spark, output_path, expected_count):
    """Read Parquet data back and compare its row count."""
    read_back = spark.read.parquet(str(output_path))
    read_back_count = read_back.count()

    print("Expected row count:", expected_count)
    print("Read-back row count:", read_back_count)

    if read_back_count != expected_count:
        raise ValueError(
            "Parquet validation failed: "
            f"expected {expected_count} rows, got {read_back_count}."
        )

    print("Parquet validation: PASS")
    return read_back


def main():
    spark = create_spark_session("BankingParquet")

    try:
        # Step 1: Load the required SQLite tables.
        transactions = load_transactions(spark)
        accounts = load_accounts(spark)
        branches = load_branches(spark)

        # Step 2: Create the branch summary.
        branch_summary = create_branch_summary(
            transactions,
            accounts,
            branches,
        )

        expected_count = branch_summary.count()

        print("\nBranch Summary:")
        branch_summary.show()

        print("Expected row count:", expected_count)

        # Step 3: Write the summary to Parquet.
        write_parquet(branch_summary)
        print("\nParquet write completed.")

        # Step 4: Read the data back and validate it.
        read_back = validate_parquet(
            spark,
            PARQUET_PATH,
            expected_count,
        )

        print("\nRead-Back Data:")
        read_back.show()

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
