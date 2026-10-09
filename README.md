# Incremental Banking Pipeline + Analytical Layer

## 1. Project Overview

This project implements a Python and SQLite banking data pipeline that processes transaction data, validates incoming records, maintains an operational relational database, and builds a separate analytical database for reporting.

The project extends the earlier banking pipeline with **incremental daily transaction processing**, **correction handling using UPSERT**, **rerun-safe processing**, and an **analytical star-schema layer**.

### Overall Architecture

```mermaid
flowchart TD

    A["data/raw/<br/>Branch Transaction CSVs"] --> B["src/ingestion<br/>Read + Validate"]

    B --> C["data/validated/<br/>Valid Transactions"]
    B --> D["data/validated/<br/>Invalid Transactions"]
    B --> E["output/<br/>DQ + Summaries + Logs"]

    R["data/reference/<br/>Customers + Branches + Accounts"] --> F["src/operational<br/>Initial Database Load"]

    C --> F
    F --> G[("database/banking.db<br/>Operational Database")]

    H["data/daily/<br/>Daily Transaction CSVs"] --> I["src/operational/<br/>incremental_load.py"]

    I -->|"New transactions + UPSERT corrections"| G

    G --> J["src/analytics<br/>Analytical Transformation"]

    J --> K[("database/analytics.db<br/>Analytical Database")]

    K --> L["dim_customer"]
    K --> M["dim_account"]
    K --> N["dim_branch"]
    K --> O["dim_date"]
    K --> P["fact_transaction"]

    K --> Q["sql/analytical_queries.sql"]

    T["tests/"] --> U["pytest"]
    U -.-> G
    U -.-> K
```

### Data Flow

The main data flow is:

```text
Raw branch CSV files
        ↓
Ingestion and validation
        ↓
Validated transactions
        ↓
banking.db
        ↓
Incremental daily processing
        ↓
banking.db updated with new/corrected transactions
        ↓
Analytical transformation
        ↓
analytics.db
        ↓
Analytical SQL queries
```

The analytical database is built from trusted relational data in `banking.db`, not directly from the raw branch CSV files.

---

## 2. Repository Structure

```text
banking_data_pipeline/
│
|- README.md
|- requirements.txt
|
├── config/
│   ├── __init__.py
│   └── config.py
│
├── data/
│   ├── raw/
│   ├── reference/
│   ├── validated/
│   └── daily/
|   └── generated/
│
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── validation.py
│   │   └── dq_metrics.py
│   │
│   ├── operational/
│   │   ├── database.py
│   │   ├── incremental_load.py
│   │   ├── integrity_tests.py
│   │   ├── run_query.py
│   │   └── schema.sql
│   │
│   └── analytics/
│   |    ├── __init__.py
│   |    ├── analytics.py
│   |    ├── analytics_schema.sql
│   |    └── run_query.py
│   |
|   |── spark/
|         |── anaytics.py
|         |── data_quality.py
|         |── generate_transactions.py
|         |── generated_transactions_analysis.py
|         |── load_data.py
|         |── parquet.py
|         |── spark_sql_analysis.py
|         |── transformations.py
|
├── output/
│   ├── logs/
│   ├── dq/
│   └── summaries/
│
├── database/
│   ├── banking.db
│   └── analytics.db
│
├── sql/
│   ├── operational_queries.sql
│   └── analytical_queries.sql
│
├── tests/
│   ├── fixtures/
│   ├── test_pipeline.py
│   ├── test_validation.py
│   ├── test_database.py
│   ├── test_incremental_load.py
│   └── test_analytics.py
|   |── conftest.py
|   |── test_banking_spark.py
|
│
├── evidence/
│   ├── earlier_pipeline/
│   ├── class_4/
│   └── week_5/
|   |── week_6/
│
└── docs/
    ├── erd/
    │   └── ER Diagram.png
    └── analytics/
        └── star_schema.md

```

---

# 3. Ingestion and Validation

## Raw Data

The original branch transaction files are stored in:

```text
data/raw/
```

The reference data used to build the operational database is stored in:

```text
data/reference/
```

This includes:

* `customers.csv`
* `branches.csv`
* `accounts.csv`

The ingestion pipeline discovers CSV files from the raw-data directory and reads them using pandas.

## Validation

The ingestion layer checks required transaction fields and validates:

* `transaction_id`
* `account_id`
* `transaction_date`
* `transaction_type`
* `amount`
* `currency`
* duplicate transaction IDs

