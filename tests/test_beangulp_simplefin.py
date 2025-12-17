import json
import tempfile
import os

from beangulp_simplefin import Importer


def test_identify_valid():
    """Test that importer identifies valid SimpleFIN JSON."""
    data = {
        "accounts": [{
            "id": "ACT-123",
            "name": "Checking",
            "transactions": []
        }]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = Importer("Assets:Checking", account_id="ACT-123")
        assert importer.identify(f.name) == True
        os.unlink(f.name)


def test_identify_wrong_account():
    """Test that importer rejects JSON with wrong account ID."""
    data = {
        "accounts": [{
            "id": "ACT-123",
            "name": "Checking",
            "transactions": []
        }]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = Importer("Assets:Checking", account_id="ACT-999")
        assert importer.identify(f.name) == False
        os.unlink(f.name)


def test_extract_expense():
    """Test extraction of expense transaction."""
    data = {
        "accounts": [{
            "id": "ACT-123",
            "name": "Checking",
            "currency": "USD",
            "transactions": [{
                "id": "TRN-001",
                "posted": 793065600,
                "description": "Coffee Shop",
                "amount": "-5.50"
            }],
            "balance": 100.00,
            "balance-date": 793065600
        }]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = Importer("Assets:Checking", account_id="ACT-123")
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
        "accounts": [{
            "id": "ACT-123",
            "name": "Checking",
            "currency": "USD",
            "transactions": [{
                "id": "TRN-002",
                "posted": 793065600,
                "description": "Direct Deposit",
                "amount": "1000.00"
            }]
        }]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        f.flush()
        importer = Importer("Assets:Checking", account_id="ACT-123")
        entries = importer.extract(f.name, [])
        os.unlink(f.name)

    assert len(entries) == 1
    txn = entries[0]
    assert txn.postings[1].account == "Income:Uncategorized"
