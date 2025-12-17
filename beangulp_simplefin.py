"""Beangulp importer for SimpleFIN data.

Imports transactions from SimpleFIN JSON files into Beancount.

Usage with `simplefin fetch` output (one file per account):

    from beangulp_simplefin import SimpleFINImporter

    importers = [
        SimpleFINImporter(account_mapping={
            "ACT-abc123": "Assets:Checking:Chase",
            "ACT-def456": "Liabilities:CreditCard:Amex",
        })
    ]

Then run:
    python my_import.py extract /path/to/simplefin-data/
"""

import json
from datetime import datetime
from decimal import Decimal
from os import path

import beangulp
from beancount.core import amount, data, flags


class SimpleFINImporter(beangulp.Importer):
    """Importer for SimpleFIN JSON files.

    Handles per-account JSON files as output by `simplefin fetch`.
    Each file contains a single account with its transactions.
    """

    def __init__(self, account_mapping, currency='USD',
                 expense_account='Expenses:Uncategorized',
                 income_account='Income:Uncategorized'):
        """Create a SimpleFIN importer.

        Args:
            account_mapping: Dict mapping SimpleFIN account IDs to Beancount accounts.
                            e.g., {"ACT-xxx": "Assets:Checking:Chase"}
            currency: Default currency (default: USD).
            expense_account: Account for outflows (default: Expenses:Uncategorized).
            income_account: Account for inflows (default: Income:Uncategorized).
        """
        self.account_mapping = account_mapping
        self.currency = currency
        self.expense_account = expense_account
        self.income_account = income_account

    def identify(self, filepath):
        """Return True if this is a SimpleFIN account JSON we can handle."""
        if not filepath.endswith('.json'):
            return False
        try:
            with open(filepath) as f:
                data = json.load(f)

            # Single account format (from `simplefin fetch`)
            # Must have 'id' field and that ID must be in our mapping
            if isinstance(data, dict) and 'id' in data:
                return data['id'] in self.account_mapping

            return False
        except (json.JSONDecodeError, IOError):
            return False

    def account(self, filepath):
        """Return the account for filing."""
        try:
            with open(filepath) as f:
                data = json.load(f)
            account_id = data.get('id')
            return self.account_mapping.get(account_id, 'Assets:Unknown')
        except (json.JSONDecodeError, IOError):
            return 'Assets:Unknown'

    def filename(self, filepath):
        """Return a normalized filename for archiving."""
        return path.basename(filepath)

    def extract(self, filepath, existing):
        """Extract transactions from SimpleFIN JSON."""
        with open(filepath) as f:
            account_data = json.load(f)

        account_id = account_data.get('id')
        if account_id not in self.account_mapping:
            return []

        beancount_account = self.account_mapping[account_id]
        currency = account_data.get('currency', self.currency)

        entries = []

        # Extract transactions
        for txn in account_data.get('transactions', []):
            entry = self._extract_transaction(
                txn, beancount_account, currency, filepath
            )
            if entry:
                entries.append(entry)

        # Add balance assertion if available
        balance = account_data.get('balance')
        balance_date = account_data.get('balance-date')
        if balance is not None and balance_date:
            bal_entry = self._make_balance(
                beancount_account, balance, balance_date, currency, filepath
            )
            if bal_entry:
                entries.append(bal_entry)

        # Sort by date
        entries.sort(key=lambda e: e.date)
        return entries

    def _extract_transaction(self, txn, account_name, currency, filepath):
        """Convert a SimpleFIN transaction to a Beancount transaction."""
        posted = txn.get('posted')
        if not posted:
            return None

        # Skip pending transactions
        if txn.get('pending'):
            return None

        # Parse date - handle both timestamp and ISO string formats
        if isinstance(posted, (int, float)):
            date = datetime.fromtimestamp(posted).date()
        elif isinstance(posted, str):
            try:
                # ISO format: "2025-01-15T12:00:00+00:00"
                dt = datetime.fromisoformat(posted.replace('Z', '+00:00'))
                date = dt.date()
            except ValueError:
                return None
        else:
            return None

        # Parse amount
        amt = txn.get('amount')
        if amt is None:
            return None
        amt = Decimal(str(amt))

        description = txn.get('description', 'Unknown')
        txn_id = txn.get('id', '')

        # Build metadata
        meta = data.new_metadata(filepath, 0)
        meta['simplefin_id'] = txn_id

        # Build postings
        units = amount.Amount(amt, currency)
        posting1 = data.Posting(
            account_name, units, None, None, None,
            {'simplefin_id': txn_id}
        )

        # Counter posting
        if amt < 0:
            counter_account = self.expense_account
        else:
            counter_account = self.income_account

        posting2 = data.Posting(
            counter_account, None, None, None, None, None
        )

        return data.Transaction(
            meta, date, flags.FLAG_OKAY,
            None, description,
            data.EMPTY_SET, data.EMPTY_SET,
            [posting1, posting2]
        )

    def _make_balance(self, account_name, balance, balance_date, currency, filepath):
        """Create a balance assertion."""
        if isinstance(balance_date, (int, float)):
            date = datetime.fromtimestamp(balance_date).date()
        elif isinstance(balance_date, str):
            try:
                dt = datetime.fromisoformat(balance_date.replace('Z', '+00:00'))
                date = dt.date()
            except ValueError:
                return None
        else:
            return None

        meta = data.new_metadata(filepath, 0)
        bal = amount.Amount(Decimal(str(balance)), currency)
        return data.Balance(meta, date, account_name, bal, None, None)


# Backwards compatibility alias
Importer = SimpleFINImporter
