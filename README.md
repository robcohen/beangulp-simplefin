# Beangulp SimpleFIN Importer

[![PyPI version](https://img.shields.io/pypi/v/beangulp-simplefin.svg)](https://pypi.org/project/beangulp-simplefin/)
[![Python versions](https://img.shields.io/pypi/pyversions/beangulp-simplefin.svg)](https://pypi.org/project/beangulp-simplefin/)
[![CI](https://github.com/robcohen/beangulp-simplefin/actions/workflows/ci.yml/badge.svg)](https://github.com/robcohen/beangulp-simplefin/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A [beangulp](https://github.com/beancount/beangulp) importer for [SimpleFIN](https://www.simplefin.org/) data.

## Installation

```bash
uv add beangulp-simplefin
```

Or with pip:

```bash
pip install beangulp-simplefin
```

## Usage

### 1. Download SimpleFIN data

Use the SimpleFIN CLI to download your account data:

```bash
uv add simplefin
simplefin fetch --output ~/simplefin-data/
```

This creates one JSON file per account in the output directory.

### 2. Configure your importer

Create an `import.py` configuration:

```python
from beangulp_simplefin import SimpleFINImporter
import beangulp

importers = [
    SimpleFINImporter(account_mapping={
        "ACT-xxx-xxx": "Assets:Checking:Chase",
        "ACT-yyy-yyy": "Assets:Checking:Schwab",
        "ACT-zzz-zzz": "Liabilities:CreditCard:Amex",
    })
]

if __name__ == "__main__":
    beangulp.Ingest(importers)()
```

### 3. Extract transactions

```bash
python import.py extract ~/simplefin-data/ >> ledger.beancount
```

### 4. Archive the files (optional)

```bash
python import.py archive ~/simplefin-data/ -o documents/
```

## Importer Options

```python
SimpleFINImporter(
    account_mapping,        # Dict mapping SimpleFIN account IDs to Beancount accounts
    currency='USD',         # Default currency
    expense_account='Expenses:Uncategorized',   # For outflows
    income_account='Income:Uncategorized',      # For inflows
)
```

## Output Format

Each transaction becomes a Beancount entry:

```beancount
2024-01-15 * "GROCERY STORE #123"
  simplefin_id: "TRN-abc123"
  Assets:Checking:Chase  -45.67 USD
    simplefin_id: "TRN-abc123"
  Expenses:Uncategorized

2024-01-16 balance Assets:Checking:Chase  1234.56 USD
```

## Workflow Example

```bash
# Daily/weekly sync
simplefin fetch --output ~/simplefin-data/
python import.py extract ~/simplefin-data/ >> ledger.beancount
bean-check ledger.beancount
```

## Related Tools

- [simplefin](https://github.com/simplefin/simplefin-py) - SimpleFIN Python client
- [sfin2beancount](https://github.com/simplefin/sfin2beancount) - Pipe-based SimpleFIN to Beancount converter
- [sfin2ledger](https://github.com/simplefin/sfin2ledger) - SimpleFIN to Ledger converter

## License

MIT