The accepted transaction types are:

```text
CREDIT
DEBIT
```

The required currency is:

```text
USD
```

Amounts must be numeric and greater than zero.

Dates must use a valid `YYYY-MM-DD` format and represent an actual calendar date.

Invalid records are not loaded into the operational database.

## Validated and Invalid Data

After ingestion:

```text
data/validated/valid_transactions.csv
data/validated/invalid_transactions.csv
```

contain the valid and rejected records respectively.

---

# 4. Logs, Data Quality and Run Summaries

The pipeline generates runtime logs in:

```text
output/logs/
```

Data-quality metrics are written to:

```text
output/dq/
```

Run summaries are written to:

```text
output/summaries/
```

The DQ output includes information such as:

* total rows read
* valid rows
* invalid rows
* rejection rate
* missing fields
* invalid transaction types
* invalid amounts
* invalid dates
* invalid currency
* duplicate transaction IDs
* files discovered
* files successfully read
* files skipped

---

# 5. Running Ingestion and Validation

From the project root:

```powershell
python -m src.ingestion.pipeline
```

The pipeline reads the CSV files from:

```text
data/raw/
```

and produces validated data and data-quality outputs.

The original pipeline currently produces:

```text
Total records: 24
Valid records: 10
Invalid records: 14
```

---

# 6. Operational Database

The operational database is:

```text
database/banking.db
```

It contains:

```text
customer
branch
account
transactions
```

The relationships are:

```text
customer
   ↓
account
   ↓
transactions

branch
   ↓
account
```

The transaction table uses `transaction_id` as its primary key.

Foreign-key constraints are enabled using:

```python
PRAGMA foreign_keys = ON
```

---

## 7. Creating and Loading `banking.db`

The operational database can be created using:

```powershell
python -m src.operational.database
```

This creates the database if it does not already exist, using the operational schema and loading:

1. customers
2. branches
3. accounts
4. validated transactions

The initial database contains:

```text
customer: 6
branch: 3
account: 10
transactions: 10
```

The initial database build is a full-load operation and is intentionally separate from the Week 5 incremental processing.

If `banking.db` already exists, the command does not delete or rebuild it. It skips the full load to protect existing operational data.

For Week 5 daily processing, use:

```powershell
python -m src.operational.incremental_load
```

The incremental loader keeps the existing database and applies new transactions and corrections using `INSERT`/`UPDATE` (UPSERT) behavior.


---

# 8. Week 5 Incremental Processing

The Week 5 daily transaction files are stored in:

```text
data/daily/
```

The supplied daily files are:

```text
transactions_20260907.csv
transactions_20260908.csv
transactions_20260909.csv
```

These files contain new transactions as well as later corrections to previously stored transactions.

A daily file can be processed using:

```powershell
python -m src.operational.incremental_load
```

The incremental loader reads one daily CSV file and applies its transactions to `banking.db`.

---

# 9. New Transactions

When a transaction ID does not already exist in `transactions`, the transaction is inserted.

For example, the daily files introduced transaction IDs such as:

```text
T4001
T4002
T4003
T4004
T4005
T4006
T4007
T4008
T4009
T4010
```

After processing the supplied daily files, the operational database contains:

```text
20 transactions
```

---

# 10. Corrections and UPSERT

The incremental loader uses SQLite UPSERT behavior:

```sql
ON CONFLICT(transaction_id) DO UPDATE SET
```

This means that when a transaction ID already exists, the later supplied record updates the stored transaction instead of creating a duplicate.

Examples:

```text
T1001
500.0 → 550.0
```

and:

```text
T4002
50.0 → 55.0
```

This is why `INSERT OR IGNORE` is not sufficient for this pipeline. `INSERT OR IGNORE` would keep the existing row unchanged when the later file contains a correction.

The transaction ID acts as the business key used to identify the existing transaction.

---

# 11. Rerun Safety

The incremental process is designed to be safe to rerun.

If the same daily file is processed again:

* existing transaction IDs are matched
* the existing rows are updated with the same supplied values
* new duplicate rows are not created

For example, after processing the Sept 9 file:

```text
Transaction count: 20
```

After processing the same file again:

```text
Transaction count: 20
```

The correction to `T4002` also remains:

```text
T4002 → 55.0
```

Therefore, rerunning the same batch does not increase the business transaction count or reverse a previously applied correction.

---

# 12. Analytical Layer

The analytical database is:

