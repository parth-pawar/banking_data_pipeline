from pyspark.sql.functions import col, count

from src.spark.load_data import create_spark_session, load_table_from_sqlite


def print_check_result(check_name, bad_count, description):
    status = "PASS" if bad_count == 0 else "FAIL"
    print(f"{check_name}: {status} - {bad_count} {description}")


def main():
    spark = create_spark_session("BankingDataQuality")

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

    print("\nData Quality Checks:")

    # Check 1: Null transaction IDs
    null_transaction_ids = transactions_df.filter(
        col("transaction_id").isNull()
    ).count()

    print_check_result(
        "Null transaction IDs",
        null_transaction_ids,
        "bad records",
    )

    # Check 2: Null account IDs
    null_account_ids = transactions_df.filter(
        col("account_id").isNull()
    ).count()

    print_check_result(
        "Null account IDs",
        null_account_ids,
        "bad records",
    )

    # Check 3: Null amounts
    null_amounts = transactions_df.filter(
        col("amount").isNull()
    ).count()

    print_check_result(
        "Null amounts",
        null_amounts,
        "bad records",
    )

    # Check 4: Duplicate transaction IDs
    duplicate_transaction_ids = (
        transactions_df
        .groupBy("transaction_id")
        .agg(count("*").alias("occurrence_count"))
        .filter(col("occurrence_count") > 1)
        .count()
    )

    print_check_result(
        "Duplicate transaction IDs",
        duplicate_transaction_ids,
        "duplicate IDs",
    )

    # Check 5: Transactions referencing nonexistent accounts
    invalid_transaction_accounts = transactions_df.join(
        accounts_df,
        "account_id",
        "left_anti",
    ).count()

    print_check_result(
        "Transactions with nonexistent accounts",
        invalid_transaction_accounts,
        "bad records",
    )

    # Check 6: Accounts referencing nonexistent customers
    invalid_account_customers = accounts_df.join(
        customers_df,
        "customer_id",
        "left_anti",
    ).count()

    print_check_result(
        "Accounts with nonexistent customers",
        invalid_account_customers,
        "bad records",
    )

    # Check 7: Accounts referencing nonexistent branches
    invalid_account_branches = accounts_df.join(
        branches_df,
        "branch_id",
        "left_anti",
    ).count()

    print_check_result(
        "Accounts with nonexistent branches",
        invalid_account_branches,
        "bad records",
    )

    spark.stop()


if __name__ == "__main__":
    main()