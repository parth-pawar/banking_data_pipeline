import csv
from datetime import datetime
from pathlib import Path

import dagster as dg

from src.spark.load_data import (
    create_spark_session,
    load_accounts,
    load_branches,
    load_customers,
    load_transactions,
)
from src.spark.data_quality import run_checks, validate_data_quality
from src.spark.transformations import (
    credit_transactions,
    high_value_transactions,
    reporting_columns,
    add_transaction_value_category,
    transform_transactions,
)
from src.spark.analytics import (
    join_transaction_details,
    summary_by_transaction_type,
    summary_by_account,
    customer_transaction_totals,
    branch_transaction_amount_range,
    high_value_customer_transactions,
    average_transaction_by_account_type,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_ROOT / "database" / "banking.db"

REPORT_DIR = PROJECT_ROOT / "output" / "dagster" / "reports"
LOAD_REPORT_DIR = REPORT_DIR / "load"
TRANSFORM_REPORT_DIR = REPORT_DIR / "transformations"
ANALYTICS_REPORT_DIR = REPORT_DIR / "analytics"

LOG_FILE = PROJECT_ROOT / "output" / "logs" / "week7_pipeline.log"


# ---------------------------------------------------------
# Shared logging and reporting helpers
# ---------------------------------------------------------

def log_stage(context, message, level="info"):
    """Log to Dagster and append to the Week 7 application log."""
    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    formatted_message = f"{timestamp} | {message}"

    getattr(context.log, level)(message)

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(formatted_message + "\n")

    except OSError as exc:
        context.log.warning(
            f"Could not write application log: {exc}"
        )


def dataframe_to_rows(dataframe):
    """Convert a small Spark DataFrame to dictionaries."""
    return [
        row.asDict(recursive=True)
        for row in dataframe.collect()
    ]


def inspect_dataframe(context, name, dataframe):
    """Log the row count and display the DataFrame."""
    count = dataframe.count()

    log_stage(context, f"[INFO] {name}: {count} rows")
    context.log.info(f"Displaying DataFrame: {name}")

    dataframe.show(truncate=False)

    return count


def write_csv_report(context, directory, filename, rows, fieldnames):
    """Write one CSV report, replacing its previous version."""
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / filename
    temporary_path = report_path.with_suffix(".tmp")

    try:
        with temporary_path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="raise",
            )
            writer.writeheader()
            writer.writerows(rows)

        temporary_path.replace(report_path)

    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise

    log_stage(
        context,
        f"[REPORT] {report_path} | rows={len(rows)}",
    )

    return str(report_path)



# ---------------------------------------------------------
# Op 1: Extract SQLite data
# ---------------------------------------------------------

@dg.op(
    config_schema={
        "db_path": dg.Field(str, default_value=str(DATABASE_FILE)),
    },
    retry_policy=dg.RetryPolicy(
        max_retries=2,
        delay=5,
    ),
)

def extract_sqlite(context):
    """Load the four source tables and record their row counts."""
    db_path = Path(context.op_config["db_path"]).resolve()

    log_stage(context, "[START] SQLite extraction")

    spark = None

    try:
        if not db_path.is_file():
            raise FileNotFoundError(
                f"Banking database not found: {db_path}"
            )

        spark = create_spark_session("DagsterBankingExtract")

        tables = {
            "customers": load_customers(spark, db_path),
            "branches": load_branches(spark, db_path),
            "accounts": load_accounts(spark, db_path),
            "transactions": load_transactions(spark, db_path),
        }

        counts = {}

        for name, dataframe in tables.items():
            counts[name] = inspect_dataframe(
                context,
                name,
                dataframe,
            )

        log_stage(
            context,
            "[END] SQLite extraction | status=SUCCESS",
        )

        return {
            "db_path": str(db_path),
            "counts": counts,
        }

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] SQLite extraction: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] SQLite extraction | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()


# ---------------------------------------------------------
# Op 2: Validate banking data
# ---------------------------------------------------------

@dg.op
def validate_banking_data(context, extraction):
    """Run the existing Week 6 data-quality checks."""
    db_path = extraction["db_path"]

    log_stage(context, "[START] Data-quality validation")

    spark = None

    try:
        spark = create_spark_session("DagsterBankingValidation")

        transactions = load_transactions(spark, db_path)
        accounts = load_accounts(spark, db_path)
        customers = load_customers(spark, db_path)
        branches = load_branches(spark, db_path)

        results = run_checks(
            transactions,
            accounts,
            customers,
            branches,
        )

        for check_name, bad_count in results:
            status = "PASS" if bad_count == 0 else "FAIL"

            log_stage(
                context,
                f"[CHECK] {check_name} | "
                f"status={status} | issues={bad_count}",
            )

        # This raises an exception when any check fails.
        validate_data_quality(results)

        log_stage(
            context,
            "[END] Data-quality validation | status=SUCCESS",
        )

        return {
            "db_path": db_path,
            "checks_passed": len(results),
            "checks_failed": 0,
        }

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] Data-quality validation: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] Data-quality validation | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()


