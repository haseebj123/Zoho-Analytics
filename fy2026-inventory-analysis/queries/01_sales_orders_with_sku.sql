-- View: 2026 Sales Orders with SKU
-- ID: 2350577000030862193
-- Purpose: Sales order lines for the 19 tracked SKUs (Nov 2025 onwards),
--          excluding void/draft orders, with SO status

SELECT
  so."Sales Order#"   AS "SO_Number",
  so."Status"         AS "SO_Status",
  i."SKU",
  i."Item Name"       AS "Item_Name",
  soi."Quantity",
  so."Order Date"     AS "Order_Date"
FROM "Sales Order Items (Zoho Inventory)" soi
JOIN "Sales Orders (Zoho Inventory)"   so ON soi."Sales order ID" = so."Sales order ID"
JOIN "Items (Zoho Inventory)"           i  ON soi."Item Name"     = i."Item Name"
WHERE i."SKU" IN (
  'END50R14A20C','END50R14M20C','END50R14M30C','END50R14M17C','END50R14A17C',
  'END50R14M40C','ENST50R14C20C','ENST50R14M20C','ENST50R14C17D','ENST50R14M17C',
  'ENST50R14C17C','ENST50R14C17E','FOENV35W12.8A-BLACK-23','FOENV35W12.8A-BLUE-23',
  'FOENV35W12.8A-RED-23','FLEXOL-BLKS','FLEXOL-ORS','FLTRK-BLKS','FLTRK-ORS'
)
AND so."Status" NOT IN ('void','draft','pending_approval','approved')
AND YEAR(so."Order Date") >= 2025