```text
database/analytics.db
```

It is kept separate from the operational database.

The analytical layer is built from trusted data in:

```text
database/banking.db
```

using:

```text
src/analytics/analytics.py
```

The analytical schema contains:

```text
dim_customer
dim_account
dim_branch
dim_date
fact_transaction
```

The final analytical table counts are:

```text
dim_customer: 6
dim_branch: 3
dim_account: 10
dim_date: 4
fact_transaction: 20
```

---

# 13. Fact Grain

The grain of `fact_transaction` is:

> **One row represents one banking transaction identified by `transaction_id`.**

This grain is defined before building the fact table because it determines what each row represents and prevents accidental duplication or mixing of different levels of detail.

At the declared grain:

```text
20 unique transactions
=
20 fact_transaction rows
```

---
# 14. Fact and Dimension Model

The analytical model contains one central fact table:

```text
fact_transaction
```

and descriptive dimension tables:

```text
dim_customer
dim_account
dim_branch
dim_date
```

The fact table stores transaction-level information and the keys needed to connect each transaction directly to the relevant dimensions:

```text
transaction_id
customer_id
account_id
branch_id
transaction_date
transaction_type
amount
currency
```

The dimensions provide descriptive context for analysis.

```text
                 dim_customer
                      |
                      v
dim_branch ----> fact_transaction <---- dim_account
                      ^
                      |
                   dim_date
```

For example:

* `dim_customer` describes the customer.
* `dim_account` describes the account.
* `dim_branch` describes the branch.
* `dim_date` describes the transaction date.
* `fact_transaction` records each banking transaction and directly references the relevant customer, account, branch, and date.

The fact table has a grain of **one row per banking transaction**, identified by `transaction_id`.

The analytical star-schema documentation is stored in:

```text
docs/analytics/star_schema.md
```

---


# 15. Analytical SQL Queries

The analytical queries are stored in:

```text
sql/analytical_queries.sql
```

There are seven analytical queries covering:

1. Transaction count and total amount by branch
2. Transaction count and total amount by transaction type
3. Transaction activity by customer
4. Transaction activity by date
5. Transaction activity by customer and branch
6. Average transaction amount by account type
7. Largest individual transactions

The queries are executed individually using:

```text
src/analytics/run_query.py
```

This approach makes it easier to run, verify and capture the result of each query separately.

---

# 16. Operational SQL

Operational SQL queries are stored in:

```text
sql/operational_queries.sql
```

The operational query runner is:

```text
src/operational/run_query.py
```

It connects to:

```text
database/banking.db
```

and executes the selected SQL query.

For example:

```powershell
python -m src.operational.run_query
```

---

# 17. Running Analytical SQL

The analytical query runner is:

```text
src/analytics/run_query.py
```

Run it with:

```powershell
python -m src.analytics.run_query
```

The SQL inside the runner can be changed to the required analytical query.

The runner connects to:

```text
database/analytics.db
```

and prints the returned rows.

---

# 18. Testing

Tests are implemented using `pytest`.

Run the complete test suite with:

```powershell
python -m pytest -v
```

Week 5 specifically adds tests for:

### Incremental processing

* new transaction insertion
* correction of an existing transaction
* rerunning the same daily batch

### Analytical layer

* fact rows reference valid dimensions
* fact transaction IDs are unique
* a known analytical query returns the expected result

The six Week 5 tests all passed.

---

# 19. Test Fixtures and Evidence

Test fixtures are stored in:

```text
tests/fixtures/
```

These include scenarios used by the earlier ingestion and validation tests.

Assessment evidence is separated by project stage:

```text
evidence/
├── earlier_pipeline/
├── class_4/
└── week_5/
```

### earlier_pipeline

Contains useful earlier regression and manual test evidence from the previous pipeline work.

### class_4

Contains Class 4 operational database evidence such as:

* database loading results
* integrity test results
* returned SQL results
* before/after `EXPLAIN QUERY PLAN` results

### week_5

Contains evidence for:

* incremental processing
* new transaction insertion
* corrections
* rerun safety
* final operational database counts
* final analytical database counts
* analytical query results
* Week 5 pytest results

---

# 20. Dependencies

The project uses Python and SQLite.

The main Python dependencies are:

```text
pandas
pytest
```

SQLite is provided through Python's standard-library `sqlite3` module.

The project does not require:

* Airflow
* dbt
* Docker
* Kafka
* cloud services
* a separate database server

---