# ---------------------------------------------------------
# Op 3: Run transformations
# ---------------------------------------------------------

@dg.op
def run_transformations(context, validation):
    """Generate the five Week 6 transformation outputs."""
    db_path = validation["db_path"]

    log_stage(context, "[START] Transformations")

    spark = None

    try:
        spark = create_spark_session("DagsterBankingTransform")
        transactions = load_transactions(spark, db_path)

        dataframes = {
            "credit_transactions.csv": credit_transactions(
                transactions
            ),
            "high_value_transactions.csv": high_value_transactions(
                transactions
            ),
            "reporting_columns.csv": reporting_columns(
                transactions
            ),
            "transactions_with_value_category.csv": (
                add_transaction_value_category(transactions)
            ),
            "transaction_reporting.csv": transform_transactions(
                transactions
            ),
        }

        reports = {}

        for filename, dataframe in dataframes.items():
            count = inspect_dataframe(
                context,
                filename,
                dataframe,
            )
            reports[filename] = {
            "rows": dataframe_to_rows(dataframe),
            "row_count": count,
            "fieldnames": dataframe.columns,
            }

        log_stage(
            context,
            "[END] Transformations | status=SUCCESS",
        )

        return reports

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] Transformations: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] Transformations | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()


# ---------------------------------------------------------
# Op 4: Analyze transactions and accounts
# ---------------------------------------------------------

@dg.op
def analyze_transactions(context, validation):
    """Calculate transaction-type and account summaries."""
    db_path = validation["db_path"]

    log_stage(context, "[START] Transaction and account analytics")

    spark = None

    try:
        spark = create_spark_session("DagsterTransactionAnalytics")
        transactions = load_transactions(spark, db_path)

        dataframes = {
            "transaction_type_summary.csv": (
                summary_by_transaction_type(transactions)
            ),
            "account_summary.csv": summary_by_account(transactions),
        }

        reports = {}

        for filename, dataframe in dataframes.items():
            count = inspect_dataframe(context, filename, dataframe)
            reports[filename] = {
            "rows": dataframe_to_rows(dataframe),
            "row_count": count,
            "fieldnames": dataframe.columns,
            }
        log_stage(
            context,
            "[END] Transaction and account analytics | status=SUCCESS",
        )

        return reports

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] Transaction and account analytics: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] Transaction and account analytics | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()


# ---------------------------------------------------------
# Op 5: Analyze customers
# ---------------------------------------------------------

@dg.op
def analyze_customers(context, validation):
    """Calculate customer totals and high-value customer details."""
    db_path = validation["db_path"]

    log_stage(context, "[START] Customer analytics")

    spark = None

    try:
        spark = create_spark_session("DagsterCustomerAnalytics")

        transactions = load_transactions(spark, db_path)
        accounts = load_accounts(spark, db_path)
        customers = load_customers(spark, db_path)
        branches = load_branches(spark, db_path)

        joined = join_transaction_details(
            transactions,
            accounts,
            customers,
            branches,
        )

        dataframes = {
            "customer_transaction_totals.csv": (
                customer_transaction_totals(joined)
            ),
            "high_value_customer_transactions.csv": (
                high_value_customer_transactions(joined)
            ),
        }

        reports = {}

        for filename, dataframe in dataframes.items():
            count = inspect_dataframe(context, filename, dataframe)
            reports[filename] = {
            "rows": dataframe_to_rows(dataframe),
            "row_count": count,
            "fieldnames": dataframe.columns,
            }

        log_stage(
            context,
            "[END] Customer analytics | status=SUCCESS",
        )

        return reports

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] Customer analytics: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] Customer analytics | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()


# ---------------------------------------------------------
# Op 6: Analyze branches
# ---------------------------------------------------------

