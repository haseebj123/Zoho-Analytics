# Channel Profitability P&L Report

A Zoho Analytics Channel P&L system that breaks down the full Profit & Loss statement by sales channel: **B2B**, **Retail**, **Costco**, and **Unallocated**.

## Overview

This report system splits all revenue, COGS, operating expenses, and non-operating items across three sales channels plus an Unallocated bucket. It uses a chain of Zoho Analytics query tables built on top of the `Accrual Transactions (Zoho Inventory)` source data, with a final interactive pivot table that supports date range filtering.

**Workspace ID:** `2350577000000005001`
**Org ID:** `712029089`

## Query Table Architecture

```
Source Tables
  |
  +-- Invoice Channel Bridge Qry (renames "Sales Order #" -> "SO Number")
  |     |
  |     +-- Entity Channel Bridge Qry (UNION ALL: Invoices + Credit Notes)
  |           |
  |           +-- Channel Revenue Qry (Income + COGS with channel logic)
  |                 |
  |                 +-- Channel COGS Alloc Qry (pro-rata split of shared COGS)
  |
  +-- Channel Opex Payroll Qry (payroll 4-way split)
  +-- Channel Opex Alloc Qry (advertising + payment processing + other opex)
  +-- Channel Opex Unalloc Qry (Exchange Gain/Loss + IRAP reimbursements)
  +-- Channel Other Exp Qry (non-operating expenses)
  |
  +-- Channel PL Qry (UNION ALL of all above + inline Net Profit/Loss)
        |
        +-- Channel Profitability (pivot report)
```

## View IDs

| Query Table | View ID | Level |
|---|---|---|
| Invoice Channel Bridge Qry | `2350577000032152029` | 1 |
| Entity Channel Bridge Qry | `2350577000032154023` | 2 |
| Channel Revenue Qry | `2350577000032150027` | 3 |
| Channel COGS Alloc Qry | `2350577000032154049` | 4 |
| Channel Opex Payroll Qry | `2350577000032155062` | 1 |
| Channel Opex Alloc Qry | `2350577000032153094` | 1 |
| Channel Opex Unalloc Qry | `2350577000032144016` | 1 |
| Channel Other Exp Qry | `2350577000032147036` | 1 |
| Channel PL Qry | `2350577000032144027` | 5 |
| **Channel Profitability** (pivot) | `2350577000032154059` | - |

## Channel Identification Logic

### Revenue / COGS (Channel Revenue Qry)

**Priority order of channel assignment:**

1. **Costco-named accounts** (no entity match required):
   - `Discount - Costco Sales`
   - `Shipping, Freight -Costco`
   - `Cost of Labour - Costco`
   - `Sales of Product Income Costco`
   - `Cost of Goods Sold Costco`
   - `Other Charges -Shipping Discount` (reclassification journals)

2. **Retail vendor bills/expenses** (11 specific vendor IDs):
   - Canpar Express, City Business Brokerage LLC, Bloom, Han-Lin Yong, Hammad Mansoor, Amir Hossein Qaidzadeh, David Burnett, Jason Avenido, Denis Charlebois, Rolls Right Industries Ltd., Worldwide Express/GlobalTranz/Unishippers

3. **Pro-rata COGS allocation** (shared costs with no channel link):
   - Splits by all-time revenue %: B2B 37.25% / Retail 49.95% / Costco 12.80%
   - Excludes: `Subcontractors - COGS` and `inventory_adjustment_by_quantity` (kept Unallocated)

4. **Invoice/Credit Note salesperson** (entity match via Entity Channel Bridge):
   - Mitch Merker (`1979954000002036262`) or Serge Giguere (`1979954000044158860`) -> **B2B**
   - Costco Online (`1979954000047575788`) or Costco RoadShow (`1979954000053988204`) -> **Costco**
   - Blank salesperson + SO# prefix `0089400` -> **Costco**
   - Blank salesperson + SO# prefix `SO-EB-` or `SO-MB-` -> **Retail**
   - Blank salesperson (credit notes) -> **Retail**
   - Blank salesperson (invoices, no SO match) -> **B2B**
   - All other salespersons -> **Retail**