# 21. Assumptions and Limitations

### Assumptions

* The supplied daily transaction files are treated as trusted, already-valid inputs for the Week 5 incremental stage.
* `transaction_id` uniquely identifies a banking transaction.
* Later records with an existing `transaction_id` represent corrections to that transaction.
* The transaction amount is stored as a positive value for both CREDIT and DEBIT transactions.
* `USD` is the required currency for the supplied transaction data.
* The analytical layer is derived from trusted data in `banking.db`.

### Limitations

* The pipeline uses local CSV files and SQLite rather than a production database or distributed processing system.
* The incremental loader processes supplied daily files explicitly rather than implementing automated file discovery or CDC.
* No Slowly Changing Dimension Type 2 implementation is included.
* No historical dimension-version tracking is implemented.
* The analytical date dimension contains only the dates required by the available transaction data.
* The project does not calculate account balances or signed net cash flow from the transaction amounts.
* The project does not use Airflow, dbt, Kafka, Docker, cloud infrastructure or a server-based database.

---

# 22. Week 5 Concept Answers

## 1. What is the grain of `fact_transaction` and why is it defined first?

The grain of `fact_transaction` is one row per banking transaction identified by `transaction_id`. Defining the grain first establishes exactly what each fact row represents and helps prevent duplicate or incorrectly aggregated data.

## 2. What is the difference between a full load and an incremental load?

A full load rebuilds or reloads the target database from the complete available source data. An incremental load processes only new or changed data and applies those changes to the existing database.

## 3. Why is `INSERT OR IGNORE` insufficient for corrections?

`INSERT OR IGNORE` ignores a new record when its primary key already exists. Therefore, if a later file contains a corrected value for an existing `transaction_id`, the old value would remain unchanged.

## 4. What makes the implementation rerun-safe?

The transaction ID is used as the unique business key and the incremental loader uses UPSERT behavior. Processing the same daily file again therefore updates the existing transaction rather than creating another transaction row.

## 5. What is the difference between a fact and a dimension?

A fact table stores measurable business events at a defined grain, such as banking transactions and their amounts. Dimension tables store descriptive information that provides context for analyzing those facts, such as customers, accounts, branches and dates.


# 23. Week 6 — PySpark Banking Analytics

Week 6 extends the existing banking project with **Apache Spark using PySpark**.

The existing Python/SQLite banking work is preserved. Spark is used as an additional analytical processing layer rather than replacing the operational database.

The Week 6 work demonstrates:

* Loading SQLite banking data into Spark DataFrames
* Data transformations and filtering
* Aggregations
* Joins across banking tables
* Data-quality checks
* Processing a larger synthetic dataset
* Spark partitions and basic Spark execution concepts
* Spark SQL
* Automated Spark validation using pytest
* An attempted Parquet workflow

---

## 23.1 Spark Environment

The Week 6 Spark work was developed and tested using:

```text
Windows 11
Python 3.13.15
PySpark 4.2.0
Java JDK 17
```

Spark runs locally using:

```python
.master("local[*]")
```

The project does not require a Spark cluster.

---

## 23.2 Week 6 Inputs

The main banking input is the existing operational database:

```text
database/banking.db
```

The database contains:

```text
customer
branch
account
transactions
```

The relationships are:

```text
customer
   ↓
account
   ↓
transactions

branch
   ↓
account
```

The `account` table connects transactions to their customers and branches.

The Week 6 Spark work therefore continues to use the existing banking data rather than creating a separate banking source.

The larger-data analysis also uses a generated file:

```text
data/generated/synthetic_transactions.csv
```

This file contains approximately 100,000 synthetic transactions.

---

## 23.3 Loading Banking Data into Spark

The main Spark loading code is:

```text
src/spark/load_data.py
```

Run it from the project root using:

```powershell
python -m src.spark.load_data
```

The script loads the following SQLite tables into Spark DataFrames:

```text
customer
branch
account
transactions
```

For each DataFrame, the script displays:

* sample rows
* schema
* row count

The transaction date is converted into a Spark date column during loading.

---

## 23.4 Spark Transformations and Aggregations

The Week 6 analysis uses Spark DataFrame operations such as:

```text
filter()
groupBy()
agg()
join()
```

Examples include:

* filtering CREDIT transactions
* identifying high-value transactions
* calculating transaction totals
* calculating average transaction amounts
* grouping transactions by transaction type
* grouping transactions by account type

