-- ============================================================
-- Query: Total Sales Invoice Items Qry
-- Purpose: Variant of the Sales & Ad Spend By Category query.
--          Key difference: ad spend is joined from
--          "Google Facebook Spent Grouped Qry" (spend grouped by Channel,
--          NOT by Product Category), so spend columns reflect total brand
--          spend rather than category-level spend.
--
--          "Is First Row" window partition is also broader here:
--          PARTITION BY (Year-Week, Channel) — flags first item per
--          channel per week (vs per category in query 03).
--
-- Depends on:
--   • Year Week Channel Qry
--   • Google Facebook Spent Grouped Qry  (channel-level spend rollup)
--   • Deals Weekly Qry _ Brand
-- ============================================================

SELECT
    YW."Year-Week"                                                              AS "Year Week",
    INVB."Invoice Week"                                                         AS "Invoice Week",
    COALESCE(INVB."Invoice Date Start", YW."Week Start Date")                  AS "Invoice Date Start",
    COALESCE(INVB."Invoice Date End",   YW."Week End Date")                    AS "Invoice Date End",
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
    PP.SKU                                                                      AS "Item SKU",
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
    -- Flag the first item row per (week, channel) — broader than query 03
    -- which partitions by (week, category)
    IF(II."Item ID" = MIN(II."Item ID") OVER (PARTITION BY YW."Year-Week",
                                                            YW."Channel"), 1, 0) AS "Is First Row"

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
        -- Legacy channel field
        if(INSTR(SO."Sales Order#", '-') = 0,
           if(is_startswith(SO."Sales Order#", '0089400'), 'Costco', ''),
           if(is_startswith(SO."Sales Order#", 'SO-EB-'), 'EbikeBC',
           if(is_startswith(SO."Sales Order#", 'SO-VM-'), 'Veemo',
           if(is_startswith(SO."Sales Order#", 'SO-MB-'), 'Moonbike',
           if(is_startswith(SO."Sales Order#", 'SO-'), 'ENVO', ''))))) AS "SO Channel Old",
        -- Canonical channel
        CASE
            WHEN SO."Sales Order#" IS NULL                             THEN 'No SO'
            WHEN INSTR(SO."Sales Order#", '-') = 0
             AND INSTR(SO."Sales Order#", '0089400') = 1               THEN 'Costco'  -- removed redundant nested if
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
LEFT OUTER JOIN "Customers (Zoho Inventory)"      CC  ON CC."Customer ID"     = INVB."Customer ID"
/* ── Invoice line items ── */
LEFT OUTER JOIN "Invoice Items (Zoho Inventory)"  II  ON II."Invoice ID"      = INVB."Invoice ID"
/* ── Item master (SKU) ── */
LEFT OUTER JOIN "Items (Zoho Inventory)"          PP  ON PP."Item ID"         = II."Product ID"
/* ── Product category ── */
LEFT OUTER JOIN "Category (Zoho Inventory)"       CAT ON CAT."Category ID"    = PP."Category ID"
/* ── Sales person ── */
LEFT OUTER JOIN "Sales Persons (Zoho Inventory)"  SP  ON SP."Sales Person ID" = INVB."Sales Person ID"

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

/* ── Channel-level ad spend (NOT category-level — key difference from query 03) ── */
LEFT OUTER JOIN "Google Facebook Spent Grouped Qry" MS ON MS."Year Week" = YW."Year-Week"
                                                      AND MS."Channel"   = YW."Channel"

/* ── CRM deal pipeline metrics per week / brand ── */
LEFT OUTER JOIN "Deals Weekly Qry _ Brand" DW ON DW."Year Week" = YW."Year-Week"
                                              AND DW."Channel"   = YW."Channel"

WHERE YW."Year-Week" <= CONCAT(YEAR(start_date_current_week(CURRENT_DATE(), 2)), '-',
                               LPAD(WEEK(start_date_current_week(CURRENT_DATE(), 2)), 2, '0'))
  AND (CC."Account Type" NOT IN ('Dealer - Bronze', 'Dealer - Gold',
                                  'Dealer - Silver', 'Dealer - Standard')
       OR CC."Account Type" IS NULL)

ORDER BY YW."Year-Week" DESC;
