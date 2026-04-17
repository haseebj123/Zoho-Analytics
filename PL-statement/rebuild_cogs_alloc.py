"""Rebuild COGS allocation using actual PO purchase prices instead of revenue split."""
import json, urllib.request, urllib.parse, time

# Auth
data = urllib.parse.urlencode({
    'grant_type': 'refresh_token',
    'client_id': '1000.LQPSANXX3UYZ2T9IAZQEZ0YIZGNIEW',
    'client_secret': '175c6141a81c8ef20abf52c57772ef9c0b6af13b7a',
    'refresh_token': '1000.1975e5d0a4ad36c8314dee91361192ae.07278eb068b68a826dbf52f4360ac45c'
}).encode()
req = urllib.request.Request('https://accounts.zoho.com/oauth/v2/token', data=data, method='POST')
with urllib.request.urlopen(req) as resp:
    TOKEN = json.loads(resp.read())['access_token']
print(f"Token: {TOKEN[:20]}...")

ORG = '712029089'
WS = '2350577000000005001'
FOLDER_ID = '2350577000032146061'

def create_qt(name, sql):
    config = json.dumps({'queryTableName': name, 'sqlQuery': sql, 'folderId': FOLDER_ID})
    data = urllib.parse.urlencode({'CONFIG': config}).encode()
    req = urllib.request.Request(
        f'https://analyticsapi.zoho.com/restapi/v2/workspaces/{WS}/querytables',
        data=data, headers={
            'ZANALYTICS-ORGID': ORG,
            'Authorization': f'Zoho-oauthtoken {TOKEN}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            r = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        r = json.loads(e.read().decode())
    vid = r.get('data', {}).get('viewId', 'FAILED')
    print(f"  {name}: {vid}")
    if vid == 'FAILED':
        print(f"    Error: {r}")
    return vid

def create_report(title, base, config_extra):
    config = {
        'baseTableName': base, 'title': title,
        'reportType': 'pivot', 'folderId': FOLDER_ID,
        'axisColumns': [
            {'type': 'row', 'columnName': 'PL Section', 'operation': 'actual'},
            {'type': 'row', 'columnName': 'a.Account Name', 'operation': 'actual'},
            {'type': 'column', 'columnName': 'Channel', 'operation': 'actual'},
            {'type': 'data', 'columnName': 'Amount', 'operation': 'sum'},
        ],
        'userFilters': [{'tableName': base, 'columnName': 't.Transaction Date', 'operation': 'range'}],
    }
    data = urllib.parse.urlencode({'CONFIG': json.dumps(config)}).encode()
    req = urllib.request.Request(
        f'https://analyticsapi.zoho.com/restapi/v2/workspaces/{WS}/reports',
        data=data, headers={
            'ZANALYTICS-ORGID': ORG,
            'Authorization': f'Zoho-oauthtoken {TOKEN}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            r = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        r = json.loads(e.read().decode())
    vid = r.get('data', {}).get('viewId', 'FAILED')
    print(f"  {title}: {vid}")
    if vid == 'FAILED':
        print(f"    Error: {r}")
    return vid

# ============================================================
# Step 1: Item Avg PO Cost Qry
# Weighted average PO purchase price per product (in CAD)
# ============================================================
sql1 = (
    'SELECT "Product ID", '
    'SUM("Item Price (BCY)" * "Quantity") / SUM("Quantity") AS "Avg Cost" '
    'FROM "Purchase Order Items (Zoho Inventory)" '
    'GROUP BY "Product ID"'
)
print("Creating Item Avg PO Cost Qry...")
v1 = create_qt("Item Avg PO Cost Qry", sql1)
time.sleep(2)

# ============================================================
# Step 2: Channel PO Cost Qry
# Total purchase cost per channel based on invoice items x avg PO cost
# Uses Channel Profitability Inputs for salesperson mapping
# ============================================================
sql2 = (
    'SELECT CASE WHEN sp."Channel" IS NOT NULL THEN sp."Channel" '
    "ELSE 'Retail' END AS \"Channel\","
    'SUM(ii."Quantity" * pavg."Avg Cost") AS "Total Cost" '
    'FROM "Invoice Items (Zoho Inventory)" ii '
    'JOIN "Invoices (Zoho Inventory)" inv ON ii."Invoice ID"=inv."Invoice ID" '
    'JOIN "Item Avg PO Cost Qry" pavg ON ii."Product ID"=pavg."Product ID" '
    'LEFT JOIN "Channel Profitability Inputs" sp '
    "ON sp.\"Type\"='salesperson' AND sp.\"Key\"=inv.\"Sales Person ID\" "
    'GROUP BY CASE WHEN sp."Channel" IS NOT NULL THEN sp."Channel" '
    "ELSE 'Retail' END"
)
print("Creating Channel PO Cost Qry...")
v2 = create_qt("Channel PO Cost Qry", sql2)
time.sleep(2)

# ============================================================
# Step 3: Channel COGS Alloc Qry
# Uses PO cost proportions instead of revenue proportions
# ============================================================
sql3 = (
    'SELECT "PL Section","a.Account Name","t.Transaction Date",'
    '"Amount"*(SELECT SUM(c."Total Cost") FROM "Channel PO Cost Qry" c WHERE c."Channel"=\'B2B\')'
    '/(SELECT SUM(c."Total Cost") FROM "Channel PO Cost Qry" c WHERE c."Channel" IN (\'B2B\',\'Retail\',\'Costco\'))'
    ' AS "Amount",\'B2B\' AS "Channel" FROM "Channel Revenue Qry" WHERE "Channel"=\'ProRataAlloc\''
    ' UNION ALL '
    'SELECT "PL Section","a.Account Name","t.Transaction Date",'
    '"Amount"*(SELECT SUM(c."Total Cost") FROM "Channel PO Cost Qry" c WHERE c."Channel"=\'Retail\')'
    '/(SELECT SUM(c."Total Cost") FROM "Channel PO Cost Qry" c WHERE c."Channel" IN (\'B2B\',\'Retail\',\'Costco\'))'
    ' AS "Amount",\'Retail\' AS "Channel" FROM "Channel Revenue Qry" WHERE "Channel"=\'ProRataAlloc\''
    ' UNION ALL '
    'SELECT "PL Section","a.Account Name","t.Transaction Date",'
    '"Amount"*(SELECT SUM(c."Total Cost") FROM "Channel PO Cost Qry" c WHERE c."Channel"=\'Costco\')'
    '/(SELECT SUM(c."Total Cost") FROM "Channel PO Cost Qry" c WHERE c."Channel" IN (\'B2B\',\'Retail\',\'Costco\'))'
    ' AS "Amount",\'Costco\' AS "Channel" FROM "Channel Revenue Qry" WHERE "Channel"=\'ProRataAlloc\''
)
print("Creating Channel COGS Alloc Qry...")
v3 = create_qt("Channel COGS Alloc Qry", sql3)
time.sleep(2)

# ============================================================
# Step 4: Channel PL Qry (with Net P/L)
# ============================================================
_PL = (
    'SELECT * FROM "Channel Revenue Qry" WHERE "Channel"<>\'ProRataAlloc\' '
    'UNION ALL SELECT * FROM "Channel Opex Payroll Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Alloc Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Unalloc Qry" '
    'UNION ALL SELECT * FROM "Channel Other Exp Qry" '
    'UNION ALL SELECT * FROM "Channel COGS Alloc Qry"'
)
sql4 = (
    f'{_PL} UNION ALL SELECT \'6. Net Profit/Loss\',\'Net Profit/Loss\','
    'net."t.Transaction Date",'
    'SUM(CASE WHEN net."PL Section" IN (\'1. Operating Income\',\'4. Non Operating Income\') '
    'THEN net."Amount" ELSE -net."Amount" END),net."Channel" '
    f'FROM ({_PL}) AS net GROUP BY net."t.Transaction Date",net."Channel"'
)
print("Creating Channel PL Qry...")
v4 = create_qt("Channel PL Qry", sql4)
time.sleep(2)

# ============================================================
# Step 5: Channel Profitability pivot
# ============================================================
print("Creating Channel Profitability pivot...")
v5 = create_report("Channel Profitability", "Channel PL Qry", {})

print("\n=== FINAL VIEW IDS ===")
for name, vid in [
    ("Item Avg PO Cost Qry", v1),
    ("Channel PO Cost Qry", v2),
    ("Channel COGS Alloc Qry", v3),
    ("Channel PL Qry", v4),
    ("Channel Profitability (pivot)", v5),
]:
    print(f"  {name}: {vid}")
