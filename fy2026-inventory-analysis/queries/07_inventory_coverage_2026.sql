-- View: Inventory Coverage 2026
-- ID: 2350577000030853258
-- Purpose: Stock on hand + in-transit vs next 2 months planned demand per SKU
--          All values dynamic — stock syncs from Zoho Inventory, plan window rolls forward
-- Depends on: Stock On Hand per SKU, Next 2M Plan per SKU

SELECT
  s."SKU"            AS "SKU",
  s."Item Name"      AS "Item_Name",
  s."Stock_On_Hand"  AS "Stock_On_Hand",
  s."In_Transit"     AS "In_Transit",
  s."External_Inv"   AS "External_Inv",
  p."Next_2M_Plan"   AS "Next_2M_Plan"
FROM "Stock On Hand per SKU" s
LEFT JOIN "Next 2M Plan per SKU" p ON s."SKU" = p."SKU"

-- NOTE: Add formula columns in Zoho Analytics UI:
--   Total_Available  = Stock_On_Hand + In_Transit
--   Coverage_Status  = IF(Total_Available >= Next_2M_Plan, "Sufficient", "Shortfall")
