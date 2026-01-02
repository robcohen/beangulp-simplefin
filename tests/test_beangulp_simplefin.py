import json
import os
import tempfile

from beangulp_simplefin import SimpleFINImporter, __version__

# =============================================================================
# Version tests
# =============================================================================


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.2.0"


# =============================================================================
# Identify tests
# =============================================================================


def test_identify_valid():
    """Test that importer identifies valid SimpleFIN JSON."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.identify(f.name) is True
        os.unlink(f.name)


def test_identify_wrong_account():
    """Test that importer rejects JSON with wrong account ID."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-999": "Assets:Checking"})
        assert importer.identify(f.name) is False
        os.unlink(f.name)


def test_identify_non_json_file():
    """Test that importer rejects non-JSON files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("not json")
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.identify(f.name) is False
        os.unlink(f.name)


def test_identify_malformed_json():
    """Test that importer rejects malformed JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid json")
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.identify(f.name) is False
        os.unlink(f.name)


def test_identify_missing_id():
    """Test that importer rejects JSON without id field."""
    data = {
        "name": "Checking",
        "transactions": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.identify(f.name) is False
        os.unlink(f.name)


def test_identify_json_array():
    """Test that importer rejects JSON array (wrong format)."""
    data = [{"id": "ACT-123"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.identify(f.name) is False
        os.unlink(f.name)


# =============================================================================
# Account tests
# =============================================================================


def test_account_returns_mapped_account():
    """Test that account() returns the mapped account."""
    data = {"id": "ACT-123", "name": "Checking"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.account(f.name) == "Assets:Checking"
        os.unlink(f.name)


def test_account_returns_unknown_for_unmapped():
    """Test that account() returns Assets:Unknown for unmapped accounts."""
    data = {"id": "ACT-999", "name": "Checking"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.account(f.name) == "Assets:Unknown"
        os.unlink(f.name)


def test_account_handles_malformed_json():
    """Test that account() handles malformed JSON gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{bad json")
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        assert importer.account(f.name) == "Assets:Unknown"
        os.unlink(f.name)


# =============================================================================
# Extract tests - basic
# =============================================================================


def test_extract_expense():
    """Test extraction of expense transaction."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "currency": "USD",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": 793065600,
                "description": "Coffee Shop",
                "amount": "-5.50",
            }
        ],
        "balance": 100.00,
        "balance-date": 793065600,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    # Should have 1 transaction + 1 balance
    assert len(entries) == 2

    txn = entries[0]
    assert txn.narration == "Coffee Shop"
    assert len(txn.postings) == 2
    assert txn.postings[0].account == "Assets:Checking"
    assert str(txn.postings[0].units.number) == "-5.50"
    assert txn.postings[1].account == "Expenses:Uncategorized"


def test_extract_income():
    """Test extraction of income transaction."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "currency": "USD",
        "transactions": [
            {
                "id": "TRN-002",
                "posted": 793065600,
                "description": "Direct Deposit",
                "amount": "1000.00",
            }
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    txn = entries[0]
    assert txn.postings[1].account == "Income:Uncategorized"


# =============================================================================
# Extract tests - edge cases
# =============================================================================


def test_extract_empty_transactions():
    """Test extraction with empty transactions list."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 0


def test_extract_unmapped_account_returns_empty():
    """Test that extract returns empty for unmapped accounts."""
    data = {
        "id": "ACT-999",
        "name": "Unknown",
        "transactions": [{"id": "TRN-001", "posted": 793065600, "amount": "100"}],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 0


def test_extract_skips_pending_transactions():
    """Test that pending transactions are skipped."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": 793065600,
                "description": "Pending Payment",
                "amount": "-50.00",
                "pending": True,
            },
            {
                "id": "TRN-002",
                "posted": 793065600,
                "description": "Cleared Payment",
                "amount": "-25.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    assert entries[0].narration == "Cleared Payment"


def test_extract_skips_transaction_without_posted():
    """Test that transactions without posted date are skipped."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "description": "No Date",
                "amount": "-50.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 0


def test_extract_skips_transaction_without_amount():
    """Test that transactions without amount are skipped."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": 793065600,
                "description": "No Amount",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 0


def test_extract_iso_date_format():
    """Test extraction with ISO date string format."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": "2024-06-15T12:00:00Z",
                "description": "ISO Date Transaction",
                "amount": "-10.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    from datetime import date

    assert entries[0].date == date(2024, 6, 15)


def test_extract_iso_date_with_timezone():
    """Test extraction with ISO date with timezone offset."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": "2024-06-15T12:00:00+05:00",
                "description": "Timezone Transaction",
                "amount": "-10.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1


def test_extract_invalid_date_format():
    """Test that invalid date formats are skipped."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": "not-a-date",
                "description": "Bad Date",
                "amount": "-10.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 0


def test_extract_uses_file_currency():
    """Test that currency from file is used over default."""
    data = {
        "id": "ACT-123",
        "name": "Euro Account",
        "currency": "EUR",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": 793065600,
                "description": "Euro Transaction",
                "amount": "-10.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    assert entries[0].postings[0].units.currency == "EUR"


def test_extract_default_currency():
    """Test that default currency is used when not in file."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": 793065600,
                "description": "Transaction",
                "amount": "-10.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(
            account_mapping={"ACT-123": "Assets:Checking"},
            currency="GBP",
        )
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    assert entries[0].postings[0].units.currency == "GBP"


def test_extract_custom_expense_income_accounts():
    """Test custom expense and income accounts."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": 793065600,
                "description": "Expense",
                "amount": "-10.00",
            },
            {
                "id": "TRN-002",
                "posted": 793065600,
                "description": "Income",
                "amount": "100.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(
            account_mapping={"ACT-123": "Assets:Checking"},
            expense_account="Expenses:Bank",
            income_account="Income:Bank",
        )
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 2
    # Entries are sorted by date, then by order
    expense = next(e for e in entries if e.narration == "Expense")
    income = next(e for e in entries if e.narration == "Income")
    assert expense.postings[1].account == "Expenses:Bank"
    assert income.postings[1].account == "Income:Bank"


def test_extract_balance_without_date():
    """Test that balance without date is skipped."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [],
        "balance": 100.00,
        # no balance-date
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 0


def test_extract_metadata_contains_simplefin_id():
    """Test that transactions have simplefin_id in metadata."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-unique-id",
                "posted": 793065600,
                "description": "Transaction",
                "amount": "-10.00",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    assert entries[0].meta["simplefin_id"] == "TRN-unique-id"
    assert entries[0].postings[0].meta["simplefin_id"] == "TRN-unique-id"


def test_extract_default_description():
    """Test that missing description defaults to 'Unknown'."""
    data = {
        "id": "ACT-123",
        "name": "Checking",
        "transactions": [
            {
                "id": "TRN-001",
                "posted": 793065600,
                "amount": "-10.00",
                # no description
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    assert entries[0].narration == "Unknown"


# =============================================================================
# Filename tests
# =============================================================================


def test_filename_returns_basename():
    """Test that filename() returns just the basename."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    assert importer.filename("/path/to/account.json") == "account.json"
    assert importer.filename("account.json") == "account.json"


# =============================================================================
# Backwards compatibility
# =============================================================================


def test_importer_alias():
    """Test that Importer alias works for backwards compatibility."""
    from beangulp_simplefin import Importer

    importer = Importer(account_mapping={"ACT-123": "Assets:Checking"})
    assert isinstance(importer, SimpleFINImporter)


# =============================================================================
# Deduplication (cmp) tests
# =============================================================================


def _make_transaction(simplefin_id, date_str, amount_str, account):
    """Helper to create a transaction for cmp tests."""
    from datetime import date as date_type
    from decimal import Decimal

    from beancount.core import amount as amt_module
    from beancount.core import data, flags

    meta = data.new_metadata("test.json", 0)
    if simplefin_id:
        meta["simplefin_id"] = simplefin_id

    units = amt_module.Amount(Decimal(amount_str), "USD")
    posting = data.Posting(account, units, None, None, None, None)

    year, month, day = map(int, date_str.split("-"))
    return data.Transaction(
        meta,
        date_type(year, month, day),
        flags.FLAG_OKAY,
        None,
        "Test Transaction",
        data.EMPTY_SET,
        data.EMPTY_SET,
        [posting],
    )


def test_cmp_same_simplefin_id():
    """Test that transactions with same simplefin_id are duplicates."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    txn1 = _make_transaction("TRN-001", "2024-01-15", "-50.00", "Assets:Checking")
    txn2 = _make_transaction("TRN-001", "2024-01-15", "-50.00", "Assets:Checking")
    assert importer.cmp(txn1, txn2) is True


def test_cmp_different_simplefin_id():
    """Test that transactions with different simplefin_id are not duplicates."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    txn1 = _make_transaction("TRN-001", "2024-01-15", "-50.00", "Assets:Checking")
    txn2 = _make_transaction("TRN-002", "2024-01-15", "-50.00", "Assets:Checking")
    assert importer.cmp(txn1, txn2) is False


def test_cmp_one_has_simplefin_id():
    """Test that transactions where only one has simplefin_id are not duplicates."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    txn1 = _make_transaction("TRN-001", "2024-01-15", "-50.00", "Assets:Checking")
    txn2 = _make_transaction(None, "2024-01-15", "-50.00", "Assets:Checking")
    assert importer.cmp(txn1, txn2) is False
    assert importer.cmp(txn2, txn1) is False


def test_cmp_no_simplefin_id_same_details():
    """Test fallback comparison when neither has simplefin_id."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    txn1 = _make_transaction(None, "2024-01-15", "-50.00", "Assets:Checking")
    txn2 = _make_transaction(None, "2024-01-15", "-50.00", "Assets:Checking")
    assert importer.cmp(txn1, txn2) is True


def test_cmp_no_simplefin_id_different_date():
    """Test fallback comparison with different dates."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    txn1 = _make_transaction(None, "2024-01-15", "-50.00", "Assets:Checking")
    txn2 = _make_transaction(None, "2024-01-16", "-50.00", "Assets:Checking")
    assert importer.cmp(txn1, txn2) is False


def test_cmp_no_simplefin_id_different_amount():
    """Test fallback comparison with different amounts."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    txn1 = _make_transaction(None, "2024-01-15", "-50.00", "Assets:Checking")
    txn2 = _make_transaction(None, "2024-01-15", "-75.00", "Assets:Checking")
    assert importer.cmp(txn1, txn2) is False


def test_cmp_no_simplefin_id_different_account():
    """Test fallback comparison with different accounts."""
    importer = SimpleFINImporter(account_mapping={"ACT-123": "Assets:Checking"})
    txn1 = _make_transaction(None, "2024-01-15", "-50.00", "Assets:Checking")
    txn2 = _make_transaction(None, "2024-01-15", "-50.00", "Assets:Savings")
    assert importer.cmp(txn1, txn2) is False
