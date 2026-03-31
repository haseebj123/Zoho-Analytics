-- View: Next 2M Plan per SKU
-- ID: 2350577000030862357
-- Purpose: Planned quantity for the next 2 calendar months from today
--          Fully dynamic — rolls forward automatically each month via CURDATE()
-- Depends on: 2026 Plan - SKU Monthly

SELECT
  "SKU",
  SUM("Planned Qty") AS "Next_2M_Plan"
FROM "2026 Plan - SKU Monthly"
WHERE
  (YEAR("Plan Month")  = YEAR(DATE_ADD(CURDATE(), INTERVAL 1 MONTH))
   AND MONTH("Plan Month") = MONTH(DATE_ADD(CURDATE(), INTERVAL 1 MONTH)))
  OR
  (YEAR("Plan Month")  = YEAR(DATE_ADD(CURDATE(), INTERVAL 2 MONTH))
   AND MONTH("Plan Month") = MONTH(DATE_ADD(CURDATE(), INTERVAL 2 MONTH)))
GROUP BY "SKU"
