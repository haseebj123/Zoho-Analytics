-- View: YTD Plan per SKU
-- ID: 2350577000030860433
-- Purpose: FY2026 planned quantity per SKU from Nov 2025 to today
--          Uses daily plan table for precise partial-month proration
--          Fully dynamic — updates daily via CURDATE()
-- Depends on: 2026 Daily Plan (imported CSV)

SELECT
  "SKU",
  SUM("Daily_Plan_Qty") AS "YTD_Plan_Qty"
FROM "2026 Daily Plan"
WHERE "Plan_Date" >= '2025-11-01'
  AND "Plan_Date" <= CURDATE()
GROUP BY "SKU"
