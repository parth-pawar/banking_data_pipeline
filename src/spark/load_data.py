
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


def create_spark_session(app_name="BankingSpark"):
    """Create and return a local Spark session."""
    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def load_table_from_sqlite(spark, table_name, db_path=DATABASE_FILE):
    """Load an SQLite table into a Spark DataFrame.

    The database is opened in read-only mode.
    A different database path can be supplied for testing.
    """
    database_path = Path(db_path).resolve()

    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database file not found: {database_path}"
        )

    database_uri = f"{database_path.as_uri()}?mode=ro"

    with sqlite3.connect(database_uri, uri=True) as connection:
        cursor = connection.execute(f"SELECT * FROM {table_name}")
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

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


def load_customers(spark, db_path=DATABASE_FILE):
    """Load customer records."""
    return load_table_from_sqlite(spark, "customer", db_path)


def load_branches(spark, db_path=DATABASE_FILE):
    """Load branch records."""
    return load_table_from_sqlite(spark, "branch", db_path)


def load_accounts(spark, db_path=DATABASE_FILE):
    """Load account records."""
    return load_table_from_sqlite(spark, "account", db_path)


def load_transactions(spark, db_path=DATABASE_FILE):
    """Load transaction records and normalize transaction dates."""
    return load_table_from_sqlite(spark, "transactions", db_path)


def inspect_dataframe(name, dataframe, sample_rows=5):
    """Display sample rows, schema, and row count."""
    print(f"\n{name}:")
    dataframe.show(sample_rows)
    dataframe.printSchema()
    print(f"{name} count:", dataframe.count())


def main():
    spark = create_spark_session("BankingDataLoad")

    try:
        dataframes = {
            "Customers": load_customers(spark),
            "Branches": load_branches(spark),
            "Accounts": load_accounts(spark),
            "Transactions": load_transactions(spark),
        }

        for name, dataframe in dataframes.items():
            inspect_dataframe(name, dataframe)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
