# Channel Profitability P&L Report

A Zoho Analytics Channel P&L system that breaks down the full Profit & Loss statement by sales channel: **B2B**, **Retail**, **Costco**, and **Unallocated**.

## Overview

This report system splits all revenue, COGS, operating expenses, and non-operating items across three sales channels plus an Unallocated bucket. It uses a chain of Zoho Analytics query tables built on top of the `Accrual Transactions (Zoho Inventory)` source data, with a final interactive pivot table that supports date range filtering.

All allocation rules (salesperson IDs, vendor IDs, account names, percentages) are stored in the **Channel Profitability Inputs** config table in Zoho Analytics. Changes to channel assignments, payroll splits, or account classifications can be made by editing the config table directly -- no SQL rebuilds required.

**Workspace ID:** `2350577000000005001`
**Org ID:** `712029089`

## Query Table Architecture

```
Source Tables + Channel Profitability Inputs (config)
  |
  +-- Invoice Channel Bridge Qry (renames "Sales Order #" -> "SO Number")
  |     |
  |     +-- Entity Channel Bridge Qry (UNION ALL: Invoices + Credit Notes)
  |           |
  |           +-- Channel Revenue Qry (JOINs config for SP/vendor/account mapping)
  |                 |
  |                 +-- Channel COGS Alloc Qry (dynamic PO cost-based split)
  |                 +-- Channel Opex Alloc Qry (JOINs config + dynamic revenue splits)
  |                 +-- Channel Other Exp Qry (JOINs config + dynamic revenue splits)
  |
  +-- Item Avg PO Cost Qry (weighted avg purchase price per product)
  |     |
  |     +-- Channel PO Cost Qry (purchase cost per channel, uses config for SP mapping)
  |
  +-- Channel Opex Payroll Qry (JOINs config for payroll % split)
  +-- Channel Opex Unalloc Qry (JOINs config for unallocated account list)
  |
  +-- Channel PL Qry (UNION ALL of all above + inline Net Profit/Loss)
        |
        +-- Channel Profitability (pivot report with date range filter)
```

## View IDs

| Query Table | View ID | Config-driven? |
|---|---|---|
| Invoice Channel Bridge Qry | `2350577000032145057` | N/A (structural) |
| Entity Channel Bridge Qry | `2350577000032154067` | N/A (structural) |
| Channel Revenue Qry | `2350577000032208002` | Yes - salesperson, vendor, costco_account, cogs_unalloc |
| Item Avg PO Cost Qry | `2350577000032152091` | N/A |
| Channel PO Cost Qry | `2350577000032148145` | Yes - salesperson |
| Channel COGS Alloc Qry | `2350577000032208013` | Yes - dynamic PO cost proportions |
| Channel Opex Payroll Qry | `2350577000032206002` | Yes - payroll_pct |
| Channel Opex Alloc Qry | `2350577000032209002` | Yes - ad_pct, payment_account, commission_fee |
| Channel Opex Unalloc Qry | `2350577000032207013` | Yes - unalloc_opex |
| Channel Other Exp Qry | `2350577000032209013` | Yes - unalloc_other_exp |
| Channel PL Qry | `2350577000032210002` | N/A (UNION ALL) |
| **Channel Profitability** (pivot) | `2350577000032206012` | - |
| Channel Profitability Inputs | `2350577000032148135` | Config table |

**Folder:** Channel Profitability (`2350577000032146061`)

## Channel Profitability Inputs (Config Table)

All allocation rules are stored in the `Channel Profitability Inputs` table with columns: **Type**, **Key**, **Channel**, **Value**, **Description**.

### Config Types

| Type | Purpose | How to update |
|---|---|---|
| `salesperson` | Maps Sales Person ID to channel | Add row: Type=salesperson, Key=SP ID, Channel=B2B/Costco. Unlisted SPs default to Retail. |
| `vendor` | Maps Vendor ID to channel for COGS bills | Add row: Type=vendor, Key=Vendor ID, Channel=Retail/B2B/Costco |
| `costco_account` | Account names tagged Costco when no invoice match | Add row: Type=costco_account, Key=exact account name, Channel=Costco |
| `so_prefix` | SO# prefix rules (structural, rarely changes) | Key=prefix, Channel=target, Value=match length |
| `default_channel` | Fallback rules for blank salesperson | Key=blank_sp_invoice/blank_sp_creditnote/other_sp |
| `payroll_pct` | Payroll split per account per channel | Key=account name, Channel=B2B/Retail/Costco/Unallocated, Value=decimal (must sum to 1.0) |
| `ad_pct` | Advertising split per account per channel | Key=account name, Channel=B2B/Retail, Value=decimal (must sum to 1.0) |
| `commission_fee` | Commission accounts split B2B/Retail by revenue (no Costco) | Key=account name, Channel=B2B/Retail (split is dynamic from revenue) |
| `payment_account` | Payment processing accounts | Key=account name, Channel=Retail, Value=1.0 (100%) |
| `unalloc_opex` | OpEx accounts kept 100% Unallocated | Key=account name, Channel=Unallocated |
| `unalloc_other_exp` | Non-operating expense accounts kept Unallocated | Key=account name, Channel=Unallocated |
| `cogs_unalloc` | COGS items kept Unallocated (account name or entity type) | Key=account name or entity type, Channel=Unallocated |

