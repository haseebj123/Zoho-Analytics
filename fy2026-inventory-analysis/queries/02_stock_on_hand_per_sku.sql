-- View: Stock On Hand per SKU
-- ID: 2350577000030849308
-- Purpose: Current stock position per SKU from Inventory Count Value Warehouse Qry
--          Stock_On_Hand matches the Zoho Inventory pivot exactly

SELECT
  "SKU",
  "Item Name",
  SUM("Quantity Available") AS Stock_On_Hand,
  SUM("External Inv")       AS External_Inv,
  SUM("Transit Inv")        AS In_Transit
FROM "Inventory Count Value Warehouse Qry"
WHERE "SKU" IN (
  'END50R14A20C','END50R14M20C','END50R14M30C','END50R14M17C','END50R14A17C',
  'END50R14M40C','ENST50R14C20C','ENST50R14M20C','ENST50R14C17D','ENST50R14M17C',
  'ENST50R14C17C','ENST50R14C17E','FOENV35W12.8A-BLACK-23','FOENV35W12.8A-BLUE-23',
  'FOENV35W12.8A-RED-23','FLEXOL-BLKS','FLEXOL-ORS','FLTRK-BLKS','FLTRK-ORS'
)
GROUP BY "SKU", "Item Name"
