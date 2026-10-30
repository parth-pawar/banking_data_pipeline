# CDP Test Results

## Test: C001 – Customer with Multiple Accounts and Transactions

### Objective

Verify that the Customer 360 Gold table correctly aggregates transaction data for a customer with multiple accounts and multiple transactions.

### Test Scenario

| Item | Test data |
|---|---|
| Customer ID | `C001` |
| Customer name | Synthetic Customer One |
| Account IDs | `A1001`, `A1002` |
| Number of accounts | 2 |
| Number of transactions | 4 |
| Expected transaction amount | 850.00 |

### Expected vs Actual Results

| Scenario | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|
| Customer identification | `C001` | `C001` | PASS | Customer ID returned from `customer_360` |
| Account count | 2 | 2 | PASS | Independent SQL query using `COUNT(DISTINCT account_id)` |
| Transaction count | 4 | 4 | PASS | Independent SQL query using `COUNT(transaction_id)` |
| Total transaction amount | 850.00 | 850.00 | PASS | Independent SQL query using `SUM(amount)` |

### Independent SQL Verification

The test creates a separate `test_transactions` table using the test transaction records and independently calculates the expected results by joining it with the CDP accounts table.

```sql
SELECT
    COUNT(DISTINCT t.account_id) AS account_count,
    COUNT(t.transaction_id) AS transaction_count,
    SUM(t.amount) AS total_transaction_amount
FROM test_transactions t
JOIN accounts a
    ON t.account_id = a.account_id
WHERE a.customer_id = 'C001';

```

### Test Command and Result
Test Command: 
```
pytest cdp/tests/test_customer360.py::test_c001_customer_summary -v
```
Result:
```
cdp/tests/test_customer360.py::test_c001_customer_summary PASSED
```



## Test: C002 – API Returns the Correct Customer

### Objective

Verify that the Customer Summary API uses the customer ID in the URL to retrieve the correct customer's record, rather than returning another customer's data.

### Test Scenario

| Item | Test data |
|---|---|
| Customer ID | `C002` |
| Customer name | Synthetic Customer Two |
| API endpoint | `GET /customers/C002/summary` |
| Expected HTTP status | `200 OK` |
| Expected transaction count | 7 |
| Expected total transaction amount | 2760.00 |

### Expected vs Actual Results

| Scenario | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|
| HTTP response | `200 OK` | `200 OK` | PASS | API test response status |
| Customer ID | `C002` | `C002` | PASS | Response JSON contains `customer_id: C002` |
| Customer name | Synthetic Customer Two | Synthetic Customer Two | PASS | Response JSON contains the expected customer name |
| Transaction count | 7 | 7 | PASS | Response JSON contains the expected transaction count |
| Total transaction amount | 2760.00 | 2760.00 | PASS | Response JSON contains the expected amount |
| URL parameter selection | Return C002, not C001 | C002 returned | PASS | Test requests `/customers/C002/summary` and checks the returned customer ID |

### Test Execution

Test command:

```powershell
pytest cdp/tests/test_customer360.py::test_c002_api_returns_requested_customer -v
```

Result:
```
cdp/tests/test_customer360.py::test_c002_api_returns_requested_customer PASSED
```


## Test: C003 – Customer with No Transactions

### Objective

Verify that a customer with valid customer and account records but no transactions is retained in the Customer 360 Gold table.

The customer should not be excluded simply because no transaction records exist.

### Test Scenario

| Item | Test data |
|---|---|
| Customer ID | `C003` |
| Customer name | Synthetic Customer Three |
| Account ID | `A9001` |
| Number of accounts | 1 |
| Number of transactions | 0 |
| Expected transaction count | 0 |
| Expected total transaction amount | 0.00 |
| Expected last transaction date | NULL |

### Expected vs Actual Results

| Scenario | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|
| Customer identification | `C003` exists in Customer 360 | `C003` exists | PASS | Customer row retrieved from `customer_360` |
| Account count | 1 | 1 | PASS | Gold record contains `account_count = 1` |
| Transaction count | 0 | 0 | PASS | Gold record contains `transaction_count = 0` |
| Total transaction amount | 0.00 | 0.00 | PASS | Gold record contains `total_transaction_amount = 0.0` |
| Last transaction date | NULL | NULL | PASS | Gold record contains no transaction date |
| Customer retention | Customer remains in Gold | Customer remains in Gold | PASS | Query returns the C003 record instead of an empty result |

### Test Execution

Test command:

```powershell
pytest cdp/tests/test_customer360.py::test_c003_customer_with_no_transactions -v 
```

Result:
```
cdp/tests/test_customer360.py::test_c003_customer_with_no_transactions PASSED                                                                 
```


