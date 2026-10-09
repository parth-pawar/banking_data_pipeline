from pyspark.sql.functions import avg, count, sum

from src.spark.load_data import create_spark_session, load_table_from_sqlite


PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
PARQUET_PATH = PROJECT_ROOT / "output" / "spark" / "parquet" / "branch_summary"


def main():
    spark = create_spark_session("BankingParquet")

    transactions_df = load_table_from_sqlite(
        spark,
        "transactions",
        [
            "transaction_id",
            "account_id",
            "transaction_date",
            "transaction_type",
            "amount",
            "currency",
            "source_file",
        ],
    )

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

    branches_df = load_table_from_sqlite(
        spark,
        "branch",
        [
            "branch_id",
            "branch_name",
            "city",
            "state",
        ],
    )

    # Join transactions to accounts using account_id.
    transactions_accounts_df = transactions_df.join(
        accounts_df,
        "account_id",
        "inner",
    )

    # Join branch information using branch_id.
    joined_df = transactions_accounts_df.join(
        branches_df,
        "branch_id",
        "inner",
    )

    # Create a meaningful analytical DataFrame for Parquet storage.
    branch_summary_df = joined_df.groupBy(
        "branch_id",
        "branch_name",
    ).agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_transaction_amount"),
        avg("amount").alias("average_transaction_amount"),
    )

    expected_count = branch_summary_df.count()

    print("\nBranch Summary:")
    branch_summary_df.show()

    print("Expected row count:", expected_count)

    # Write the analytical DataFrame to Parquet.
    branch_summary_df.write.mode("overwrite").parquet(
        str(PARQUET_PATH)
    )

    print("\nParquet write completed.")

    # Read the Parquet data back into Spark.
    read_back_df = spark.read.parquet(
        str(PARQUET_PATH)
    )

    read_back_count = read_back_df.count()

    print("Read-back row count:", read_back_count)

    if read_back_count == expected_count:
        print("Parquet validation: PASS")
    else:
        print("Parquet validation: FAIL")

    print("\nRead-Back Data:")
    read_back_df.show()

    spark.stop()


if __name__ == "__main__":
    main()