For this project, transactions with an amount of **USD 500 or more** are classified as high-value transactions.

The banking business rules remain the same as the earlier Python/SQLite implementation. Spark changes how the processing is performed, not the meaning of the banking calculations.

The transformations code is in:

```text
src/spark/transformations.py
```

Run it from the project root using:

```powershell
python -m src.spark.transformations
```
---

## 23.5 Banking Joins

The Aggregations and Joins code is in:

```text
src/spark/analytics.py
```

Run it from the project root using:

```powershell
python -m src.spark.analytics
```
The transaction table does not directly contain customer or branch information.

The Spark analysis therefore follows the existing relational structure:

```text
transactions
     ↓ account_id
account
     ↓ customer_id
customer

account
     ↓ branch_id
branch
```

The analysis joins:

```text
transactions → account
account → customer
account → branch
```

This allows transaction-level analysis to include customer and branch information.

---

## 23.6 Data-Quality Checks

The data quality code is in:

```text
src/spark/data_quality.py
```

Run it from the project root using:

```powershell
python -m src.spark.data_quality
```
The Spark work includes checks for:

* null transaction IDs
* null account IDs
* null transaction amounts
* duplicate transaction IDs
* transactions referring to nonexistent accounts
* accounts referring to nonexistent customers
* accounts referring to nonexistent branches

The checks use Spark DataFrame operations and return the number of invalid records.

The completed checks passed with no invalid records in the banking dataset.

---

## 23.7 Generating Larger Data

The script:

```text
src/spark/generate_transactions.py
```

generates synthetic transaction data for larger-scale Spark processing.

Run:

```powershell
python -m src.spark.generate_transactions
```

The generated data is written to:

```text
data/generated/synthetic_transactions.csv
```

The generation uses a fixed random seed so that the dataset can be reproduced.

The generated dataset contains:

```text
100,000 transactions
```

---

## 23.8 Larger Dataset Analysis

The larger dataset can be analyzed using:

```text
src/spark/generated_transactions_analysis.py
```

Run:

```powershell
python -m src.spark.generated_transactions_analysis
```

The analysis includes:

* total transaction count
* high-value transaction count
* CREDIT/DEBIT aggregation
* total and average transaction amounts
* join with the account table
* aggregation by account type
* Spark partition inspection

The generated dataset was successfully processed with:

```text
100,000 transactions
2 Spark partitions
```

All generated account IDs matched accounts in the banking database.

---

## 23.9 Spark SQL

Spark SQL provides another way to perform analytical processing using the Spark engine.

The script:

```text
src/spark/spark_sql_analysis.py
```

registers the transactions DataFrame as a temporary SQL view and performs transaction-type aggregation using SQL.

Run:

```powershell
python -m src.spark.spark_sql_analysis
```

The same transaction-type analysis was also implemented using the PySpark DataFrame API.

Both approaches produced the same results.

The difference is how the processing is expressed:

```text
PySpark DataFrame API
        ↓
Python methods such as filter(), groupBy(), agg()

Spark SQL
        ↓
SQL statements such as SELECT, GROUP BY, SUM()
```

Both are executed by the Spark engine.

---

## 23.10 Spark Concepts Demonstrated

### Transformation

A transformation describes a new DataFrame based on an existing DataFrame.

Example:

```python
transactions_df.filter(
    col("transaction_type") == "CREDIT"
)
```

`filter()` is a transformation.

### Action

An action causes Spark to execute the required processing and return a result.

Example:

```python
transactions_df.count()
```

`count()` is an action.

### Lazy Evaluation

Spark does not immediately execute transformations.

Instead, Spark builds an execution plan and waits until an action requires the result.

For example:

```python
credit_df = transactions_df.filter(...)
```

does not immediately calculate the filtered result.

Calling:

```python
credit_df.count()
```

causes Spark to execute the required processing.

### Partition

A partition is a portion of a Spark DataFrame's data that Spark can process independently.

The larger synthetic transaction dataset was observed with:

```text
2 partitions
```

### Shuffle

A shuffle occurs when Spark needs to redistribute data between partitions.

Operations such as:

```python
groupBy("transaction_type")
```

can cause a shuffle because records with the same grouping key may need to be brought together.

---

## 23.11 Parquet

The Parquet workflow is implemented in:

```text
src/spark/parquet.py
```

The intended workflow is:

```text
Spark analytical DataFrame
        ↓
write to Parquet
        ↓
read Parquet back into Spark
        ↓
compare/read-back row count
```