## Test: C999 – Unknown Customer

### Objective

Verify that the Customer Summary API handles requests for customers who do not exist in the Customer 360 Gold table.

The API should return HTTP `404 Not Found` with a clear error message.

### Test Scenario

| Item | Test data |
|---|---|
| Customer ID | `C999` |
| API endpoint | `GET /customers/C999/summary` |
| Customer record | Does not exist |
| Expected HTTP status | `404 Not Found` |
| Expected response | `{"error": "Customer not found"}` |

### Expected vs Actual Results

| Scenario | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|
| Unknown customer lookup | Customer not found | Customer not found | PASS | API returns the expected error |
| HTTP response status | `404` | `404` | PASS | Test checks the HTTP error code |
| Error response body | `{"error": "Customer not found"}` | `{"error": "Customer not found"}` | PASS | Test compares the decoded JSON response |
| Database integrity | No customer record created | No customer record created | PASS | API performs a read-only lookup |

### Test Execution

Test command:

```powershell
pytest cdp/tests/test_customer360.py::test_c999_unknown_customer_returns_404 -v
```

Result:
```
cdp/tests/test_customer360.py::test_c999_unknown_customer_returns_404 PASSED
```



## Test: Duplicate Transactions and Unknown References

### Objective

Verify that the CDP rejects invalid transaction and account records and records each rejected record in the exceptions table.

### Test Scenario

The test uses the following records:

| Record | Test data | Issue |
|---|---|---|
| TX001 | Account `A1001`, amount 100.00 | Valid transaction |
| TX002 | Appears twice with the same transaction ID | Duplicate transaction ID |
| TX003 | References account `A8888` | Unknown account ID |
| A9999 | References customer `C999` | Unknown customer ID |

The valid customer is `C001`, and the valid account is `A1001`, linked to `C001`.

### Expected vs Actual Results

| Scenario | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|
| Valid transaction TX001 | Accepted | Accepted | PASS | Included in C001 Gold aggregation |
| Duplicate transaction TX002 | Both occurrences rejected | Both occurrences rejected | PASS | Two exception records for TX002 |
| Unknown account TX003 | Rejected | Rejected | PASS | Exception reason: `Unknown account_id` |
| Account A9999 with unknown customer C999 | Rejected | Rejected | PASS | Exception reason: `Unknown customer_id: C999` |
| C001 Gold transaction count | 1 | 1 | PASS | Only TX001 is included |
| C001 Gold transaction amount | 100.00 | 100.00 | PASS | Invalid transactions are excluded from aggregation |

### Expected Exception Records

| Record type | Record ID | Exception reason |
|---|---|---|
| transaction | TX002 | Duplicate transaction_id |
| transaction | TX002 | Duplicate transaction_id |
| transaction | TX003 | Unknown account_id |
| account | A9999 | Unknown customer_id: C999 |

### Expected Gold Result

| customer_id | account_count | transaction_count | total_transaction_amount |
|---|---:|---:|---:|
| C001 | 1 | 1 | 100.00 |

### Test Execution

Test command:

```powershell
pytest cdp/tests/test_customer360.py::test_invalid_transactions_are_rejected -v
```

Result:
```
cdp/tests/test_customer360.py::test_invalid_transactions_are_rejected PASSED
```



## Test: Customer 360 Build Idempotency

### Objective

Verify that running the Customer 360 build twice with identical input data produces the same Gold business results.

The second build must not create duplicate customer records, inflate transaction counts, or change aggregated transaction amounts.

### Test Scenario

| Item | Test data |
|---|---|
| Customer ID | `C001` |
| Customer name | Synthetic Customer One |
| Input | Same customer, account, and transaction records |
| Build executions | 2 |
| Comparison | Gold results after first and second builds |

### Expected vs Actual Results

| Scenario | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|
| First build | Customer 360 Gold table generated successfully | Build completed successfully | PASS | First build executed in pytest |
| Second build | Customer 360 Gold table rebuilt successfully | Build completed successfully | PASS | Second build executed using identical inputs |
| Customer records | No duplicate customer records | Customer records remained unchanged | PASS | Gold rows compared before and after |
| Account count | Same account count | Same account count | PASS | Before-and-after comparison |
| Transaction count | Same transaction count | Same transaction count | PASS | Before-and-after comparison |
| Total transaction amount | Same total amount | Same total amount | PASS | Before-and-after comparison |
| Last transaction date | Same transaction date | Same transaction date | PASS | Before-and-after comparison |

### Test Execution

Test command:

```powershell
pytest cdp/tests/test_customer360.py::test_build_customer360_is_idempotent -v
```

Result:

```
cdp/tests/test_customer360.py::test_build_customer360_is_idempotent PASSED
```