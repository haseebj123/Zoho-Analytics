-- View: Stock Coverage - Multi Window
-- ID: 2350577000030851706
-- Purpose: Pre-built 4-week, 6-week, and 8-week plan demand columns vs current stock
--          All windows dynamic — roll forward daily via CURDATE()
-- Depends on: Stock On Hand per SKU, 2026 Daily Plan (imported CSV)

SELECT
  s."SKU"       AS "SKU",
  s."Item Name" AS "Item_Name",
  s."Stock_On_Hand"  AS "Stock_On_Hand",
  s."In_Transit"     AS "In_Transit",
  s."External_Inv"   AS "External_Inv",
  SUM(CASE WHEN d."Plan_Date" >= CURDATE()
            AND d."Plan_Date" <= DATE_ADD(CURDATE(), INTERVAL 27 DAY)
            THEN d."Daily_Plan_Qty" ELSE 0 END) AS "Plan_4W",
  SUM(CASE WHEN d."Plan_Date" >= CURDATE()
            AND d."Plan_Date" <= DATE_ADD(CURDATE(), INTERVAL 41 DAY)
            THEN d."Daily_Plan_Qty" ELSE 0 END) AS "Plan_6W",
  SUM(CASE WHEN d."Plan_Date" >= CURDATE()
            AND d."Plan_Date" <= DATE_ADD(CURDATE(), INTERVAL 55 DAY)
            THEN d."Daily_Plan_Qty" ELSE 0 END) AS "Plan_8W"
FROM "Stock On Hand per SKU" s
JOIN "2026 Daily Plan" d ON s."SKU" = d."SKU"
WHERE d."Plan_Date" >= CURDATE()
  AND d."Plan_Date" <= DATE_ADD(CURDATE(), INTERVAL 55 DAY)
GROUP BY s."SKU", s."Item Name", s."Stock_On_Hand", s."In_Transit", s."External_Inv"
