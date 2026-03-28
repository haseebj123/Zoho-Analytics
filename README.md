# Zoho Analytics — Sales & Marketing KPI Queries

SQL queries powering the **Sales and Marketing KPI** workspace in Zoho Analytics. The queries pull from Zoho Inventory, Facebook Ads, Google Ads, and a manual spend table to produce weekly performance dashboards across four brands: **ENVO**, **Veemo**, **EbikeBC**, and **Moonbike** (plus Costco wholesale).

---

## Repository Structure

```
queries/
  01_google_facebook_spent.sql       — Raw weekly ad spend (FB + Google + Other), one row per ad set / campaign
  02_ad_spend_by_category.sql        — Ad spend summarised by week × product category
  03_sales_ad_spend_by_category.sql  — Sales invoices + ad spend joined by week × category (primary KPI query)
  04_total_sales_invoice_items.sql   — Sales invoices + ad spend joined by week × channel (brand-level variant)
```

---

## Query Dependency Graph

```
Facebook Ads tables  ──┐
Google Ads tables    ──┼──► 01_google_facebook_spent         ──► 02_ad_spend_by_category
Other Marketing Spend──┘         │                                        │
                                 │                                        │
                                 └────────────────────────────────────────┼──► 03_sales_ad_spend_by_category
                                                                          │
Year Week Channel Qry ────────────────────────────────────────────────────┤
Zoho Inventory tables ────────────────────────────────────────────────────┤
Deals Weekly Qry _ Brand ─────────────────────────────────────────────────┘

Google Facebook Spent Grouped Qry ──► 04_total_sales_invoice_items
  (channel-level rollup of query 01)
```

> **Queries 03 and 04 are the two main dashboard-facing queries.** Queries 01 and 02 are intermediate views they depend on.

---

## Query Details

### 01 — Google Facebook Spent Qry

**File:** `queries/01_google_facebook_spent.sql`

Produces one row per ad set (Facebook) or campaign (Google) per ISO week, with spend in both USD and CAD. The three source blocks are `UNION ALL`-ed together.

| Block | Source tables | Output columns populated |
|---|---|---|
| Facebook | `Ad Sets`, `Ad Set Insights` | `FB USD`, `FB CAD` |
| Google | `Campaigns`, `Campaign Performance` | `Google USD`, `Google CAD` |
| Other | `Other Marketing Spend` (manual) | `Other CAD` |

**Channel and Product Category** are parsed directly from the ad set / campaign **name** using string splitting:
- Everything before the first `-` → `Channel`
- The segment between the first and second `-` → `Product Category`

So a campaign named `ENVO - Ebike - Brand` would yield `Channel = ENVO` and `Product Category = Ebike`.

**Currency conversion:** All Facebook and Google costs are in USD. A fixed rate of **1.35** is applied to produce CAD values.

**Week key format:** `YYYY-WW` (e.g. `2024-03`), anchored to Monday using `start_date_current_week(..., 2)`.

---

### 02 — Ad Spend By Category Qry

**File:** `queries/02_ad_spend_by_category.sql`

A simple `GROUP BY` rollup of query 01. Collapses individual ad set rows into one row per `(Year Week, Product Category)`.

Output columns: `FB Spend CAD`, `Google Spend CAD`, `Total Spend CAD`, `FB Spend USD`, `Google Spend USD`.

---

### 03 — Sales & Ad Spend By Category Qry

**File:** `queries/03_sales_ad_spend_by_category.sql`

The **primary KPI query**. Joins the weekly calendar scaffold against closed invoices, then enriches each invoice line item with ad spend, payment data, and CRM pipeline metrics.

**Key joins:**

| Join | Purpose |
|---|---|
| `Year Week Channel Qry` | Provides the full calendar + brand matrix so weeks with zero sales still appear |
| Invoices + Sales Orders subquery | Resolves channel from SO# prefix; filters to `Status = 'Closed'` |
| `Invoice Items` | Explodes each invoice to one row per line item |
| `Items` / `Category` | Adds SKU and product category to each line |
| `Customers` | Adds account type / contact type for dealer exclusion |
| `Sales Persons` | Resolves sales person name |
| `Google Facebook Spent Qry` (grouped) | Joins spend on `(Year Week, Category Name)` |
| Invoice Payments subquery | Aggregates cash received per `(week, channel)`, excluding dealers |
| `Deals Weekly Qry _ Brand` | Adds pipeline, weighted pipeline, deal counts, won/lost from CRM |

**Channel derivation** — applied consistently in both the invoice subquery and the payments subquery:

| Sales Order # pattern | Channel |
|---|---|
| Starts with `0089400` | Costco |
| Starts with `SO-EB-` | EbikeBC |
| Starts with `SO-VM-` | Veemo |
| Starts with `SO-MB-` | Moonbike |
| Starts with `SO-` | ENVO |
| NULL or no `-` | No SO |

**Dealer exclusion:** Rows where `Account Type` is `Dealer - Bronze / Gold / Silver / Standard` are filtered out from both the main result set and the payments subquery. This ensures KPIs reflect retail/direct sales only.

**`Is First Row` flag:** Uses a window function `MIN(Item ID) OVER (PARTITION BY Year-Week, Category Name)` to mark the first item row per week × category. Dashboard charts use this flag to avoid double-counting header-level metrics (total spend, pipeline amounts, payment totals) when aggregating across multiple line items.

**Invoice Paid Status** is derived:
- `Balance = 0` → `Paid`
- `Balance != Total` → `Partial`
- Otherwise → `Not Paid`

---

### 04 — Total Sales Invoice Items Qry

**File:** `queries/04_total_sales_invoice_items.sql`

Structurally identical to query 03 with **two key differences**:

| | Query 03 | Query 04 |
|---|---|---|
| Ad spend join | `Google Facebook Spent Qry` grouped by **category** | `Google Facebook Spent Grouped Qry` grouped by **channel** |
| `Is First Row` partition | `(Year-Week, Category Name)` | `(Year-Week, Channel)` |

Use query 04 when you need brand-level totals (e.g. total ENVO spend per week regardless of category). Use query 03 when you need category-level breakdown (e.g. Ebike spend vs Scooter spend).

---

## Data Sources

| Zoho / Platform table | Description |
|---|---|
| `Invoices (Zoho Inventory)` | Invoice header: date, total, balance, status |
| `Invoice Items (Zoho Inventory)` | Line items: quantity, price, item reference |
| `Sales Orders (Zoho Inventory)` | SO header: SO#, type — used for channel derivation |
| `Sales Order Invoice (Zoho Inventory)` | Junction table linking SOs to Invoices |
| `Invoice Payments (Zoho Inventory)` | Cash receipts against invoices |
| `Customers (Zoho Inventory)` | Account type (dealer vs retail), contact type |
| `Items (Zoho Inventory)` | SKU, product master |
| `Category (Zoho Inventory)` | Product category lookup |
| `Sales Persons (Zoho Inventory)` | Sales rep name lookup |
| `Ad Sets (Facebook Ads)` | Facebook ad set metadata |
| `Ad Set Insights (Facebook Ads)` | Facebook daily/weekly spend |
| `Campaigns (Google Ads)` | Google campaign metadata |
| `Campaign Performance (Google Ads)` | Google daily/weekly cost |
| `Other Marketing Spend` | Manual CAD spend entries (trade shows, influencers, etc.) |
| `Year Week Channel Qry` | Calendar scaffold: one row per ISO week × channel |
| `Deals Weekly Qry _ Brand` | CRM deal pipeline aggregated by week and brand |
| `Google Facebook Spent Grouped Qry` | Channel-level rollup of query 01 (used by query 04) |

---

## Notes

- All week keys use ISO week numbering anchored to **Monday** via the Zoho Analytics function `start_date_current_week(date, 2)`.
- Queries are filtered to weeks `<= current week` to prevent future placeholder rows from appearing in dashboards.
- The `SO Channel Old` column preserves the original legacy `if()` chain for backwards compatibility; `Channel` (CASE-based) is the canonical value used for all joins.

---

## Voice KPI Reports

Agent performance reports built in the **Zoho Voice Analytics** workspace. See [`voice-kpi/`](voice-kpi/) for full documentation.

| Report | View ID | Description |
|--------|---------|-------------|
| [KPI Voice Call Pickup by Agent](voice-kpi/01_kpi_voice_call_pickup_by_agent.md) | `2350577000030633734` | Pickup rate per agent broken down by outcome (answered / agent miss / tech fail / customer cancel / lose race) |
| [KPI Voice Missed Call Callback Tracker](voice-kpi/02_kpi_voice_missed_call_callback_tracker.md) | `2350577000030645441` | Per missed call: which agent called back and how many minutes it took |

### Supporting Query Tables

| Table | View ID | Description |
|-------|---------|-------------|
| `KPI Voice Call Log` | `2350577000030636652` | Deduplicated incoming/missed calls per agent with 1/0 outcome flags |
| `KPI Voice Outgoing Each` | `2350577000030642916` | One row per outgoing call with customer number and agent name |
| `KPI Voice Missed Callback` | `2350577000030634199` | Cross-join of missed calls × outgoing calls for callback time calculation |
