from pyspark.sql import functions as F

from src.spark.analytics import summary_by_transaction_type
from src.spark.data_quality import (
    count_duplicate_ids,
    count_nulls,
    count_orphans,
)
from src.spark.transformations import credit_transactions


def test_expected_row_count(banking_data):
    transactions_df, _ = banking_data

    assert transactions_df.count() == 4


def test_credit_count(banking_data):
    transactions_df, _ = banking_data

    credits_df = credit_transactions(transactions_df)

    assert credits_df.count() == 2


def test_credit_total(banking_data):
    transactions_df, _ = banking_data

    summary_df = summary_by_transaction_type(transactions_df)

    credit_total = (
        summary_df
        .filter(F.col("transaction_type") == "CREDIT")
        .select("total_transaction_amount")
        .first()[0]
    )

    assert credit_total == 300.0


def test_duplicate_ids(banking_data):
    transactions_df, _ = banking_data

    # Deliberately add T001 a second time to test duplicate detection.
    duplicate_test_df = transactions_df.union(
        transactions_df.filter(F.col("transaction_id") == "T001")
    )

    duplicate_count = count_duplicate_ids(
        duplicate_test_df,
        "transaction_id",
    )

    assert duplicate_count == 1


def test_null_values(banking_data):
    transactions_df, _ = banking_data

    assert count_nulls(transactions_df, "transaction_id") == 0
    assert count_nulls(transactions_df, "account_id") == 0
    assert count_nulls(transactions_df, "amount") == 0


def test_join_integrity(banking_data):
    transactions_df, accounts_df = banking_data

    invalid_accounts = count_orphans(
        transactions_df,
        accounts_df,
        "account_id",
    )

    assert invalid_accounts == 0