### Important Notes

- **Key column must be Plain Text** -- do not open in Excel before uploading (converts IDs to scientific notation)
- **Payroll percentages must sum to 1.0** across all 4 channels for each account
- **Import mode: use "Truncate and Add"** when re-importing to avoid duplicates
- Adding a new salesperson, vendor, or account to the config table takes effect immediately (query tables re-evaluate on refresh)

## Channel Identification Logic

### Revenue / COGS (Channel Revenue Qry)

**Priority order of channel assignment (all config-driven except SO prefix):**

1. **Costco-named accounts** -- JOINs to config `costco_account` type. Tags transactions as Costco when no invoice/credit note match.

2. **Retail vendor bills/expenses** -- JOINs to config `vendor` type. Tags vendor COGS bills to specified channel.

3. **Pro-rata COGS allocation** -- Shared COGS with no channel link (excluding `cogs_unalloc` items from config). Split dynamically by weighted average PO purchase cost per channel.

4. **Invoice/Credit Note salesperson** -- JOINs to config `salesperson` type via Entity Channel Bridge. Mapped SPs get their configured channel; unmapped SPs default to Retail.

5. **SO# prefix fallback** (structural) -- For blank-salesperson invoices: `0089400` prefix = Costco, `SO-EB-`/`SO-MB-` = Retail, else B2B.

6. **Unallocated** -- Everything else with no entity match and no config rule.

### Operating Expenses

**Payroll (Channel Opex Payroll Qry):**
- Single JOIN to config `payroll_pct` type
- Each transaction auto-generates one row per channel (B2B/Retail/Costco/Unallocated) with the configured percentage
- Current split derived from Payroll Allocation.xlsx (36 employees, 9 unallocated)

**Allocated OpEx (Channel Opex Alloc Qry):**
- **Advertising**: JOINs to config `ad_pct` (currently B2B 10% / Retail 90%)
- **Payment processing**: JOINs to config `payment_account` (currently 100% Retail)
- **Commissions and fees**: JOINs to config `commission_fee` -- split B2B/Retail by dynamic revenue ratio (Costco excluded)
- **Other OpEx**: Everything not in any config type -- split by dynamic all-time revenue ratio (B2B/Retail/Costco)

**Unallocated OpEx (Channel Opex Unalloc Qry):**
- JOINs to config `unalloc_opex` type -- currently Exchange Gain/Loss and IRAP reimbursements

### Non-Operating Expenses (Channel Other Exp Qry)

- **Unallocated**: JOINs to config `unalloc_other_exp` -- SRED, IRAP, CanExport, Amortization, etc.
- **Allocated**: Everything NOT in `unalloc_other_exp` config -- split by dynamic revenue ratio

### COGS Pro-Rata Allocation (Channel COGS Alloc Qry)

Shared COGS (freight, customs, certificates with no invoice match) are allocated using **actual purchase order costs**, not revenue percentages:

```
Channel share = Shared COGS * (Channel PO cost / Total PO cost)
```

PO costs are computed from `Purchase Order Items` weighted average prices, joined to `Invoice Items` and channeled via salesperson mapping from the config table.

### Net Profit/Loss

Calculated inline within Channel PL Qry:
```
Net P/L = SUM(Operating Income + Non-Operating Income) - SUM(COGS + OpEx + Non-Operating Expense)
```

## Dynamic vs Structural Elements

