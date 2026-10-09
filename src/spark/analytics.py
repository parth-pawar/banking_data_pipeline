from pyspark.sql.functions import avg, count, max, min, sum
from src.spark.load_data import create_spark_session, load_table_from_sqlite


def main():
    spark = create_spark_session("BankingAggregations")

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

# JOINS 

    # Join transactions to accounts using account_id.
    transactions_accounts_df = transactions_df.join(
        accounts_df,
        "account_id",
        "inner",
    )

    # Join customer information using customer_id.
    transactions_accounts_customers_df = transactions_accounts_df.join(
        customers_df,
        "customer_id",
        "inner",
    )

    # Join branch information using branch_id.
    final_joined_df = transactions_accounts_customers_df.join(
        branches_df,
        "branch_id",
        "inner",
    )



# Part 3

    # Requirement 1: Summary by transaction type
    transaction_type_summary_df = transactions_df.groupBy(
        "transaction_type"
    ).agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_transaction_amount"),
        avg("amount").alias("average_transaction_amount"),
    )

    print("\nSummary by Transaction Type:")
    transaction_type_summary_df.show()

    # Requirement 2: Summary by account
    account_summary_df = transactions_df.groupBy(
        "account_id"
    ).agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_transaction_amount"),
        avg("amount").alias("average_transaction_amount"),
    )

    print("\nSummary by Account:")
    account_summary_df.show()


    # Requirement 3: Summary by branch
    branch_summary_df = final_joined_df.groupBy(
    "branch_id",
    "branch_name",
    ).agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_transaction_amount"),
        avg("amount").alias("average_transaction_amount"),
    )

    print("\nSummary by Branch:")
    branch_summary_df.show()



# Part 4

    # Customer with highest transaction value
    customer_totals_df = final_joined_df.groupBy(
        "customer_id",
        "customer_name",
    ).agg(
        sum("amount").alias("total_transaction_amount")
    ).orderBy(
        "total_transaction_amount",
        ascending=False,
    )

    print("\nCustomers by Total Transaction Amount:")
    customer_totals_df.show()


    # Branch transaction amount range
    branch_amount_range_df = final_joined_df.groupBy(
    "branch_id",
    "branch_name",
    ).agg(
        min("amount").alias("minimum_transaction_amount"),
        max("amount").alias("maximum_transaction_amount"),
    )

    print("\nTransaction Amount Range by Branch:")
    branch_amount_range_df.show()



    # High-value customer transactions
    high_value_customer_transactions_df = final_joined_df.filter(
    final_joined_df.amount >= 500
    ).select(
        "transaction_id",
        "customer_name",
        "account_id",
        "branch_name",
        "transaction_type",
        "amount",
    )

    print("\nHigh-Value Customer Transactions:")
    high_value_customer_transactions_df.show()


    # Account type with highest average transaction
    account_type_average_df = final_joined_df.groupBy(
    "account_type"
    ).agg(
        avg("amount").alias("average_transaction_amount")
    ).orderBy(
        "average_transaction_amount",
        ascending=False,
    )

    print("\nAverage Transaction Amount by Account Type:")
    account_type_average_df.show()
    spark.stop()


if __name__ == "__main__":
    main()

