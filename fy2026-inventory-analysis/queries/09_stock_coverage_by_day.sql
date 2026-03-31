-- View: Stock Coverage by Day
-- ID: 2350577000030856336
-- Purpose: Stock on hand per SKU joined with daily plan (one row per SKU per day)
--          Base table for flexible date-range coverage analysis
--          Filter Plan_Date in the report to any window (4W, 6W, 8W, custom)
-- Depends on: Stock On Hand per SKU, 2026 Daily Plan (imported CSV)

SELECT
  s."SKU"            AS "SKU",
  s."Item Name"      AS "Item_Name",
  s."Stock_On_Hand"  AS "Stock_On_Hand",
  s."In_Transit"     AS "In_Transit",
  s."External_Inv"   AS "External_Inv",
  d."Plan_Date"      AS "Plan_Date",
  d."Daily_Plan_Qty" AS "Daily_Plan_Qty"
FROM "Stock On Hand per SKU" s
JOIN "2026 Daily Plan" d ON s."SKU" = d."SKU"
