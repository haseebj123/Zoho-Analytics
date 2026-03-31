-- View: 2026 Sales vs Plan - Pivot Ready
-- ID: 2350577000030856207
-- Purpose: Plan-anchored view — all 19 SKUs x 12 months (Nov 2025–Oct 2026)
--          with actual sales summed per month. Zero shown for months with no sales.
-- Depends on: 2026 Plan - SKU Monthly, 2026 Sales Orders with SKU

SELECT
  p."SKU",
  p."Plan Month"   AS "Month",
  p."Planned Qty"  AS "Plan_Qty",
  COALESCE(SUM(s."soi.Quantity"), 0) AS "Actual_Qty"
FROM "2026 Plan - SKU Monthly" p
LEFT JOIN "2026 Sales Orders with SKU" s
  ON  s."i.SKU" = p."SKU"
  AND YEAR(s."Order_Date")  = YEAR(p."Plan Month")
  AND MONTH(s."Order_Date") = MONTH(p."Plan Month")
GROUP BY p."SKU", p."Plan Month", p."Planned Qty"
