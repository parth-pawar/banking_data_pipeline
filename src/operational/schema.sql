CREATE TABLE customer (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    email TEXT NOT NULL,
    customer_segment TEXT NOT NULL
);

CREATE TABLE branch (
    branch_id TEXT PRIMARY KEY,
    branch_name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL
);


CREATE TABLE account (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    branch_id TEXT NOT NULL,
    account_type TEXT NOT NULL
        CHECK (account_type IN ('CHECKING', 'SAVINGS')),
    account_status TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (branch_id) REFERENCES branch(branch_id)
);


CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN ('CREDIT', 'DEBIT')),
    amount REAL NOT NULL
        CHECK (amount > 0),
    currency TEXT NOT NULL
        CHECK (currency = 'USD'),
    source_file TEXT,
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);