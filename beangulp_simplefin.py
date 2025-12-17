"""Beangulp importer for SimpleFIN data.

Imports transactions from SimpleFIN JSON files into Beancount.
"""

import json
from datetime import datetime
from decimal import Decimal
from os import path

import beangulp
from beancount.core import amount, data, flags


def sanitize_account_name(name):
    """Convert account name to valid Beancount account component."""
    clean = name.replace(' ', '-').replace('/', '-').replace('&', '-')
    while '--' in clean:
        clean = clean.replace('--', '-')
    return clean.strip('-')


class Importer(beangulp.Importer):
    """Importer for SimpleFIN JSON files."""

    def __init__(self, account, account_id=None, currency='USD',
                 expense_account='Expenses:Uncategorized',
                 income_account='Income:Uncategorized'):
        """Create a SimpleFIN importer.

        Args:
            account: Beancount account for this SimpleFIN account.
            account_id: SimpleFIN account ID (ACT-xxx). If None, imports all accounts.
            currency: Default currency (default: USD).
            expense_account: Account for outflows (default: Expenses:Uncategorized).
            income_account: Account for inflows (default: Income:Uncategorized).
        """
        self.account = account
        self.account_id = account_id
        self.currency = currency
        self.expense_account = expense_account
        self.income_account = income_account

    def identify(self, filepath):
        """Return True if this file is a SimpleFIN JSON file."""
        if not filepath.endswith('.json'):
            return False
        try:
            with open(filepath) as f:
                data = json.load(f)
            # Check for SimpleFIN structure
            if 'accounts' not in data:
                return False
            # If account_id specified, check it exists in the file
            if self.account_id:
                for acct in data.get('accounts', []):
                    if acct.get('id') == self.account_id:
                        return True
                return False
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def account(self, filepath):
        """Return the account for filing."""
        return self._account

    @property
    def _account(self):
        return self.account

    def filename(self, filepath):
        """Return a normalized filename for archiving."""
        return f"simplefin.{path.basename(filepath)}"

    def extract(self, filepath, existing):
        """Extract transactions from SimpleFIN JSON."""
        with open(filepath) as f:
            sfin_data = json.load(f)

        entries = []
        accounts = sfin_data.get('accounts', [])

        for sfin_account in accounts:
            # Skip if we're filtering by account_id and this isn't it
            if self.account_id and sfin_account.get('id') != self.account_id:
                continue

            account_name = self._account
            currency = sfin_account.get('currency', self.currency)

            for txn in sfin_account.get('transactions', []):
                entry = self._extract_transaction(
                    txn, account_name, currency, filepath
                )
                if entry:
                    entries.append(entry)

            # Add balance assertion if available
            balance = sfin_account.get('balance')
            balance_date = sfin_account.get('balance-date')
            if balance is not None and balance_date:
                bal_entry = self._make_balance(
                    account_name, balance, balance_date, currency, filepath
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

        # Parse date
        if isinstance(posted, (int, float)):
            date = datetime.fromtimestamp(posted).date()
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
        else:
            return None

        meta = data.new_metadata(filepath, 0)
        bal = amount.Amount(Decimal(str(balance)), currency)
        return data.Balance(meta, date, account_name, bal, None, None)
