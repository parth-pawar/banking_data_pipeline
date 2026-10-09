
from pyspark.sql.functions import when

from src.spark.load_data import create_spark_session, load_table_from_sqlite


def main():
    spark = create_spark_session("BankingTransformations")

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

    # Requirement 1: CREDIT-only transactions
    credit_transactions_df = transactions_df.filter(
        transactions_df.transaction_type == "CREDIT"
    )

    print("\nCREDIT Transactions:")
    credit_transactions_df.show()

    print(
        "CREDIT transaction count:",
        credit_transactions_df.count()
    )

    # Requirement 2: High-value transactions
    high_value_threshold = 500

    high_value_transactions_df = transactions_df.filter(
        transactions_df.amount >= high_value_threshold
    )

    print("\nHigh-Value Transactions:")
    high_value_transactions_df.show()

    print(
        "High-value transaction count:",
        high_value_transactions_df.count()
    )

    # Requirement 3: Selected reporting columns
    reporting_df = transactions_df.select(
        "transaction_id",
        "account_id",
        "transaction_date",
        "transaction_type",
        "amount",
        "currency",
    )

    print("\nTransaction Reporting Dataset:")
    reporting_df.show()

    # Requirement 4: Derived column
    reporting_df = reporting_df.withColumn(
        "transaction_value_category",
        when(
            reporting_df.amount >= high_value_threshold,
            "HIGH_VALUE"
        ).otherwise("NORMAL"),

    )

    print("\nTransaction Reporting Dataset With transaction_value_category:")
    reporting_df.show()

    print("\nReporting Dataset Schema:")
    reporting_df.printSchema()

    spark.stop()


if __name__ == "__main__":
    main()
