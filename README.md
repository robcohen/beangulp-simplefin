# Beangulp SimpleFIN Importer

A [beangulp](https://github.com/beancount/beangulp) importer for [SimpleFIN](https://www.simplefin.org/) data.

## Installation

```bash
pip install git+https://github.com/simplefin/beangulp-simplefin.git
```

## Usage

### 1. Download SimpleFIN data

Use the SimpleFIN CLI or curl to download your account data:

```bash
curl "${ACCESS_URL}/accounts" > simplefin.json
```

Or using the `simplefin` Python package:

```bash
pip install simplefin
simplefin accounts > simplefin.json
```

### 2. Configure your importer

Create an `import.py` configuration:

```python
from beangulp_simplefin import Importer
import beangulp

importers = [
    Importer("Assets:Checking:Chase", account_id="ACT-xxx-xxx"),
    Importer("Assets:Checking:Schwab", account_id="ACT-yyy-yyy"),
    Importer("Liabilities:CreditCard:Amex", account_id="ACT-zzz-zzz"),
]

if __name__ == "__main__":
    beangulp.Ingest(importers)()
```

### 3. Extract transactions

```bash
python import.py extract simplefin.json >> ledger.beancount
```

### 4. Archive the file (optional)

```bash
python import.py archive simplefin.json -o documents/
```

## Importer Options

```python
Importer(
    account,            # Beancount account (required)
    account_id=None,    # SimpleFIN account ID (ACT-xxx), None imports all
    currency='USD',     # Default currency
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
curl "${ACCESS_URL}/accounts" > ~/Downloads/simplefin.json
python import.py extract ~/Downloads/simplefin.json >> ledger.beancount
bean-check ledger.beancount
```

## Related Tools

- [sfin2beancount](https://github.com/simplefin/sfin2beancount) - Pipe-based SimpleFIN to Beancount converter
- [sfin2ledger](https://github.com/simplefin/sfin2ledger) - SimpleFIN to Ledger converter

## License

MIT