@dg.op
def analyze_branches(context, validation):
    """Calculate transaction amount ranges by branch."""
    db_path = validation["db_path"]

    log_stage(context, "[START] Branch analytics")

    spark = None

    try:
        spark = create_spark_session("DagsterBranchAnalytics")

        transactions = load_transactions(spark, db_path)
        accounts = load_accounts(spark, db_path)
        customers = load_customers(spark, db_path)
        branches = load_branches(spark, db_path)

        joined = join_transaction_details(
            transactions,
            accounts,
            customers,
            branches,
        )

        dataframe = branch_transaction_amount_range(joined)

        count = inspect_dataframe(
            context,
            "branch_transaction_amount_ranges.csv",
            dataframe,
        )

        log_stage(
            context,
            "[END] Branch analytics | status=SUCCESS",
        )

        return {
            "branch_transaction_amount_ranges.csv": {
                "rows": dataframe_to_rows(dataframe),
                "row_count": count,
                "fieldnames": dataframe.columns,
            }
        }

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] Branch analytics: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] Branch analytics | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()


# ---------------------------------------------------------
# Op 7: Analyze account types
# ---------------------------------------------------------

@dg.op
def analyze_account_types(context, validation):
    """Calculate average transaction amount by account type."""
    db_path = validation["db_path"]

    log_stage(context, "[START] Account-type analytics")

    spark = None

    try:
        spark = create_spark_session("DagsterAccountTypeAnalytics")

        transactions = load_transactions(spark, db_path)
        accounts = load_accounts(spark, db_path)
        customers = load_customers(spark, db_path)
        branches = load_branches(spark, db_path)

        joined = join_transaction_details(
            transactions,
            accounts,
            customers,
            branches,
        )

        dataframe = average_transaction_by_account_type(joined)

        count = inspect_dataframe(
            context,
            "average_by_account_type.csv",
            dataframe,
        )

        log_stage(
            context,
            "[END] Account-type analytics | status=SUCCESS",
        )

        return {
            "average_by_account_type.csv": {
                "rows": dataframe_to_rows(dataframe),
                "row_count": count,
                "fieldnames": dataframe.columns,
            }
        }

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] Account-type analytics: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] Account-type analytics | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()


# ---------------------------------------------------------
# Op 8: Publish all 15 CSV reports
# ---------------------------------------------------------

@dg.op(
    retry_policy=dg.RetryPolicy(
        max_retries=2,
        delay=5,
    )
)

def publish_reports(
    context,
    extraction,
    transformations,
    transaction_analytics,
    customer_analytics,
    branch_analytics,
    account_type_analytics,
):
    """Write the load, transformation and analytics CSV reports."""
    db_path = extraction["db_path"]

    log_stage(context, "[START] Publish reports")

    spark = None

    try:
        # Re-load source tables for their published CSV reports.
        spark = create_spark_session("DagsterLoadReportPublishing")

        source_tables = {
            "customers.csv": load_customers(spark, db_path),
            "branches.csv": load_branches(spark, db_path),
            "accounts.csv": load_accounts(spark, db_path),
            "transactions.csv": load_transactions(spark, db_path),
        }

        report_count = 0

        # Publish the four loaded tables.
        for filename, dataframe in source_tables.items():
            count = inspect_dataframe(context, filename, dataframe)
            rows = dataframe_to_rows(dataframe)

            write_csv_report(
                context,
                LOAD_REPORT_DIR,
                filename,
                rows,
                dataframe.columns,
            )
            report_count += 1

        spark.stop()
        spark = None

        # Combine transformation and analytics outputs.
        report_groups = [
            (TRANSFORM_REPORT_DIR, transformations),
            (ANALYTICS_REPORT_DIR, transaction_analytics),
            (ANALYTICS_REPORT_DIR, customer_analytics),
            (ANALYTICS_REPORT_DIR, branch_analytics),
            (ANALYTICS_REPORT_DIR, account_type_analytics),
        ]

        for directory, reports in report_groups:
            for filename, report in reports.items():
                write_csv_report(
                    context,
                    directory,
                    filename,
                    report["rows"],
                    report["fieldnames"],
                )
                report_count += 1

        if report_count != 15:
            raise ValueError(
                f"Expected 15 reports, but prepared {report_count}"
            )

        log_stage(
            context,
            f"[END] Publish reports | status=SUCCESS | "
            f"reports={report_count}",
        )

        return {
            "reports_published": report_count,
            "report_directory": str(REPORT_DIR),
            "log_file": str(LOG_FILE),
        }

    except Exception as exc:
        log_stage(
            context,
            f"[ERROR] Publishing reports: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )
        log_stage(
            context,
            "[END] Publish reports | status=FAILURE",
            "error",
        )
        raise

    finally:
        if spark is not None:
            spark.stop()
