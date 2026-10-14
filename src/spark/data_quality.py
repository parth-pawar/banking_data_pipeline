
from pyspark.sql import functions as F

from src.spark.load_data import (
    create_spark_session,
    load_accounts,
    load_branches,
    load_customers,
    load_transactions,
)


def count_nulls(dataframe, column_name):
    """Count records where the specified column is null."""
    return dataframe.filter(
        F.col(column_name).isNull()
    ).count()


def count_duplicate_ids(dataframe, column_name):
    """Count distinct IDs that occur more than once."""
    return (
        dataframe
        .groupBy(column_name)
        .count()
        .filter(F.col("count") > 1)
        .count()
    )


def count_orphans(child_df, parent_df, key):
    """Count non-null child keys with no matching parent key."""
    child_records = child_df.filter(F.col(key).isNotNull())
    parent_keys = parent_df.select(key).distinct()

    return (
        child_records
        .join(parent_keys, on=key, how="left_anti")
        .count()
    )


def count_negative_amounts(transactions):
    """Count transactions with negative amounts."""
    return transactions.filter(
        F.col("amount") < 0
    ).count()


def run_checks(transactions, accounts, customers, branches):
    """Run data-quality checks and return their results."""
    return [
        (
            "Null transaction IDs",
            count_nulls(transactions, "transaction_id"),
        ),
        (
            "Null account IDs",
            count_nulls(transactions, "account_id"),
        ),
        (
            "Null transaction amounts",
            count_nulls(transactions, "amount"),
        ),
        (
            "Duplicate transaction IDs",
            count_duplicate_ids(transactions, "transaction_id"),
        ),
        (
            "Transactions with nonexistent accounts",
            count_orphans(transactions, accounts, "account_id"),
        ),
        (
            "Accounts with nonexistent customers",
            count_orphans(accounts, customers, "customer_id"),
        ),
        (
            "Accounts with nonexistent branches",
            count_orphans(accounts, branches, "branch_id"),
        ),
        (
            "Negative transaction amounts",
            count_negative_amounts(transactions),
        ),
    ]


def print_report(results):
    """Print a summary of data-quality check results."""
    print("\nData Quality Checks:")

    for check_name, bad_count in results:
        status = "PASS" if bad_count == 0 else "FAIL"
        print(f"{status}: {check_name} - {bad_count} bad record(s)")

    passed = sum(1 for _, bad_count in results if bad_count == 0)
    failed = len(results) - passed

    print(f"\nChecks passed: {passed}/{len(results)}")
    print(f"Checks failed: {failed}/{len(results)}")


def validate_data_quality(results):
    """Raise an error if any data-quality check fails."""
    failures = [
        (check_name, bad_count)
        for check_name, bad_count in results
        if bad_count > 0
    ]

    if failures:
        failure_details = "; ".join(
            f"{check_name}: {bad_count} bad record(s)"
            for check_name, bad_count in failures
        )
        raise ValueError(
            f"Data-quality validation failed: {failure_details}"
        )


def main():
    spark = create_spark_session("BankingDataQuality")

    try:
        transactions = load_transactions(spark)
        accounts = load_accounts(spark)
        customers = load_customers(spark)
        branches = load_branches(spark)

        results = run_checks(
            transactions,
            accounts,
            customers,
            branches,
        )

        print_report(results)
        validate_data_quality(results)

        print("\nAll data-quality checks passed.")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
