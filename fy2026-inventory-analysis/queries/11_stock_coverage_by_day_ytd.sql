-- View: Stock Coverage by Day + YTD
-- ID: 2350577000030851908
-- Purpose: Stock coverage by day joined with YTD actuals and YTD plan
--          Base table for the Custom Range Pivot report
-- Depends on: Stock Coverage by Day, YTD Actuals per SKU, YTD Plan per SKU

SELECT
  d."SKU"            AS "SKU",
  d."Item_Name"      AS "Item_Name",
  d."Stock_On_Hand"  AS "Stock_On_Hand",
  d."In_Transit"     AS "In_Transit",
  d."External_Inv"   AS "External_Inv",
  d."Plan_Date"      AS "Plan_Date",
  d."Daily_Plan_Qty" AS "Daily_Plan_Qty",
  a."YTD_Actual_Qty" AS "YTD_Actual_Qty",
  p."YTD_Plan_Qty"   AS "YTD_Plan_Qty"
FROM "Stock Coverage by Day" d
LEFT JOIN "YTD Actuals per SKU" a ON d."SKU" = a."SKU"
LEFT JOIN "YTD Plan per SKU"    p ON d."SKU" = p."SKU"
