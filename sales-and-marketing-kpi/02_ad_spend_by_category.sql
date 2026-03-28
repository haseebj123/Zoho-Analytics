-- ============================================================
-- Query: Ad Spend By Category Qry
-- Purpose: Summarises weekly ad spend per product category by
--          aggregating the output of Google Facebook Spent Qry.
--          Produces separate FB and Google totals in both CAD and USD,
--          plus a combined Total Spend CAD column.
-- Depends on: Google Facebook Spent Qry (01_google_facebook_spent.sql)
-- ============================================================

SELECT
    "Year Week"                                    AS "Year Week",
    "Product Category"                             AS "Item Category",
    SUM("FB CAD")                                  AS "FB Spend CAD",
    SUM("Google CAD")                              AS "Google Spend CAD",
    SUM("FB CAD") + SUM("Google CAD")              AS "Total Spend CAD",
    SUM("FB USD")                                  AS "FB Spend USD",
    SUM("Google USD")                              AS "Google Spend USD"
FROM  "Google Facebook Spent Qry"
GROUP BY "Year Week",
         "Product Category";
