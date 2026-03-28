-- ============================================================
-- Query: Sales & Ad Spend By Category Qry
-- Purpose: The primary KPI query joining:
--   • Year-Week / Channel calendar scaffold (Year Week Channel Qry)
--   • Closed Invoices + Sales Orders (channel derived from SO prefix)
--   • Invoice line items, SKUs and product categories
--   • FB + Google + Other ad spend per category (Google Facebook Spent Qry)
--   • Invoice payment totals (excluding dealers)
--   • CRM pipeline / deal metrics per week & brand (Deals Weekly Qry _ Brand)
--
-- Channel derivation logic (Sales Order # prefix):
--   0089400...  → Costco
--   SO-EB-      → EbikeBC
--   SO-VM-      → Veemo
--   SO-MB-      → Moonbike
--   SO-         → ENVO
--   (none)      → No SO
--
-- Dealer account types are excluded from both invoice and payment rows.
-- "Is First Row" flag = 1 for the first item per (Year-Week, Category)
-- — used in reports to avoid double-counting header-level metrics.
-- ============================================================

SELECT
    YW."Year-Week"                                                              AS "Year Week",
    INVB."Invoice Week"                                                         AS "Invoice Week",
    COALESCE(INVB."Invoice Date Start",
             DATE_FORMAT(YW."Week Start Date", '%Y/%m/%d'))                     AS "Invoice Date Start",
    COALESCE(INVB."Invoice Date End",
             DATE_FORMAT(YW."Week End Date", '%Y/%m/%d'))                       AS "Invoice Date End",
    II."Item Name"                                                              AS "Item Name",
    II."Quantity"                                                               AS "Item Quantity",
    II."Total (BCY)"                                                            AS "Item Total",
    CAT."Category Name"                                                         AS "Item Category",
    INVB."Sales Order#"                                                         AS "Sales Order Number",
    YW."Channel"                                                                AS "Channel",
    INVB."SO Channel Old"                                                       AS "SO Channel Old",
    MS."FB CAD"                                                                 AS "FB Spend",
    MS."Google CAD"                                                             AS "Google Spend",
    MS."Other CAD"                                                              AS "Other Spend",
    MS."FB CAD" + MS."Google CAD" + MS."Other CAD"                              AS "Total Spend",
    INVB."Invoice Date"                                                         AS "Invoice Date",
    IP."Paid Total"                                                             AS "Total Paid",
    INVB."Sales Order Type"                                                     AS "Sales Order Type",
    PP."SKU"                                                                    AS "Item SKU",
    INVB."Source(Sales Channel)"                                                AS "INV.Source(Sales Channel)",
    INVB."Source New"                                                           AS "Invoice Channel",
    SP."Name"                                                                   AS "Sales Person",
    IF(INVB."Balance (BCY)" = 0, 'Paid',
       IF(INVB."Total (BCY)" != INVB."Balance (BCY)", 'Partial', 'Not Paid'))  AS "Invoice Paid Status",
    INVB."Status"                                                               AS "Invoice Status",
    DW."Pipeline"                                                               AS "Pipeline Amount",
    DW."Weighted Pipeline"                                                      AS "Weighted Pipeline Amount",
    DW."Deal Count"                                                             AS "Deal Count",
    DW."Qualification Cnt"                                                      AS "Qualification Cnt",
    DW."Closed Won Cnt"                                                         AS "Won Cnt",
    DW."Closed Lost Cnt"                                                        AS "Lost Cnt",
    CC."Contact Type"                                                           AS "Customer Contact Type",
    CC."Account Type"                                                           AS "Customer Account Type",
    INVB."Invoice Number"                                                       AS "Invoice Number",
    II."Warehouse ID"                                                           AS "Item Warehouse Id",
    INVB."Sales order ID"                                                       AS "SO Id",
    INVB."Invoice ID"                                                           AS "Invoice Id",
    INVB."Shipping Status Description"                                          AS "Invoice Shipping Status",
    -- Flag the first item row per (week, category) to avoid double-counting
    -- header-level metrics (spend, pipeline, payments) in aggregations
    IF(II."Item ID" = MIN(II."Item ID") OVER (PARTITION BY YW."Year-Week",
                                                            CAT."Category Name"), 1, 0) AS "Is First Row"

FROM "Year Week Channel Qry" YW

/* ── Closed Invoices + Sales Order channel derivation ── */
LEFT JOIN (
    SELECT
        INV."Invoice ID",
        INV."Customer ID",
        INV."Invoice Date",
        INV."Total (BCY)",
        INV."Balance (BCY)",
        INV."Invoice Number",
        INV."Source(Sales Channel)",
        INV."Source New",
        INV."Sales Person ID",
        INV."Status",
        INV."Shipping Status Description",
        CONCAT(YEAR(start_date_current_week(INV."Invoice Date", 2)), '-',
               LPAD(WEEK(start_date_current_week(INV."Invoice Date", 2)), 2, '0'))          AS "Invoice Week",
        DATE_FORMAT(start_date_current_week(INV."Invoice Date", 2), '%Y/%m/%d')             AS "Invoice Date Start",
        DATE_FORMAT(add_date(start_date_current_week(INV."Invoice Date", 2), 6), '%Y/%m/%d') AS "Invoice Date End",
        SO."Sales order ID",
        SO."Sales Order#",
        SO."Sales Order Type",
        -- Legacy channel field (if/else chain)
        if(INSTR(SO."Sales Order#", '-') = 0,
           if(is_startswith(SO."Sales Order#", '0089400'), 'Costco', ''),
           if(is_startswith(SO."Sales Order#", 'SO-EB-'), 'EbikeBC',
           if(is_startswith(SO."Sales Order#", 'SO-VM-'), 'Veemo',
           if(is_startswith(SO."Sales Order#", 'SO-MB-'), 'Moonbike',
           if(is_startswith(SO."Sales Order#", 'SO-'), 'ENVO', ''))))) AS "SO Channel Old",
        -- Canonical channel (CASE statement)
        CASE
            WHEN SO."Sales Order#" IS NULL                             THEN 'No SO'
            WHEN INSTR(SO."Sales Order#", '-') = 0
             AND INSTR(SO."Sales Order#", '0089400') = 1               THEN 'Costco'
            WHEN INSTR(SO."Sales Order#", '-') = 0                     THEN 'No SO'
            WHEN INSTR(SO."Sales Order#", 'SO-EB-') = 1                THEN 'EbikeBC'
            WHEN INSTR(SO."Sales Order#", 'SO-VM-') = 1                THEN 'Veemo'
            WHEN INSTR(SO."Sales Order#", 'SO-MB-') = 1                THEN 'Moonbike'
            WHEN INSTR(SO."Sales Order#", 'SO-') = 1                   THEN 'ENVO'
            ELSE 'No SO'
        END AS "Channel"
    FROM "Invoices (Zoho Inventory)" INV
    LEFT OUTER JOIN "Sales Order Invoice (Zoho Inventory)" SOI ON SOI."Invoice ID"    = INV."Invoice ID"
    LEFT OUTER JOIN "Sales Orders (Zoho Inventory)"        SO  ON SO."Sales order ID" = SOI."Sales order ID"
    WHERE INV."Status" = 'Closed'
) INVB ON INVB."Invoice Week" = YW."Year-Week"
      AND INVB."Channel"      = YW."Channel"

/* ── Customer details ── */
LEFT OUTER JOIN "Customers (Zoho Inventory)"      CC  ON CC."Customer ID"   = INVB."Customer ID"
/* ── Invoice line items ── */
LEFT OUTER JOIN "Invoice Items (Zoho Inventory)"  II  ON II."Invoice ID"    = INVB."Invoice ID"
/* ── Item master (SKU) ── */
LEFT OUTER JOIN "Items (Zoho Inventory)"          PP  ON PP."Item ID"       = II."Product ID"
/* ── Product category ── */
LEFT OUTER JOIN "Category (Zoho Inventory)"       CAT ON CAT."Category ID"  = PP."Category ID"
/* ── Sales person ── */
LEFT OUTER JOIN "Sales Persons (Zoho Inventory)"  SP  ON SP."Sales Person ID" = INVB."Sales Person ID"

/* ── Ad spend per week / category ── */
LEFT OUTER JOIN (
    SELECT
        "Year Week"        AS "Year Week",
        "Product Category" AS "Item Category",
        SUM("FB CAD")      AS "FB CAD",
        SUM("Google CAD")  AS "Google CAD",
        SUM("Other CAD")   AS "Other CAD"
    FROM "Google Facebook Spent Qry"
    GROUP BY "Year Week", "Product Category"
) MS ON MS."Year Week"    = YW."Year-Week"
     AND MS."Item Category" = CAT."Category Name"

/* ── Invoice payments (retail only — dealers excluded) ── */
LEFT OUTER JOIN (
    SELECT
        CONCAT(YEAR(start_date_current_week(PAY."Created Time", 2)), '-',
               LPAD(WEEK(start_date_current_week(PAY."Created Time", 2)), 2, '0')) AS "Payment Week",
        CASE
            WHEN SO."Sales Order#" IS NULL                             THEN 'No SO'
            WHEN INSTR(SO."Sales Order#", '-') = 0
             AND INSTR(SO."Sales Order#", '0089400') = 1               THEN 'Costco'
            WHEN INSTR(SO."Sales Order#", '-') = 0                     THEN 'No SO'
            WHEN INSTR(SO."Sales Order#", 'SO-EB-') = 1                THEN 'EbikeBC'
            WHEN INSTR(SO."Sales Order#", 'SO-VM-') = 1                THEN 'Veemo'
            WHEN INSTR(SO."Sales Order#", 'SO-MB-') = 1                THEN 'Moonbike'
            WHEN INSTR(SO."Sales Order#", 'SO-') = 1                   THEN 'ENVO'
            ELSE 'No SO'
        END AS "Channel",
        SUM(PAY."Amount (BCY)") AS "Paid Total"
    FROM "Invoice Payments (Zoho Inventory)"  PAY
    LEFT JOIN "Invoices (Zoho Inventory)"              INV   ON INV."Invoice ID"    = PAY."Invoice ID"
    LEFT JOIN "Sales Order Invoice (Zoho Inventory)"   SOI   ON SOI."Invoice ID"    = INV."Invoice ID"
    LEFT JOIN "Sales Orders (Zoho Inventory)"          SO    ON SO."Sales order ID" = SOI."Sales order ID"
    LEFT JOIN "Customers (Zoho Inventory)"             PAYCC ON PAYCC."Customer ID" = INV."Customer ID"
    WHERE (PAYCC."Account Type" NOT IN ('Dealer - Bronze', 'Dealer - Gold',
                                        'Dealer - Silver', 'Dealer - Standard')
           OR PAYCC."Account Type" IS NULL)
    GROUP BY 1, 2
) IP ON IP."Payment Week" = YW."Year-Week"
     AND IP."Channel"      = YW."Channel"

/* ── CRM deal pipeline metrics per week / brand ── */
LEFT OUTER JOIN "Deals Weekly Qry _ Brand" DW ON DW."Year Week" = YW."Year-Week"
                                              AND DW."Channel"   = YW."Channel"

WHERE YW."Year-Week" <= CONCAT(YEAR(start_date_current_week(CURRENT_DATE(), 2)), '-',
                               LPAD(WEEK(start_date_current_week(CURRENT_DATE(), 2)), 2, '0'))
  AND (CC."Account Type" NOT IN ('Dealer - Bronze', 'Dealer - Gold',
                                  'Dealer - Silver', 'Dealer - Standard')
       OR CC."Account Type" IS NULL)

ORDER BY YW."Year-Week" DESC;
