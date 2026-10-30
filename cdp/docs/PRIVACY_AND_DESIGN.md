# Customer Data Platform – Privacy and Design

## 1. Customer Identity Rule

The CDP uses `customer_id` as the unique customer identity key.

- Each customer is identified by a unique `customer_id`.
- Each account is linked to a customer through `accounts.customer_id`.
- Each transaction is linked to an account through `transactions.account_id`.
- Customer identity is determined using explicit ID relationships, not customer names.
- Customers are never merged based only on matching names.

The relationship is:

`customer_id → account_id → transaction_id`

The project uses synthetic customer and account reference data.

## 2. Table Grain

Each table has a defined level of detail (grain).

| Table | Grain |
|---|---|
| `customers` | One row per customer |
| `accounts` | One row per account |
| `silver_transactions` | One row per transaction |
| `customer_360` | One row per customer |

The `customer_360` Gold table provides customer-level aggregated information.

It contains:
- Customer ID and name
- Number of accounts
- Number of transactions
- Total transaction amount
- Latest transaction date

Customers without transactions remain in the Gold output with zero transaction counts and totals. Their latest transaction date is NULL.

## 3. Data Limitations

- The project uses synthetic customer and account reference data.
- Transaction data is sourced from the existing Silver database.
- Customer matching depends on the availability and correctness of customer and account identifiers.
- The project does not perform fuzzy matching, name-based identity resolution, or automatic customer merging.
- The Customer 360 output contains aggregated transaction information rather than individual transaction histories.
- The project is designed for demonstration and learning purposes, not production banking operations.

## 4. Sensitive Fields Excluded

The CDP uses only the fields required for customer-level aggregation and API responses.

The following sensitive information is excluded:

- Bank account numbers and production account identifiers
- Card numbers and CVV values
- Passwords, authentication tokens, and credentials
- Government-issued identification numbers
- Customer addresses and other unnecessary personal details
- Full transaction histories in API responses

The project uses synthetic customer IDs, account IDs, and customer names for demonstration.

## 5. Production Controls Not Implemented

The current implementation is a local demonstration and does not implement a complete production security framework.

The following controls are outside the current project scope:

- User authentication and authorization
- Role-based access control
- Encryption at rest and in transit
- Centralized secrets management
- Production audit logging and monitoring
- Data retention and deletion policies
- Consent and customer data access management
- Production deployment and network security controls
- Formal privacy impact assessments and security reviews

The API is bound to `127.0.0.1` and uses a read-only SQLite connection.

These measures are suitable for the current local demonstration but should not be considered sufficient for production deployment.

## 6. Design Principles

The CDP follows these principles:

1. **Explicit identity:** Customer relationships are established through unique identifiers.
2. **Data minimization:** Only required fields are used for customer-level aggregation.
3. **Separation of concerns:** Reference data, Silver transactions, Gold output, and API access have separate responsibilities.
4. **Exception tracking:** Invalid records are rejected and recorded with reasons.
5. **Reproducibility:** Rebuilding the Gold table with the same inputs produces the same business results.
6. **Read-only API:** The API retrieves customer summaries without providing write operations.

## Conclusion

The Customer Data Platform demonstrates customer-level data integration while keeping identity relationships explicit, limiting unnecessary data exposure, and tracking invalid records. It is an educational implementation and requires additional security, privacy, and operational controls before production use.