| Element | Type | How it updates |
|---|---|---|
| Salesperson channel mapping | Config-driven | Edit config table |
| Vendor channel mapping | Config-driven | Edit config table |
| Costco account names | Config-driven | Edit config table |
| Payroll split percentages | Config-driven | Edit config table (must sum to 1.0) |
| Advertising split percentages | Config-driven | Edit config table |
| Payment processing accounts | Config-driven | Edit config table |
| Commission accounts | Config-driven | Edit config table |
| Unallocated account lists | Config-driven | Edit config table |
| COGS pro-rata split | Fully dynamic | Auto-updates from PO purchase costs |
| Commission fee split (B2B/Retail) | Fully dynamic | Auto-updates from revenue ratio |
| Other OpEx split | Fully dynamic | Auto-updates from revenue ratio |
| Other Expense split | Fully dynamic | Auto-updates from revenue ratio |
| SO# prefix rules | Structural (SQL) | Requires query table rebuild |
| Default blank-SP channel | Structural (SQL) | Requires query table rebuild |

## Zoho Analytics SQL Constraints

Key limitations discovered during development:

| Constraint | Workaround |
|---|---|
| `LIKE` operator not supported in query tables | Use `LEFT(col, n) = 'prefix'` |
| `#` character in column names breaks CASE WHEN | Created bridge table to rename `Sales Order #` to `SO Number` |
| `&` in any CONFIG field causes JSON parse error | Avoid ampersands in names, descriptions, SQL |
| Nested `CASE WHEN ... THEN CASE WHEN` fails | Flatten into single-level CASE WHEN with AND conditions |
| SQL max ~4,600 chars per query table | Split into multiple query tables |
| Max 5 levels of query-over-query tables | Minimized chain depth; embedded Net P/L as inline subquery |
| Table alias prefix appears in output column names | Reference output columns with prefix (e.g., `a.Account Name`) |
| Column display name max 100 chars | Add explicit `AS "Amount"` alias for computed columns |
| Intermittent 7005 errors on valid SQL | Retry the same request |
| Multiple LEFT JOINs to same table need unique aliases | Use ca, cv, sp, cu etc. for each config type join |

## Key Findings

### Costco Channel Revenue Reconciliation

Comparing Zoho Analytics Costco Operating Income vs Costco Portal payment history revealed reclassification journals that were being double-counted:

- **Discount - Costco Sales** journals (debit side): tagged Costco via account name
- **Other Charges - Shipping Discount** journals (credit side): same journals, but were going to Unallocated

Fix: Added `Other Charges -Shipping Discount` to the Costco account name config so both sides of the reclassification journals are tagged Costco.

### Costco Returns and Re-sales

Returned Costco items are re-sold through Retail/B2B channels. The accounting correctly handles this:
- Credit notes reverse both revenue and COGS for Costco
- Re-sale invoices create new revenue and COGS for Retail/B2B
- The "Cost of Goods Sold Costco" account appearing in Retail/B2B represents re-sold Costco returns

### COGS Allocation: PO Cost vs Revenue

Initial approach used hardcoded revenue percentages. Replaced with dynamic PO purchase cost weighting which better reflects actual cost consumption per channel:

| Channel | Revenue Weight | PO Cost Weight |
|---|---|---|
| B2B | 37.3% | 31.3% |
| Retail | 49.9% | 56.3% |
| Costco | 12.8% | 12.5% |

### Unallocated Items

Items intentionally kept as Unallocated (configurable via config table):
- `Subcontractors - COGS` (Adam Nunn)
- `inventory_adjustment_by_quantity` (stock count adjustments)
- `Exchange Gain or Loss` (OpEx)
- `Payroll-IRAP` reimbursement accounts
- SRED, IRAP, CanExport, and other grant/compliance accounts (Other Expense)
- `sales_return` entity type revenue

## Files

| File | Description |
|---|---|
| `README.md` | This documentation |
| `Payroll Allocation.xlsx` | Employee-level channel allocation spreadsheet (36 employees) |
| `channel_config_v2.csv` | Config table data (reference -- import via API to preserve IDs) |
| `import_config.py` | Script to import config data via Zoho REST API (preserves text formatting) |
| `refactor_to_config.py` | Script to rebuild all query tables using config table JOINs |
| `rebuild_cogs_alloc.py` | Script to rebuild COGS allocation with PO cost-based splits |
| `channel_pl_sql.txt` | Original monolithic SQL (pre-split, reference only) |
| `channel_sqls_v2.py` | Earlier version of split SQL strings (reference only) |
| `PAYMENTHISTORY_20260416_144706_download.csv` | Costco portal payment history for FY25 reconciliation |
| `costco_inv_numbers.txt` | Extracted Costco portal invoice numbers for cross-reference |

## API Credentials

Config table imports and query table rebuilds use the Zoho Analytics REST API with OAuth. Scripts use a refresh token to auto-generate access tokens. Client credentials are stored in the Python scripts (Self Client app in Zoho API Console).
