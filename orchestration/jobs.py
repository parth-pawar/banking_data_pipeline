import dagster as dg

from orchestration.ops import (
    extract_sqlite,
    validate_banking_data,
    run_transformations,
    analyze_transactions,
    analyze_customers,
    analyze_branches,
    analyze_account_types,
    publish_reports,
)


@dg.job
def banking_pipeline_job():
    # Stage 1: Extract data from SQLite.
    extraction = extract_sqlite()

    # Stage 2: Validate the extracted banking data.
    validation = validate_banking_data(extraction)

    # Stage 3: Transform transactions.
    transformations = run_transformations(validation)

    # Stage 4: Analyze transactions by type and account.
    transaction_analytics = analyze_transactions(validation)

    # Stage 5: Analyze customer transactions.
    customer_analytics = analyze_customers(validation)

    # Stage 6: Analyze transaction amount ranges by branch.
    branch_analytics = analyze_branches(validation)

    # Stage 7: Analyze transactions by account type.
    account_type_analytics = analyze_account_types(validation)

    # Stage 8: Publish all reports after upstream stages succeed.
    publish_reports(
        extraction,
        transformations,
        transaction_analytics,
        customer_analytics,
        branch_analytics,
        account_type_analytics,
    )
