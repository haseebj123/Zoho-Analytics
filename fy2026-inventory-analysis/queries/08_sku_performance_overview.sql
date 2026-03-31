-- View: SKU Performance Overview 2026
-- ID: 2350577000030846392
-- Purpose: Master per-SKU view combining inventory position with FY2026 YTD performance
--          All columns fully dynamic — updates daily
-- Depends on: Inventory Coverage 2026, YTD Actuals per SKU, YTD Plan per SKU

SELECT
  c."SKU"            AS "SKU",
  c."Item_Name"      AS "Item_Name",
  c."Stock_On_Hand"  AS "Stock_On_Hand",
  c."In_Transit"     AS "In_Transit",
  c."External_Inv"   AS "External_Inv",
  c."Next_2M_Plan"   AS "Next_2M_Plan",
  COALESCE(a."YTD_Actual_Qty", 0) AS "YTD_Actual_Qty",
  COALESCE(p."YTD_Plan_Qty",   0) AS "YTD_Plan_Qty"
FROM "Inventory Coverage 2026" c
LEFT JOIN "YTD Actuals per SKU" a ON c."SKU" = a."SKU"
LEFT JOIN "YTD Plan per SKU"    p ON c."SKU" = p."SKU"
