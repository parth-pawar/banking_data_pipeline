
from pathlib import Path

from pyspark.sql import functions as F

from src.spark.load_data import create_spark_session
from src.spark.generated_transactions_analysis import (
    load_generated_transactions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSACTIONS_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "synthetic_transactions.csv"
)


def summary_by_transaction_type(transactions):
    """Summarize transactions using the DataFrame API."""
    return (
        transactions.groupBy("transaction_type")
        .agg(
            F.count("transaction_id").alias("transaction_count"),
            F.sum("amount").alias("total_amount"),
            F.avg("amount").alias("average_amount"),
        )
        .orderBy("transaction_type")
    )


def summary_by_transaction_type_sql(spark):
    """Summarize transactions using Spark SQL."""
    return spark.sql("""
        SELECT
            transaction_type,
            COUNT(transaction_id) AS transaction_count,
            SUM(amount) AS total_amount,
            AVG(amount) AS average_amount
        FROM transactions
        GROUP BY transaction_type
        ORDER BY transaction_type
    """)


def main():
    spark = create_spark_session("BankingSparkSQL")

    try:
        # Load the generated transactions.
        transactions = load_generated_transactions(
            spark,
            TRANSACTIONS_FILE,
        )

        # Register the DataFrame as a temporary SQL view.
        transactions.createOrReplaceTempView("transactions")

        # DataFrame API version.
        dataframe_summary = summary_by_transaction_type(transactions)

        print("\nDataFrame API Summary by Transaction Type:")
        dataframe_summary.show()

        # Spark SQL version.
        sql_summary = summary_by_transaction_type_sql(spark)

        print("\nSpark SQL Summary by Transaction Type:")
        sql_summary.show()

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
