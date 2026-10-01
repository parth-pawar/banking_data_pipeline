from src.ingestion.validation import (
    validate_amount,
    validate_date,
    validate_transaction_type,
    validate_currency,
)

# Unit tests for the validation functions in validation.py

def test_positive_amount_is_valid():
    assert validate_amount("100") is True


def test_negative_amount_is_invalid():
    assert validate_amount("-50") is False


def test_non_numeric_amount_is_invalid():
    assert validate_amount("ABC") is False


def test_valid_date_is_accepted():
    assert validate_date("2026-09-10") is True


def test_wrong_date_format_is_rejected():
    assert validate_date("2026-9-10") is False


def test_impossible_date_is_rejected():
    assert validate_date("2026-02-30") is False


def test_credit_transaction_type_is_valid():
    assert validate_transaction_type("CREDIT") is True


def test_invalid_transaction_type_is_rejected():
    assert validate_transaction_type("TRANSFER") is False


def test_usd_currency_is_valid():
    assert validate_currency("USD") is True


def test_non_usd_currency_is_rejected():
    assert validate_currency("EUR") is False




