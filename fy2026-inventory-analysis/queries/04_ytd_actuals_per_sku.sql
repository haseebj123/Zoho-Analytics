-- View: YTD Actuals per SKU
-- ID: 2350577000030860355
-- Purpose: Actual sales quantity per SKU from Nov 2025 to today (FY2026 YTD)
--          Fully dynamic — updates daily via CURDATE()
-- Depends on: 2026 Sales Orders with SKU

SELECT
  "i.SKU"                AS "SKU",
  SUM("soi.Quantity")    AS "YTD_Actual_Qty"
FROM "2026 Sales Orders with SKU"
WHERE "Order_Date" >= '2025-11-01'
  AND "Order_Date" <= CURDATE()
GROUP BY "i.SKU"
