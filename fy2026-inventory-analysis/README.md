# FY2026 Inventory & Sales Analysis — Zoho Analytics

**Workspace:** Zoho One Report — org `712029089`, workspace `2350577000000005001`
**Fiscal Year:** November 2025 – October 2026

---

## Overview

This folder contains all SQL queries and data files for the FY2026 sales vs plan and inventory coverage analysis built in Zoho Analytics.

---

## Tracked SKUs (19 total)

| Family | SKUs |
|---|---|
| D50 | END50R14A20C, END50R14M20C, END50R14M30C, END50R14M17C, END50R14A17C, END50R14M40C |
| ST50 | ENST50R14C20C, ENST50R14M20C, ENST50R14C17D, ENST50R14M17C, ENST50R14C17C, ENST50R14C17E |
| FOENV | FOENV35W12.8A-BLACK-23, FOENV35W12.8A-BLUE-23, FOENV35W12.8A-RED-23 |
| FLEXOL / FLTRK | FLEXOL-BLKS, FLEXOL-ORS, FLTRK-BLKS, FLTRK-ORS |

---

## Data Files

| File | Description |
|---|---|
| `data/plan_2026_monthly.csv` | Monthly plan: SKU × 12 months (Nov 2025–Oct 2026) |
| `data/plan_2026_daily.csv` | Daily plan: SKU × 365 days — import as `2026 Daily Plan` in Zoho Analytics |

### Generating `plan_2026_daily.csv`
```js
// Divides monthly planned qty by days in month to get a flat daily rate
// Run from project root: node generate_daily_plan.js
```
See `plan_2026_daily.csv` — 6,935 rows (19 SKUs × 365 days).

---

## Query Table Dependency Chain

```
Zoho Inventory (live sync)
├── Sales Order Items (Zoho Inventory)
├── Sales Orders (Zoho Inventory)
├── Items (Zoho Inventory)
└── Inventory Count Value Warehouse Qry
        │
        ▼
[01] 2026 Sales Orders with SKU          (ID: 2350577000030862193)
[02] Stock On Hand per SKU               (ID: 2350577000030849308)
[03] 2026 Sales vs Plan - Pivot Ready    (ID: 2350577000030856207)
[04] YTD Actuals per SKU                 (ID: 2350577000030860355)
[05] YTD Plan per SKU                    (ID: 2350577000030860433)  ← uses 2026 Daily Plan
[06] Next 2M Plan per SKU                (ID: 2350577000030862357)  ← uses 2026 Plan - SKU Monthly
[07] Inventory Coverage 2026             (ID: 2350577000030853258)
[08] SKU Performance Overview 2026       (ID: 2350577000030846392)
[09] Stock Coverage by Day               (ID: 2350577000030856336)  ← uses 2026 Daily Plan
[10] Stock Coverage - Multi Window       (ID: 2350577000030851706)  ← uses 2026 Daily Plan
[11] Stock Coverage by Day + YTD         (ID: 2350577000030851908)
```

---

## Reports & Pivots

| Report | View ID | Base Table |
|---|---|---|
| 2026 Sales vs Plan - Pivot | 2350577000030857510 | 2026 Sales vs Plan - Pivot Ready |
| Inventory Coverage Report 2026 | 2350577000030856321 | Inventory Coverage 2026 |
| SKU Performance Overview Report 2026 | 2350577000030853407 | SKU Performance Overview 2026 |
| Inventory Coverage - Custom Range | 2350577000030849614 | Stock Coverage by Day |
| Inventory Coverage - 4/6/8 Week Windows | 2350577000030853425 | Stock Coverage - Multi Window |
| Inventory Coverage - Custom Range Pivot | 2350577000030856503 | Stock Coverage by Day + YTD |

---

## Dynamic Behaviour

All queries use `CURDATE()` — no hardcoded dates except the FY start (`2025-11-01`):

| What updates | How |
|---|---|
| YTD Actual & Plan | `WHERE date <= CURDATE()` advances daily |
| Next 2M Plan window | `DATE_ADD(CURDATE(), INTERVAL 1/2 MONTH)` rolls each month |
| 4W / 6W / 8W coverage | `DATE_ADD(CURDATE(), INTERVAL N DAY)` rolls daily |
| Stock levels | Synced from Zoho Inventory on workspace sync schedule |

---

## Notes

- **Arithmetic in SELECT** is not supported in Zoho Analytics QueryTables — computed columns (e.g. `Stock + InTransit`) must be added as formula columns in the report UI.
- **Table alias prefixes** are preserved in column names (e.g. `i."SKU"` becomes column `i.SKU`). Use explicit `AS` aliases to avoid dot-notation in downstream queries.
- **Negative stock** is valid — indicates pre-sell inventory.
- SO statuses excluded: `void`, `draft`, `pending_approval`, `approved`.
