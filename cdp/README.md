# Customer Data Platform (CDP)

## 1. Project Setup

### Prerequisites

- Python 3.12 or a compatible Python version
- pip
- Git (optional)

### Clone the repository

```bash
git clone https://github.com/parth-pawar/banking_data_pipeline.git
cd banking_data_pipeline
```

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

The virtual environment keeps project dependencies separate from the system Python installation.


## 2. Running the Customer Data Platform

The CDP uses:

- Customer reference data from `cdp/input/customers.csv`
- Account reference data from `cdp/input/accounts.csv`
- Trusted transaction data from `capstone/database/silver.db`

Run the CDP build from the project root:

```bash
python cdp/build_customer360.py
```

The build performs the following operations:

1. Initializes the CDP SQLite database.
2. Loads and validates customer reference records.
3. Loads and validates account reference records.
4. Reads transaction records from the Silver database.
5. Validates transaction identifiers and account references.
6. Records rejected records in the CDP exceptions table.
7. Builds the customer-level Gold summary.
8. Exports the customer summary to CSV.

### CDP Outputs

| Output | Location |
|---|---|
| CDP database | `cdp/database/cdp.db` |
| Customer 360 CSV | `cdp/output/customer_360.csv` |

## 3. Running the Customer Summary API

Run the API server from the project root:

```bash
python cdp/api_server.py
```

The server listens on:

`http://127.0.0.1:8000`

### API Endpoint

```http
GET /customers/{customer_id}/summary
```

Example:

```http
GET http://127.0.0.1:8000/customers/C001/summary
```

A successful request returns the requested customer's summary.

An unknown customer returns:

```json
{
  "error": "Customer not found"
}
```

The API uses a read-only database connection and only exposes customer summary information.

Stop the server using `Ctrl + C`.

## 4. Data Model


### Customer Data Platform

The CDP uses three main entities:

| Entity | Grain | Description |
|---|---|---|
| Customer | One row per customer | Customer reference information |
| Account | One row per account | Account-to-customer relationship |
| Transaction | One row per transaction | Transaction associated with an account |
| Customer 360 | One row per customer | Aggregated customer-level information |

### Customer 360 Gold Fields

| Column | Description |
|---|---|
| `customer_id` | Unique customer identifier |
| `customer_name` | Customer name |
| `account_count` | Number of accounts belonging to the customer |
| `transaction_count` | Number of associated transactions |
| `total_transaction_amount` | Sum of associated transaction amounts |
| `last_transaction_date` | Latest transaction date for the customer |

The Customer 360 table uses `customer_id` as its customer identity key.

Customers without transactions are retained in the Gold output with zero transaction counts and zero transaction amounts.

## 5. Data Freshness

The Customer 360 dataset is a batch-generated snapshot.

Its freshness depends on:

1. When new branch transaction files are ingested.
2. When the Silver layer is successfully updated.
3. When the CDP build is executed.

The CDP does not continuously refresh when new transactions arrive.

A new CDP build is required to incorporate changes in the Silver database or reference CSV files.

The project does not currently maintain a dedicated freshness monitoring system or an automated last-successful-refresh indicator.

## 6. Data Provenance and Lineage

The Customer 360 dataset is derived from two categories of sources:

| Source | Data supplied |
|---|---|
| `customers.csv` | Customer identifiers and names |
| `accounts.csv` | Account identifiers and customer relationships |
| `silver_transactions` | Validated transaction records |

### Transformation Lineage

1. Customer reference records are loaded and validated.
2. Account records are checked against customer identifiers.
3. Silver transactions are read from the banking pipeline.
4. Transactions are checked for duplicate transaction identifiers and unknown account references.
5. Valid transactions are associated with customers through the account relationship.
6. Transaction data is aggregated at customer level.
7. The resulting Customer 360 dataset is stored in SQLite and exported as CSV.

Invalid records are recorded in the CDP exceptions table.


## 7. Assumptions and Limitations

### Assumptions

- Customer identifiers are unique and reliable.
- Account identifiers are unique and linked to valid customers.
- Transaction records in Silver have already passed the upstream validation process.
- Each transaction references an account.
- Customer identity is determined through `customer_id`, not customer names.
- The CDP is rebuilt using the available reference files and Silver transaction data.

### Limitations

- The project uses synthetic customer and account reference data.
- It is a local demonstration, not a production banking system.
- Customer matching uses explicit identifiers; fuzzy identity matching is not implemented.
- Customer 360 provides aggregated information rather than a complete customer transaction history.
- Data freshness depends on manual or externally triggered batch execution.
- Automated lineage and historical data-version tracking are not implemented.
- The API is intended for local testing only.
- Production authentication, authorization, audit logging, consent management, privacy enforcement, and rate limiting are not implemented.

## 8. Security and Controls Required in a Real Bank

The current project is a learning and portfolio implementation. A real banking environment would require additional security, privacy, and operational controls.

| Control | Purpose | Production Requirement |
|---|---|---|
| Authentication | Verify the identity of API users and services | Strong authentication, secure credentials, and service identity management |
| Authorization | Restrict access to permitted customer records and operations | Role-based or attribute-based access control and customer-level access checks |
| Audit logs | Record access and important data operations | Tamper-resistant logs containing user/service identity, action, timestamp, and outcome |
| Consent and privacy | Ensure customer data is used only for permitted purposes | Consent and lawful-purpose checks, data minimization, retention policies, deletion workflows, and privacy reviews |
| Rate limiting | Prevent excessive API requests and abuse | Per-user or per-client request limits, throttling, and abuse monitoring |

Additional production controls would include:

- Encryption in transit and at rest.
- Secure secrets and key management.
- Network isolation and firewall restrictions.
- Monitoring, alerting, and incident response.
- Backup and disaster recovery procedures.
- Data retention and secure deletion.
- Data-quality and data-freshness monitoring.
- Deployment controls and environment separation.
- Security testing and periodic access reviews.

These controls are recommendations for a production implementation and are not claimed to exist in this project.

## 9. Automated Tests

The CDP test suite covers:

- Customer-level aggregation.
- API retrieval of a requested customer.
- Customers with no transactions.
- Unknown customer API requests.
- Idempotent rebuilds.
- Invalid transactions and reference relationships.

Run the tests from the project root:

```bash
pytest cdp/tests/test_customer360.py -v
```

The tests use temporary databases and test fixtures to avoid modifying the normal project databases.

## 10. Project Documentation

Additional documentation is available under `cdp/docs/`:

- `ARCHITECTURE.md` – Architecture and data flow.
- `PRIVACY_AND_DESIGN.md` – Identity rules, data grain, privacy considerations, limitations, and missing production controls.
