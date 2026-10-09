from pathlib import Path

from src.spark.load_data import create_spark_session


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSACTIONS_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "synthetic_transactions.csv"
)


def main():
    spark = create_spark_session("BankingSparkSQL")

    # Load the generated transactions.
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

    # Register the DataFrame as a temporary SQL view.
    transactions_df.createOrReplaceTempView("transactions")

    # DataFrame API version
    from pyspark.sql.functions import avg, count, sum

    dataframe_summary_df = transactions_df.groupBy(
        "transaction_type"
    ).agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_amount"),
        avg("amount").alias("average_amount"),
    )

    print("\nDataFrame API Summary by Transaction Type:")
    dataframe_summary_df.show()

    # Spark SQL version
    sql_summary_df = spark.sql("""
        SELECT
            transaction_type,
            COUNT(transaction_id) AS transaction_count,
            SUM(amount) AS total_amount,
            AVG(amount) AS average_amount
        FROM transactions
        GROUP BY transaction_type
    """)

    print("\nSpark SQL Summary by Transaction Type:")
    sql_summary_df.show()

    spark.stop()


if __name__ == "__main__":
    main()