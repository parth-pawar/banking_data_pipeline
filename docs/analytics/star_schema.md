# Analytical Star Schema

The analytical layer uses `fact_transaction` at the grain of one banking transaction. The fact table directly connects to the customer, account, branch, and date dimensions.

```mermaid
erDiagram
    DIM_CUSTOMER ||--o{ FACT_TRANSACTION : has
    DIM_ACCOUNT ||--o{ FACT_TRANSACTION : records
    DIM_BRANCH ||--o{ FACT_TRANSACTION : contains
    DIM_DATE ||--o{ FACT_TRANSACTION : dates

    DIM_CUSTOMER {
        TEXT customer_id PK
        TEXT customer_name
        TEXT email
        TEXT customer_segment
    }

    DIM_BRANCH {
        TEXT branch_id PK
        TEXT branch_name
        TEXT city
        TEXT state
    }

    DIM_ACCOUNT {
        TEXT account_id PK
        TEXT customer_id
        TEXT branch_id
        TEXT account_type
        TEXT account_status
    }

    DIM_DATE {
        TEXT date PK
        INTEGER year
        INTEGER month
        INTEGER day
    }

    FACT_TRANSACTION {
        TEXT transaction_id PK
        TEXT customer_id FK
        TEXT account_id FK
        TEXT branch_id FK
        TEXT transaction_date FK
        TEXT transaction_type
        REAL amount
        TEXT currency
    }
```

### Fact grain

One row in `fact_transaction` represents **one banking transaction identified by `transaction_id`**.

The fact table stores transaction-level measures and the foreign keys needed to connect each transaction directly to the customer, account, branch, and date dimensions. The dimension tables provide descriptive information used for analysis.
