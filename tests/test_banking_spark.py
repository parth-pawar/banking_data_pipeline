from pyspark.sql.functions import col, count


def test_expected_row_count(banking_data):
    transactions_df, _ = banking_data

    assert transactions_df.count() == 4


def test_credit_count(banking_data):
    transactions_df, _ = banking_data

    credit_count = transactions_df.filter(
        col("transaction_type") == "CREDIT"
    ).count()

    assert credit_count == 2


def test_credit_total(banking_data):
    transactions_df, _ = banking_data

    credit_total = (
        transactions_df
        .filter(col("transaction_type") == "CREDIT")
        .agg({"amount": "sum"})
        .collect()[0][0]
    )

    assert credit_total == 300.0


def test_duplicate_ids(banking_data):
    transactions_df, _ = banking_data

    # Deliberately add T001 a second time to test duplicate detection.
    duplicate_test_df = transactions_df.union(
        transactions_df.filter(
            col("transaction_id") == "T001"
        )
    )

    duplicate_count = (
        duplicate_test_df
        .groupBy("transaction_id")
        .agg(count("*").alias("occurrence_count"))
        .filter(col("occurrence_count") > 1)
        .count()
    )

    assert duplicate_count == 1


def test_null_values(banking_data):
    transactions_df, _ = banking_data

    null_transaction_ids = transactions_df.filter(
        col("transaction_id").isNull()
    ).count()

    null_account_ids = transactions_df.filter(
        col("account_id").isNull()
    ).count()

    null_amounts = transactions_df.filter(
        col("amount").isNull()
    ).count()

    assert null_transaction_ids == 0
    assert null_account_ids == 0
    assert null_amounts == 0


def test_join_integrity(banking_data):
    transactions_df, accounts_df = banking_data

    invalid_accounts = transactions_df.join(
        accounts_df,
        "account_id",
        "left_anti",
    ).count()

    assert invalid_accounts == 0