The Parquet write was attempted in the Windows development environment.

However, the operation failed because the required local Hadoop filesystem support was unavailable:

```text
HADOOP_HOME and hadoop.home.dir are unset
```

As a result:

* the Parquet file could not be written
* the Parquet data could not be read back
* read-back row-count validation could not be performed

This is an environment limitation rather than a missing project implementation.

No Hadoop or `winutils.exe` installation was added to the project.

---

## 23.12 Automated Spark Testing

The Week 6 Spark tests are:

```text
tests/test_banking_spark.py
```

Shared pytest fixtures are defined in:

```text
tests/conftest.py
```

Run the Spark tests with:

```powershell
python -m pytest tests/test_banking_spark.py -v
```

The tests use a temporary SQLite database instead of modifying:

```text
database/banking.db
```

The temporary database is created from the existing project schema.

The tests validate:

1. expected transaction row count
2. CREDIT transaction count
3. CREDIT transaction total
4. duplicate transaction ID detection
5. null-value checks
6. join integrity

The final test run produced:

```text
6 passed
```


---

# 24. Week 6 Understanding Questions

## 1. What is the difference between Apache Spark and PySpark?

Apache Spark is the data-processing engine. PySpark is the Python API that allows Python programs to use Spark.

In this project, Spark performs the processing while PySpark provides the Python interface used to create DataFrames and perform operations.

## 2. What is a Spark DataFrame?

A Spark DataFrame is a distributed collection of data organized into named columns.

It is similar to a table and can be processed using Spark operations such as filtering, grouping, aggregation, and joins.

For example, the transactions DataFrame contains columns such as `transaction_id`, `account_id`, `transaction_type`, and `amount`.

## 3. What is the difference between a transformation and an action?

A transformation creates a new DataFrame or describes a processing step without immediately executing it.

For example:

```python
transactions_df.filter(
    col("transaction_type") == "CREDIT"
)
```

`filter()` is a transformation.

An action causes Spark to execute the processing and return a result.

For example:

```python
transactions_df.count()
```

`count()` is an action.

## 4. What does lazy evaluation mean in Spark?

Lazy evaluation means Spark waits before executing transformations.

Spark first builds a plan describing the required operations. Execution begins when an action such as `count()` or `show()` requires a result.

This allows Spark to optimize the execution plan before processing the data.

## 5. What is a partition?

A partition is a portion of a Spark DataFrame's data.

Spark can process different partitions independently, which allows work to be distributed across available processing resources.

The synthetic transaction analysis showed 2 partitions.

## 6. What is a shuffle? Which operation in your project could cause one?

A shuffle occurs when Spark redistributes data between partitions.

A `groupBy()` operation in this project could cause a shuffle because Spark may need to bring records with the same grouping key together before calculating the aggregation.

## 7. Why might Parquet be preferable to CSV for analytical processing?

Parquet is a columnar storage format designed for analytical workloads.

It stores data types and organizes data by column, which can allow Spark to read only the columns needed for an analysis. Parquet also supports compression.

CSV is a plain-text row-based format and generally requires more parsing during analytical processing.

## 8. How can Spark SQL and the PySpark DataFrame API solve the same data problem?

Both are interfaces for processing data using the Spark engine.

In this project, transaction totals were calculated by transaction type using the PySpark DataFrame API and then the same analysis was implemented using Spark SQL.

The two approaches produced the same result.

The main difference is the way the logic is written: one uses Python DataFrame operations while the other uses SQL.

## 9. Which parts of your banking business logic stayed the same when moving from Python/SQLite/SQL to PySpark?

The banking business logic stayed the same.

For example:

* transactions belong to accounts
* accounts belong to customers and branches
* transaction types are CREDIT and DEBIT
* transaction amounts must be positive
* USD 500 or more is the high-value threshold used in this project
* transaction totals are calculated from transaction amounts
* the same account, customer, and branch relationships are used

The processing technology changed, but the meaning of the banking calculations did not.

## 10. What changed because Spark is a different processing engine?

The processing model changed.

The earlier work used Python, SQLite, and SQL to process the banking data locally. The Week 6 work loads the data into Spark DataFrames and uses Spark's processing model.

This introduces concepts such as:

* partitions
* transformations
* actions
* lazy evaluation
* shuffles
* Spark execution plans

Therefore, the business logic remained mostly the same, while the way the data is processed changed because Spark is the processing engine.
