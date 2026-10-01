import pandas as pd
import shutil

from src.ingestion.pipeline import run_pipeline

# integration test 
# tmp_path is a pytest fixture that provides a temporary directory for the test to use. 
def test_missing_required_column_is_skipped(tmp_path):
    input_dir = tmp_path / "input"
    validated_dir = tmp_path / "validated"
    output_dir = tmp_path / "output"

    input_dir.mkdir()

    data = pd.DataFrame({
        "transaction_id": ["T1001"],
        "account_id": ["A1001"],
        "transaction_date": ["2026-09-10"],
        "transaction_type": ["CREDIT"],
        "amount": [100],
        # currency column is intentionally missing
    })

    data.to_csv(
        input_dir / "missing_currency.csv",
        index=False
    )

    run_pipeline(
    input_dir=str(input_dir),
    validated_dir=str(validated_dir),
    output_dir=str(output_dir)
    )

    dq_summary = pd.read_csv(
    output_dir / "dq" / "dq_summary.csv"
    )

    skipped_files = dq_summary.loc[
        dq_summary["metric"] == "files skipped",
        "count"
    ].iloc[0]

    assert skipped_files == 1




# integration test 
# We dont create output_dir as its created by the pipeline. 
def test_multiple_row_errors_are_preserved(tmp_path):
    input_dir = tmp_path / "input"
    validated_dir = tmp_path / "validated"
    output_dir = tmp_path / "output"

    input_dir.mkdir()

    data = pd.DataFrame({
        "transaction_id": ["T1001"],
        "account_id": ["A1001"],
        "transaction_date": ["2026-02-30"],
        "transaction_type": ["TRANSFER"],
        "amount": [-100],
        "currency": ["EUR"],
    })

    data.to_csv(
        input_dir / "multiple_errors.csv",
        index=False
    )

    run_pipeline(
    input_dir=str(input_dir),
    validated_dir=str(validated_dir),
    output_dir=str(output_dir)
    )

    invalid_transactions = pd.read_csv(
    validated_dir / "invalid_transactions.csv"
)

    error_reason = invalid_transactions.loc[
        0,
        "error_reason"
    ]

    assert "invalid transaction_type" in error_reason
    assert "amount must be greater than 0" in error_reason
    assert "invalid transaction_date" in error_reason
    assert "currency must be USD" in error_reason



# regression test to ensure that the original branch files produce the expected summary counts.
def test_original_branch_files_regression(tmp_path):
    input_dir = tmp_path / "input"
    validated_dir = tmp_path / "validated"
    output_dir = tmp_path / "output"

    input_dir.mkdir()

    original_files = [
        "data/raw/BR001_20260906_TRANSACTION.csv",
        "data/raw/BR002_20260906_TRANSACTION.csv",
        "data/raw/BR003_20260906_TRANSACTION.csv",
    ]

    for file in original_files:
        shutil.copy(file, input_dir)

    run_pipeline(
    input_dir=str(input_dir),
    validated_dir=str(validated_dir),
    output_dir=str(output_dir)
)

    summary = pd.read_csv(
    output_dir / "summaries" / "summary.csv"
    )

    total_records = summary.loc[
        summary["metric"] == "total input records",
        "count"
    ].iloc[0]

    valid_records = summary.loc[
        summary["metric"] == "valid records",
        "count"
    ].iloc[0]

    invalid_records = summary.loc[
        summary["metric"] == "invalid records",
        "count"
    ].iloc[0]

    assert total_records == 24
    assert valid_records == 10
    assert invalid_records == 14