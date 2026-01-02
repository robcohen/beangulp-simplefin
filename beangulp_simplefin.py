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

from __future__ import annotations

__version__ = "0.2.0"

import json
from datetime import date, datetime
from decimal import Decimal
from os import path
from typing import Any

import beangulp
from beancount.core import amount, data, flags
from beancount.core.data import Balance, Directive, Transaction


class SimpleFINImporter(beangulp.Importer):
    """Importer for SimpleFIN JSON files.

    Handles per-account JSON files as output by `simplefin fetch`.
    Each file contains a single account with its transactions.
    """

    def __init__(
        self,
        account_mapping: dict[str, str],
        currency: str = "USD",
        expense_account: str = "Expenses:Uncategorized",
        income_account: str = "Income:Uncategorized",
    ) -> None:
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

    def identify(self, filepath: str) -> bool:
        """Return True if this is a SimpleFIN account JSON we can handle."""
        if not filepath.endswith(".json"):
            return False
        try:
            with open(filepath) as f:
                file_data: dict[str, Any] = json.load(f)

            # Single account format (from `simplefin fetch`)
            # Must have 'id' field and that ID must be in our mapping
            if isinstance(file_data, dict) and "id" in file_data:
                return file_data["id"] in self.account_mapping

            return False
        except (json.JSONDecodeError, OSError):
            return False

    def account(self, filepath: str) -> str:
        """Return the account for filing."""
        try:
            with open(filepath) as f:
                file_data: dict[str, Any] = json.load(f)
            account_id = file_data.get("id")
            if account_id is None:
                return "Assets:Unknown"
            return self.account_mapping.get(str(account_id), "Assets:Unknown")
        except (json.JSONDecodeError, OSError):
            return "Assets:Unknown"

    def filename(self, filepath: str) -> str:
        """Return a normalized filename for archiving."""
        return path.basename(filepath)

    def extract(self, filepath: str, existing: list[Directive]) -> list[Directive]:
        """Extract transactions from SimpleFIN JSON."""
        with open(filepath) as f:
            account_data: dict[str, Any] = json.load(f)

        account_id = account_data.get("id")
        if account_id not in self.account_mapping:
            return []

        beancount_account = self.account_mapping[account_id]
        currency = account_data.get("currency", self.currency)

        entries: list[Directive] = []

        # Extract transactions
        for txn in account_data.get("transactions", []):
            entry = self._extract_transaction(
                txn, beancount_account, currency, filepath
            )
            if entry:
                entries.append(entry)

        # Add balance assertion if available
        balance = account_data.get("balance")
        balance_date = account_data.get("balance-date")
        if balance is not None and balance_date:
            bal_entry = self._make_balance(
                beancount_account, balance, balance_date, currency, filepath
            )
            if bal_entry:
                entries.append(bal_entry)

        # Sort by date
        entries.sort(key=lambda e: e.date)
        return entries

    def _extract_transaction(
        self,
        txn: dict[str, Any],
        account_name: str,
        currency: str,
        filepath: str,
    ) -> Transaction | None:
        """Convert a SimpleFIN transaction to a Beancount transaction."""
        posted = txn.get("posted")
        if not posted:
            return None

        # Skip pending transactions
        if txn.get("pending"):
            return None

        # Parse date - handle both timestamp and ISO string formats
        txn_date = self._parse_date(posted)
        if txn_date is None:
            return None

        # Parse amount
        amt = txn.get("amount")
        if amt is None:
            return None
        amt = Decimal(str(amt))

        description = txn.get("description", "Unknown")
        txn_id = txn.get("id", "")

        # Build metadata
        meta = data.new_metadata(filepath, 0)
        meta["simplefin_id"] = txn_id

        # Build postings
        units = amount.Amount(amt, currency)
        posting1 = data.Posting(
            account_name, units, None, None, None, {"simplefin_id": txn_id}
        )

        # Counter posting
        counter_account = self.expense_account if amt < 0 else self.income_account
        posting2 = data.Posting(counter_account, None, None, None, None, None)

        return data.Transaction(
            meta,
            txn_date,
            flags.FLAG_OKAY,
            None,
            description,
            data.EMPTY_SET,
            data.EMPTY_SET,
            [posting1, posting2],
        )

    def _make_balance(
        self,
        account_name: str,
        balance: float | int | str,
        balance_date: int | float | str,
        currency: str,
        filepath: str,
    ) -> Balance | None:
        """Create a balance assertion."""
        parsed_date = self._parse_date(balance_date)
        if parsed_date is None:
            return None

        meta = data.new_metadata(filepath, 0)
        bal = amount.Amount(Decimal(str(balance)), currency)
        return data.Balance(meta, parsed_date, account_name, bal, None, None)

    def _parse_date(self, value: int | float | str) -> date | None:
        """Parse a date from timestamp or ISO string."""
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value).date()
        elif isinstance(value, str):
            try:
                # ISO format: "2025-01-15T12:00:00+00:00"
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.date()
            except ValueError:
                return None
        return None

    def cmp(self, entry1: Directive, entry2: Directive) -> bool:
        """Compare entries for deduplication.

        If both entries have simplefin_id metadata, compare by ID.
        This prevents false duplicates when transactions have the same
        date/amount but different sources (e.g., PDF statement vs API).

        Returns True if entries are considered duplicates.
        """
        # Only compare transactions
        if not isinstance(entry1, Transaction) or not isinstance(entry2, Transaction):
            return False

        # Get simplefin_id from metadata
        id1 = entry1.meta.get("simplefin_id")
        id2 = entry2.meta.get("simplefin_id")

        # If both have simplefin_id, compare by ID only
        if id1 and id2:
            return bool(id1 == id2)

        # If only one has simplefin_id, they're not duplicates of each other
        # (one is from SimpleFIN, one is from another source)
        if id1 or id2:
            return False

        # Fall back to default comparison (date, amount, account)
        if entry1.date != entry2.date:
            return False

        # Compare first posting (the main account posting)
        if entry1.postings and entry2.postings:
            p1, p2 = entry1.postings[0], entry2.postings[0]
            if p1.account != p2.account:
                return False
            if p1.units != p2.units:
                return False

        return True


# Backwards compatibility alias
Importer = SimpleFINImporter
