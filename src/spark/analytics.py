
from pyspark.sql import functions as F

from src.spark.load_data import (
    create_spark_session,
    load_accounts,
    load_branches,
    load_customers,
    load_transactions,
)

HIGH_VALUE_THRESHOLD = 500.0


def join_transaction_details(transactions, accounts, customers, branches):
    """Join transactions with account, customer, and branch information."""
    return (
        transactions
        .join(accounts, on="account_id", how="inner")
        .join(customers, on="customer_id", how="inner")
        .join(branches, on="branch_id", how="inner")
    )


def summary_by_transaction_type(transactions):
    """Summarize transaction counts and amounts by transaction type."""
    return (
        transactions
        .groupBy("transaction_type")
        .agg(
            F.count("transaction_id").alias("transaction_count"),
            F.sum("amount").alias("total_transaction_amount"),
            F.avg("amount").alias("average_transaction_amount"),
        )
        .orderBy("transaction_type")
    )


def summary_by_account(transactions):
    """Summarize transaction counts and amounts by account."""
    return (
        transactions
        .groupBy("account_id")
        .agg(
            F.count("transaction_id").alias("transaction_count"),
            F.sum("amount").alias("total_transaction_amount"),
            F.avg("amount").alias("average_transaction_amount"),
        )
        .orderBy("account_id")
    )


def summary_by_branch(joined_transactions):
    """Summarize transaction counts and amounts by branch."""
    return (
        joined_transactions
        .groupBy("branch_id", "branch_name")
        .agg(
            F.count("transaction_id").alias("transaction_count"),
            F.sum("amount").alias("total_transaction_amount"),
            F.avg("amount").alias("average_transaction_amount"),
        )
        .orderBy("branch_id")
    )


def customer_transaction_totals(joined_transactions):
    """Rank customers by their total transaction amount."""
    return (
        joined_transactions
        .groupBy("customer_id", "customer_name")
        .agg(
            F.sum("amount").alias("total_transaction_amount")
        )
        .orderBy("total_transaction_amount", ascending=False)
    )


def branch_transaction_amount_range(joined_transactions):
    """Find the minimum and maximum transaction amounts per branch."""
    return (
        joined_transactions
        .groupBy("branch_id", "branch_name")
        .agg(
            F.min("amount").alias("minimum_transaction_amount"),
            F.max("amount").alias("maximum_transaction_amount"),
        )
        .orderBy("branch_id")
    )


def high_value_customer_transactions(
    joined_transactions,
    threshold=HIGH_VALUE_THRESHOLD,
):
    """Return high-value transactions with customer and branch details."""
    return (
        joined_transactions
        .filter(F.col("amount") >= threshold)
        .select(
            "transaction_id",
            "customer_name",
            "account_id",
            "branch_name",
            "transaction_type",
            "amount",
        )
        .orderBy("transaction_id")
    )


def average_transaction_by_account_type(joined_transactions):
    """Rank account types by their average transaction amount."""
    return (
        joined_transactions
        .groupBy("account_type")
        .agg(
            F.avg("amount").alias("average_transaction_amount")
        )
        .orderBy("average_transaction_amount", ascending=False)
    )


def main():
    spark = create_spark_session("BankingAggregations")

    try:
        # Load the required tables.
        transactions = load_transactions(spark)
        accounts = load_accounts(spark)
        customers = load_customers(spark)
        branches = load_branches(spark)

        # Join the tables once for reports requiring descriptive details.
        joined_transactions = join_transaction_details(
            transactions,
            accounts,
            customers,
            branches,
        )

        # Requirement 1: Summary by transaction type.
        print("\nSummary by Transaction Type:")
        summary_by_transaction_type(transactions).show()

        # Requirement 2: Summary by account.
        print("\nSummary by Account:")
        summary_by_account(transactions).show()

        # Requirement 3: Summary by branch.
        print("\nSummary by Branch:")
        summary_by_branch(joined_transactions).show()

        # Requirement 4: Customers ranked by total transaction amount.
        print("\nCustomers by Total Transaction Amount:")
        customer_transaction_totals(joined_transactions).show()

        # Requirement 5: Transaction amount range by branch.
        print("\nTransaction Amount Range by Branch:")
        branch_transaction_amount_range(joined_transactions).show()

        # Requirement 6: High-value customer transactions.
        print("\nHigh-Value Customer Transactions:")
        high_value_customer_transactions(
            joined_transactions,
            HIGH_VALUE_THRESHOLD,
        ).show()

        # Requirement 7: Average transaction amount by account type.
        print("\nAverage Transaction Amount by Account Type:")
        average_transaction_by_account_type(joined_transactions).show()

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