5. **Unallocated**: Everything else with no entity match and no rule above

### Operating Expenses (3 query tables)

**Payroll (Channel Opex Payroll Qry)** - 4-way split based on employee allocation:
| Channel | % | Source |
|---|---|---|
| B2B | 30.6944% | Payroll Allocation.xlsx (1105/3600) |
| Retail | 36.5278% | (1315/3600) |
| Costco | 7.7778% | (280/3600) |
| Unallocated | 25.0000% | 9 unallocated employees (900/3600) |

Accounts: `Payroll Expense`, `Payroll Expense:Taxes`, `Payroll Expense:Wages`, `Salaries and Employee Wages`, `EHT Expense`, `Work Safe BC Expense`, `Payroll-SRED Wages Reimbursement`

**Allocated OpEx (Channel Opex Alloc Qry):**
- **Advertising** (`Advertising`, `Advertising And Marketing`, `Promotional`): B2B 10% / Retail 90%
- **Payment processing** (`Stripe Fee`, `Stripe Fees`, `Card Fee`, `Paypal charges`, `Shopify Fee`, etc.): Retail 100%
- **Other OpEx** (everything not payroll/advertising/payment/Exchange): Revenue % split (B2B 37.25% / Retail 49.95% / Costco 12.80%)

**Unallocated OpEx (Channel Opex Unalloc Qry):**
- `Exchange Gain or Loss`
- `Payroll-IRAP -WSBC - BCTech -ECO Wages Reimbursement`
- `Payroll-IRAP Wages Reimbursement`

### Non-Operating Expenses (Channel Other Exp Qry)

- **Allocated** (revenue % split): All Other Expense accounts except those below
- **Unallocated**: SRED accounts, IRAP accounts, CanExport, Security, Exchange, Amortization, Provisions for Income Tax, Penalties and settlements, Reconciliation Discrepancies

### Net Profit/Loss

Calculated inline within Channel PL Qry using a subquery:
```
Net P/L = SUM(Operating Income + Non-Operating Income) - SUM(COGS + OpEx + Non-Operating Expense)
```

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
| Table alias prefix appears in output column names | Reference output columns with prefix (e.g., `a.Account Name`, `t.Transaction Date`) |
| Intermittent 7005 errors on valid SQL | Retry the same request |

## Key Findings

### Costco Channel Revenue Reconciliation

Comparing Zoho Analytics Costco Operating Income vs Costco Portal payment history revealed reclassification journals that were being double-counted:

- **Discount - Costco Sales** journals (debit side): tagged Costco via account name
- **Other Charges - Shipping Discount** journals (credit side): same journals, but were going to Unallocated

Fix: Added `Other Charges -Shipping Discount` to the Costco account name list so both sides of the reclassification journals are tagged Costco.

### Costco Returns and Re-sales

Returned Costco items are re-sold through Retail/B2B channels. The accounting correctly handles this:
- Credit notes reverse both revenue and COGS for Costco
- Re-sale invoices create new revenue and COGS for Retail/B2B
- The "Cost of Goods Sold Costco" account appearing in Retail ($124K) and B2B ($63K) represents re-sold Costco returns

### Unallocated Items

Items intentionally kept as Unallocated:
- `Subcontractors - COGS` (Adam Nunn)
- `inventory_adjustment_by_quantity` (stock count adjustments)
- `Exchange Gain or Loss` (OpEx)
- `Payroll-IRAP` reimbursement accounts
- SRED, IRAP, CanExport, and other grant/compliance accounts (Other Expense)
- `sales_return` entity type revenue (-$3,203 in FY26 H1)

## Files

| File | Description |
|---|---|
| `README.md` | This documentation |
| `Payroll Allocation.xlsx` | Employee-level channel allocation spreadsheet (36 employees) |
| `channel_pl_sql.txt` | Original monolithic SQL (pre-split, reference only) |
| `channel_sqls_v2.py` | Earlier version of split SQL strings (reference only) |
| `PAYMENTHISTORY_20260416_144706_download.csv` | Costco portal payment history for FY25 reconciliation |
| `costco_inv_numbers.txt` | Extracted Costco portal invoice numbers for cross-reference |
