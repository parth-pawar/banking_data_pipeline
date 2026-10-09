
import os
import sqlite3
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql.functions import coalesce, try_to_date


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_FILE = PROJECT_ROOT / "database" / "banking.db"


def create_spark_session(app_name):
    """Create and return a local Spark session."""
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .getOrCreate()
    )


def load_table_from_sqlite(spark, table_name, columns):
    """Load a SQLite table into a Spark DataFrame."""
    connection = sqlite3.connect(DATABASE_FILE)

    rows = connection.execute(
        f"SELECT * FROM {table_name}"
    ).fetchall()

    connection.close()

    dataframe = spark.createDataFrame(rows, columns)

    if table_name == "transactions":
        dataframe = dataframe.withColumn(
            "transaction_date",
            coalesce(
                try_to_date("transaction_date", "yyyy-MM-dd"),
                try_to_date("transaction_date", "M/d/yyyy"),
            ),
        )

    return dataframe


def inspect_dataframe(name, dataframe, sample_rows=5):
    """Display sample rows, schema, and row count."""
    print(f"\n{name}:")
    dataframe.show(sample_rows)
    dataframe.printSchema()
    print(f"{name} count:", dataframe.count())


def main():
    spark = create_spark_session("BankingDataLoad")

    customers_df = load_table_from_sqlite(
        spark,
        "customer",
        [
            "customer_id",
            "customer_name",
            "email",
            "customer_segment",
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

    inspect_dataframe("Customers", customers_df)
    inspect_dataframe("Branches", branches_df)
    inspect_dataframe("Accounts", accounts_df)
    inspect_dataframe("Transactions", transactions_df)

    spark.stop()


if __name__ == "__main__":
    main()
