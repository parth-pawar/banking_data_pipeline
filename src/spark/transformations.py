
from pyspark.sql import functions as F

from src.spark.load_data import (
    create_spark_session,
    load_transactions,
)


HIGH_VALUE_THRESHOLD = 500.0


def credit_transactions(df):
    """Return CREDIT transactions only."""
    return df.filter(F.col("transaction_type") == "CREDIT")


def high_value_transactions(df, threshold=HIGH_VALUE_THRESHOLD):
    """Return transactions whose amount meets the high-value threshold."""
    return df.filter(F.col("amount") >= threshold)


def reporting_columns(df):
    """Select the columns required for transaction reporting."""
    return df.select(
        "transaction_id",
        "account_id",
        "transaction_date",
        "transaction_type",
        "amount",
        "currency",
    )


def add_transaction_value_category(df, threshold=HIGH_VALUE_THRESHOLD):
    """Classify transactions as HIGH_VALUE or NORMAL."""
    return df.withColumn(
        "transaction_value_category",
        F.when(
            F.col("amount") >= threshold,
            "HIGH_VALUE",
        ).otherwise("NORMAL"),
    )


def transform_transactions(df, threshold=HIGH_VALUE_THRESHOLD):
    """Build the final transaction reporting DataFrame."""
    return add_transaction_value_category(
        reporting_columns(df),
        threshold,
    )


def main():
    spark = create_spark_session("BankingTransformations")

    try:
        transactions_df = load_transactions(spark)

        # Requirement 1: CREDIT-only transactions
        credits_df = credit_transactions(transactions_df)

        print("\nCREDIT Transactions:")
        credits_df.show()
        print("CREDIT transaction count:", credits_df.count())

        # Requirement 2: High-value transactions
        high_value_df = high_value_transactions(transactions_df)

        print("\nHigh-Value Transactions:")
        high_value_df.show()
        print(
            f"High-value transaction count "
            f"(>= {HIGH_VALUE_THRESHOLD}):",
            high_value_df.count(),
        )

        # Requirement 3: Selected reporting columns
        reporting_df = reporting_columns(transactions_df)

        print("\nTransaction Reporting Dataset:")
        reporting_df.show()

        # Requirement 4: Derived column
        final_reporting_df = transform_transactions(
            transactions_df,
            HIGH_VALUE_THRESHOLD,
        )

        print(
            "\nTransaction Reporting Dataset "
            "With transaction_value_category:"
        )
        final_reporting_df.show()

        print("\nReporting Dataset Schema:")
        final_reporting_df.printSchema()

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
