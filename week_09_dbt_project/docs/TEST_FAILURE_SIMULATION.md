### Test Failure Investigation: Negative Transaction Amount

**Test:** `assert_nonnegative_transaction_amount`

**Objective:** Verify that the data quality test detects transactions with negative raw amounts.

**Simulation:**

1. Created a separate temporary DuckDB database (`test_failure.duckdb`).
2. Copied the 48 transaction records from the original database.
3. Inserted a test transaction with ID `T999` and amount `-50.00`.
4. Executed the following Python code to check for negative transaction amounts.

**Python Assertion Code:**

```python
import duckdb

con = duckdb.connect("test_failure.duckdb")

failures = con.execute("""
    SELECT transaction_id, amount
    FROM transactions
    WHERE amount < 0
""").fetchall()

print("Assertion results:", failures)

if failures:
    print("TEST FAILED: Negative transaction amounts detected.")
else:
    print("TEST PASSED.")

con.close()
```

**Expected Result:** The query should return the invalid transaction because its amount is negative, resulting in a test failure.

**Actual Result:**

```text
Assertion results: [('T999', -50.0)]
TEST FAILED: Negative transaction amounts detected.
```

**Conclusion:** The assertion correctly detected the invalid record. This confirmed that the data quality check works as intended. The simulation was performed using a separate temporary database, leaving the original development database and source CSV files unchanged.