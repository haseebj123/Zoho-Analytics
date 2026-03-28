-- ============================================================
-- Query: Google Facebook Spent Qry
-- Purpose: Aggregates weekly ad spend from Facebook Ads, Google Ads,
--          and Other Marketing Spend into a unified dataset.
--          Spend is grouped by Year-Week, Channel, and Product Category.
--          Facebook amounts are converted from USD to CAD (x1.35).
--          Google amounts are converted from USD to CAD (x1.35).
--          "Other" spend is already in CAD from the manual input table.
-- ============================================================

SELECT *
FROM (

    /* ---------- Facebook Ads ---------- */
    SELECT
        CONCAT(YEAR(start_date_current_week(ASI."Reporting Starts", 2)), '-',
               LPAD(WEEK(start_date_current_week(ASI."Reporting Starts", 2)), 2, '0'))  AS "Year Week",
        AD."Name"                                                                         AS "Name",
        TRIM(SUBSTRING(AD."Name", 1, INSTR(AD."Name", '-') - 1))                         AS "Channel",
        TRIM(SUBSTRING(AD."Name",
             INSTR(AD."Name", '-') + 1,
             INSTR(SUBSTRING(AD."Name", INSTR(AD."Name", '-') + 1), '-') - 1))           AS "Product Category",
        ROUND(SUM(ASI."Amount Spent"), 2)                                                 AS "FB USD",
        ROUND(SUM(ASI."Amount Spent" * 1.35), 2)                                          AS "FB CAD",
        0                                                                                 AS "Google USD",
        0                                                                                 AS "Google CAD",
        0                                                                                 AS "Other CAD"
    FROM  "Ad Sets (Facebook Ads)"            AD
    LEFT OUTER JOIN "Ad Set Insights (Facebook Ads)" ASI ON ASI."Adset Id" = AD."Id"
    WHERE ASI."Amount Spent" > 0
    GROUP BY 1, 2, 3, 4

    UNION ALL

    /* ---------- Google Ads ---------- */
    SELECT
        CONCAT(YEAR(start_date_current_week(CP."Day", 2)), '-',
               LPAD(WEEK(start_date_current_week(CP."Day", 2)), 2, '0'))                 AS "Year Week",
        AD."Campaign"                                                                     AS "Name",
        TRIM(SUBSTRING(AD."Campaign", 1, INSTR(AD."Campaign", '-') - 1))                 AS "Channel",
        TRIM(SUBSTRING(AD."Campaign",
             INSTR(AD."Campaign", '-') + 1,
             INSTR(SUBSTRING(AD."Campaign", INSTR(AD."Campaign", '-') + 1), '-') - 1))   AS "Product Category",
        0                                                                                 AS "FB USD",
        0                                                                                 AS "FB CAD",
        ROUND(SUM(CP."Costs"), 2)                                                         AS "Google USD",
        ROUND(SUM(CP."Costs" * 1.35), 2)                                                  AS "Google CAD",
        0                                                                                 AS "Other CAD"
    FROM  "Campaigns (Google Ads)"             AD
    LEFT OUTER JOIN "Campaign Performance (Google Ads)" CP ON CP."Campaign ID" = AD."Campaign ID"
    WHERE CP."Costs" > 0
    GROUP BY 1, 2, 3, 4

    UNION ALL

    /* ---------- Other Marketing Spend (manual CAD input) ---------- */
    SELECT
        OMS."Year-Week"          AS "Year Week",
        OMS."Channel"            AS "Name",
        OMS."Channel"            AS "Channel",
        OMS."Product Category"   AS "Product Category",
        0                        AS "FB USD",
        0                        AS "FB CAD",
        0                        AS "Google USD",
        0                        AS "Google CAD",
        ROUND(OMS."Spending (CAD)", 2) AS "Other CAD"
    FROM  "Other Marketing Spend" OMS
    WHERE OMS."Spending (CAD)" > 0

) t
ORDER BY t."Year Week" DESC,
         t."Channel";
