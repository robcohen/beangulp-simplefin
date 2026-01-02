# SimpleFIN Integration Guide

This guide documents the SimpleFIN integration for fetching bank transactions via the SimpleFIN Bridge API.

## Overview

SimpleFIN Bridge connects to financial institutions and provides transaction data via a simple API. This integration:

1. **Fetches** account data and transactions using the `simplefin` CLI
2. **Imports** transactions to beancount using `beangulp-simplefin`
3. **Deduplicates** against existing ledger entries

## Setup

### 1. Install Dependencies

```bash
uv pip install simplefin beangulp-simplefin
```

### 2. Configure SimpleFIN Access

Get your access URL from [SimpleFIN Bridge](https://beta-bridge.simplefin.org/):

```bash
export SIMPLEFIN_ACCESS_URL="https://beta-bridge.simplefin.org/simplefin/accounts/YOUR_TOKEN"
```

Add to your shell profile or `.env` file.

### 3. Map SimpleFIN Accounts

In `importers/institutions.yaml`, add `simplefin_id` to each account:

```yaml
institutions:
  chase:
    accounts:
      - name: Chase Personal Checking
        account: Assets:Checking:Chase-Personal
        simplefin_id: ACT-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

To find your SimpleFIN account IDs:

```bash
simplefin accounts --format json | jq '.[].id'
```

## Usage

### Fetch and Extract

```bash
# Fetch from all sources including SimpleFIN
just fetch

# Extract transactions to pending-review
just extract
```

### Manual Commands

```bash
# List SimpleFIN accounts
simplefin accounts

# Get transactions for specific account
simplefin transactions ACT-xxx --lookback-days 30 --format json

# Test importer on fetched data
python importers/config.py extract raw-api/simplefin/
```

## File Structure

After fetch, SimpleFIN data is stored in:

```
raw-api/simplefin/
├── accounts.json                              # All account metadata
├── transactions_ACT-xxx.json                  # Per-account transaction files
└── transactions_ACT-yyy.json
```

Each transaction file contains:

```json
{
  "id": "ACT-xxx",
  "name": "Account Name",
  "org": {"domain": "www.bank.com", "name": "Bank Name"},
  "currency": "USD",
  "balance": "1234.56",
  "transactions": [
    {
      "id": "TRN-xxx",
      "posted": "2025-12-28T12:00:00+00:00",
      "amount": "-50.00",
      "description": "MERCHANT NAME",
      "payee": "Merchant"
    }
  ]
}
```

## Troubleshooting

### Invalid JSON from SimpleFIN CLI

**Symptom:** `JSONDecodeError: Invalid control character`

**Cause:** SimpleFIN CLI outputs invalid JSON with literal newlines in string values (e.g., account names with line breaks).

**Fix:** The fetch script (`scripts/fetch.py`) automatically sanitizes JSON by detecting continuation lines.

### smart_importer Feature Mismatch Error

**Symptom:** `ValueError: X has N features, but SVC is expecting M features`

**Cause:** The ML model was trained on different data than what's being predicted.

**Fix:** `importers/config.py` uses `RobustPredictPostings` which catches this error and returns transactions without ML predictions.

### All Transactions Marked as Duplicates

**Symptom:** Extract shows "No new transactions" but transactions are clearly new.

**Cause:** beangulp's default deduplication compares by date/amount/account, not by `simplefin_id`. If you previously imported the same transactions from PDF statements, they match as duplicates.

**Solutions:**

1. **Use `simplefin_id` for deduplication** (requires updating beangulp-simplefin):

```python
# In beangulp_simplefin.py, add custom cmp method:
@staticmethod
def cmp(entry1, entry2) -> bool:
    """Compare by simplefin_id if available."""
    id1 = entry1.meta.get("simplefin_id")
    id2 = entry2.meta.get("simplefin_id")
    if id1 and id2:
        return id1 == id2
    # Fall back to default comparison
    return default_cmp(entry1, entry2)
```

2. **Extract without deduplication** for initial import:

```bash
python importers/config.py extract raw-api/simplefin/
```

3. **Remove duplicate source data** - if you have both PDF statements and SimpleFIN for the same accounts, choose one source.

### SimpleFIN CLI Command Not Found

**Symptom:** `Error: No such command 'fetch'`

**Cause:** The `simplefin` CLI changed its interface. There's no `fetch` command.

**Fix:** Use `simplefin accounts` and `simplefin transactions ACCOUNT_ID` instead.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  SimpleFIN API  │────▶│  scripts/fetch.py │────▶│  raw-api/       │
│  (beta-bridge)  │     │  (simplefin CLI)  │     │  simplefin/     │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  pending-review/│◀────│ scripts/extract.py│◀────│ beangulp-       │
│  simplefin.bean │     │  (beangulp)       │     │ simplefin       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Account Mapping Reference

The `simplefin_id` values in `institutions.yaml` map SimpleFIN account IDs to beancount accounts. The importer uses this mapping to:

1. **Identify** which files to process (only accounts in mapping)
2. **Route** transactions to correct beancount accounts
3. **Set currency** based on account configuration

Example mapping from `institutions.yaml`:

```yaml
# Personal checking
simplefin_id: ACT-dcf81277-6684-4a8e-b348-86ae2b3762ff
account: Assets:Checking:Chase-Personal

# Credit card
simplefin_id: ACT-367a413f-d480-4ffb-8a7a-7789c9d096cc
account: Liabilities:CreditCard:Amex-Blue-Cash-Preferred

# Brokerage
simplefin_id: ACT-004a2b12-d6eb-4b74-8580-add78eb5ad58
account: Assets:Brokerage:Schwab
```

## Transaction Metadata

Imported transactions include:

```beancount
2025-12-28 * "H-E-B" "HEB CURBSIDE SAN ANTONIO TX"
  simplefin_id: "TRN-fc32100f-681b-47b5-b443-85c93153b369"
  Liabilities:CreditCard:Amex-Blue-Cash-Preferred  -267.56 USD
  Expenses:Uncategorized
```

The `simplefin_id` metadata enables:
- Tracking transaction source
- Preventing duplicate imports (when properly configured)
- Auditing imported data

## Related Files

- `scripts/fetch.py` - Fetches SimpleFIN data (and other sources)
- `scripts/extract.py` - Extracts transactions to pending-review
- `importers/config.py` - beangulp configuration with ML hooks
- `importers/registry.py` - Loads SimpleFIN importer with account mapping
- `importers/institutions.yaml` - Account configuration including `simplefin_id`
