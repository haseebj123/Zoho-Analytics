"""Create the 5 remaining tables: Revenue, COGS Alloc, Opex Alloc, Other Exp, PL, Pivot."""
import json, urllib.request, urllib.parse, time

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
FID = '2350577000032146061'
CFG = 'Channel Profitability Inputs'

def create(name, sql, is_report=False, base=None):
    print(f"  Creating {name} ({len(sql) if sql else 0} chars)...")
    if is_report:
        config = {
            'baseTableName': base, 'title': name, 'reportType': 'pivot', 'folderId': FID,
            'axisColumns': [
                {'type': 'row', 'columnName': 'PL Section', 'operation': 'actual'},
                {'type': 'row', 'columnName': 'a.Account Name', 'operation': 'actual'},
                {'type': 'column', 'columnName': 'Channel', 'operation': 'actual'},
                {'type': 'data', 'columnName': 'Amount', 'operation': 'sum'},
            ],
            'userFilters': [{'tableName': base, 'columnName': 't.Transaction Date', 'operation': 'range'}],
        }
        endpoint = 'reports'
    else:
        config = {'queryTableName': name, 'sqlQuery': sql, 'folderId': FID}
        endpoint = 'querytables'

    data = urllib.parse.urlencode({'CONFIG': json.dumps(config)}).encode()
    req = urllib.request.Request(
        f'https://analyticsapi.zoho.com/restapi/v2/workspaces/{WS}/{endpoint}',
        data=data, headers={
            'ZANALYTICS-ORGID': ORG, 'Authorization': f'Zoho-oauthtoken {TOKEN}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            r = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            r = json.loads(body)
        except:
            r = {'error': body}
        if r.get('data', {}).get('errorCode') == 8543:
            print(f"    Rate limited. Waiting 310s...")
            time.sleep(310)
            return create(name, sql, is_report, base)  # Retry

    vid = r.get('data', {}).get('viewId', 'FAILED')
    if vid == 'FAILED':
        print(f"    ERROR: {r}")
    else:
        print(f"    OK: {vid}")
    time.sleep(2)
    return vid

# Revenue subquery helpers
def rev(ch):
    return f"(SELECT SUM(r.\"Amount\") FROM \"Channel Revenue Qry\" r WHERE r.\"PL Section\"='1. Operating Income' AND r.\"Channel\"='{ch}')"

REV_ALL = f"(SELECT SUM(r.\"Amount\") FROM \"Channel Revenue Qry\" r WHERE r.\"PL Section\"='1. Operating Income' AND r.\"Channel\" IN ('B2B','Retail','Costco'))"
REV_BR = f"(SELECT SUM(r.\"Amount\") FROM \"Channel Revenue Qry\" r WHERE r.\"PL Section\"='1. Operating Income' AND r.\"Channel\" IN ('B2B','Retail'))"

# ============================================================
# 1. Channel Revenue Qry (config JOINs for SP, vendor, costco, cogs_unalloc)
# ============================================================
SQL1 = (
    "SELECT CASE WHEN a.\"Account Type\"='Income' THEN '1. Operating Income' "
    "WHEN a.\"Account Type\"='Cost Of Goods Sold' THEN '2. Cost of Goods Sold' "
    "WHEN a.\"Account Type\"='Other Income' THEN '4. Non Operating Income' END AS \"PL Section\","
    "a.\"Account Name\",t.\"Transaction Date\","
    "CASE WHEN a.\"Account Type\" IN ('Income','Other Income') THEN t.\"Credit - Debit\" "
    "ELSE t.\"Debit - Credit\" END AS \"Amount\","
    "CASE "
    "WHEN inv.\"Entity ID\" IS NULL AND ca.\"Channel\" IS NOT NULL THEN ca.\"Channel\" "
    "WHEN inv.\"Entity ID\" IS NULL AND cv.\"Channel\" IS NOT NULL THEN cv.\"Channel\" "
    "WHEN inv.\"Entity ID\" IS NULL AND a.\"Account Type\"='Cost Of Goods Sold' "
    "AND cu.\"Key\" IS NULL AND t.\"Entity Type\"<>'inventory_adjustment_by_quantity' THEN 'ProRataAlloc' "
    "WHEN inv.\"Entity ID\" IS NULL THEN 'Unallocated' "
    "WHEN sp.\"Channel\" IS NOT NULL THEN sp.\"Channel\" "
    "WHEN (inv.\"Sales Person ID\" IS NULL OR inv.\"Sales Person ID\"='') "
    "AND inv.\"Type\"='creditnote' THEN 'Retail' "
    "WHEN (inv.\"Sales Person ID\" IS NULL OR inv.\"Sales Person ID\"='') "
    "AND LEFT(inv.\"SO Number\",7)='0089400' THEN 'Costco' "
    "WHEN (inv.\"Sales Person ID\" IS NULL OR inv.\"Sales Person ID\"='') "
    "AND (LEFT(inv.\"SO Number\",6)='SO-EB-' OR LEFT(inv.\"SO Number\",6)='SO-MB-') THEN 'Retail' "
    "WHEN (inv.\"Sales Person ID\" IS NULL OR inv.\"Sales Person ID\"='') THEN 'B2B' "
    "ELSE 'Retail' END AS \"Channel\" "
    "FROM \"Accrual Transactions (Zoho Inventory)\" t "
    "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    "LEFT JOIN \"Entity Channel Bridge Qry\" inv ON t.\"Entity ID\"=inv.\"Entity ID\" "
    f"LEFT JOIN \"{CFG}\" ca ON ca.\"Type\"='costco_account' AND ca.\"Key\"=a.\"Account Name\" "
    f"LEFT JOIN \"{CFG}\" cv ON cv.\"Type\"='vendor' AND cv.\"Key\"=t.\"Vendor ID\" "
    f"LEFT JOIN \"{CFG}\" sp ON sp.\"Type\"='salesperson' AND sp.\"Key\"=inv.\"Sales Person ID\" "
    f"LEFT JOIN \"{CFG}\" cu ON cu.\"Type\"='cogs_unalloc' AND cu.\"Key\"=a.\"Account Name\" "
    "WHERE a.\"Account Type\" IN ('Income','Cost Of Goods Sold','Other Income')"
)

# ============================================================
# 2. Channel COGS Alloc Qry (PO cost-based, unchanged)
# ============================================================
SQL2 = (
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

# ============================================================
# 3. Channel Opex Alloc Qry (config JOINs + dynamic revenue)
# ============================================================
_B = (
    'SELECT \'3. Operating Expense\',a."Account Name",t."Transaction Date",'
    '{expr} AS "Amount",{ch} AS "Channel" '
    'FROM "Accrual Transactions (Zoho Inventory)" t '
    'JOIN "Accounts (Zoho Inventory)" a ON t."Account ID"=a."Account ID" '
    '{join} '
    'WHERE a."Account Type"=\'Expense\'{filt}'
)

_EXCL_JOIN = (
    f'LEFT JOIN (SELECT DISTINCT "Key" FROM "{CFG}" '
    f"WHERE \"Type\" IN ('payroll_pct','ad_pct','payment_account','commission_fee','unalloc_opex')) "
    'excl ON excl."Key"=a."Account Name"'
)

SQL3 = ' UNION ALL '.join([
    # Advertising from config
    _B.format(
        expr='t."Debit - Credit"*cfg."Value"', ch='cfg."Channel"',
        join=f'JOIN "{CFG}" cfg ON cfg."Type"=\'ad_pct\' AND cfg."Key"=a."Account Name"',
        filt=''
    ),
    # Payment processing from config
    _B.format(
        expr='t."Debit - Credit"*cfg."Value"', ch='cfg."Channel"',
        join=f'JOIN "{CFG}" cfg ON cfg."Type"=\'payment_account\' AND cfg."Key"=a."Account Name"',
        filt=''
    ),
    # Commissions B2B (dynamic B2B/Retail revenue, no Costco)
    _B.format(
        expr=f't."Debit - Credit"*{rev("B2B")}/{REV_BR}',
        ch="'B2B'",
        join=f'JOIN "{CFG}" cfg ON cfg."Type"=\'commission_fee\' AND cfg."Key"=a."Account Name" AND cfg."Channel"=\'B2B\'',
        filt=''
    ),
    # Commissions Retail
    _B.format(
        expr=f't."Debit - Credit"*{rev("Retail")}/{REV_BR}',
        ch="'Retail'",
        join=f'JOIN "{CFG}" cfg ON cfg."Type"=\'commission_fee\' AND cfg."Key"=a."Account Name" AND cfg."Channel"=\'Retail\'',
        filt=''
    ),
    # Other OpEx B2B (dynamic, exclude config-managed accounts)
    _B.format(
        expr=f't."Debit - Credit"*{rev("B2B")}/{REV_ALL}',
        ch="'B2B'",
        join=_EXCL_JOIN, filt=' AND excl."Key" IS NULL'
    ),
    # Other OpEx Retail
    _B.format(
        expr=f't."Debit - Credit"*{rev("Retail")}/{REV_ALL}',
        ch="'Retail'",
        join=_EXCL_JOIN, filt=' AND excl."Key" IS NULL'
    ),
    # Other OpEx Costco
    _B.format(
        expr=f't."Debit - Credit"*{rev("Costco")}/{REV_ALL}',
        ch="'Costco'",
        join=_EXCL_JOIN, filt=' AND excl."Key" IS NULL'
    ),
])

# ============================================================
# 4. Channel Other Exp Qry (config JOIN + dynamic revenue, WITH aliases)
# ============================================================
_OE_EXCL = f'LEFT JOIN "{CFG}" excl ON excl."Type"=\'unalloc_other_exp\' AND excl."Key"=a."Account Name"'

SQL4 = ' UNION ALL '.join([
    # Allocated B2B
    f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    f"t.\"Debit - Credit\"*{rev('B2B')}/{REV_ALL} AS \"Amount\",'B2B' AS \"Channel\" "
    f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
    f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    f"{_OE_EXCL} "
    f"WHERE a.\"Account Type\"='Other Expense' AND excl.\"Key\" IS NULL",
    # Allocated Retail
    f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    f"t.\"Debit - Credit\"*{rev('Retail')}/{REV_ALL} AS \"Amount\",'Retail' AS \"Channel\" "
    f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
    f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    f"{_OE_EXCL} "
    f"WHERE a.\"Account Type\"='Other Expense' AND excl.\"Key\" IS NULL",
    # Allocated Costco
    f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    f"t.\"Debit - Credit\"*{rev('Costco')}/{REV_ALL} AS \"Amount\",'Costco' AS \"Channel\" "
    f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
    f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    f"{_OE_EXCL} "
    f"WHERE a.\"Account Type\"='Other Expense' AND excl.\"Key\" IS NULL",
    # Unallocated from config
    f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    f"t.\"Debit - Credit\" AS \"Amount\",cfg.\"Channel\" "
    f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
    f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    f"JOIN \"{CFG}\" cfg ON cfg.\"Type\"='unalloc_other_exp' AND cfg.\"Key\"=a.\"Account Name\" "
    f"WHERE a.\"Account Type\"='Other Expense'",
])

# ============================================================
# 5. Channel PL Qry (with Net P/L)
# ============================================================
_PL = (
    'SELECT * FROM "Channel Revenue Qry" WHERE "Channel"<>\'ProRataAlloc\' '
    'UNION ALL SELECT * FROM "Channel Opex Payroll Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Alloc Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Unalloc Qry" '
    'UNION ALL SELECT * FROM "Channel Other Exp Qry" '
    'UNION ALL SELECT * FROM "Channel COGS Alloc Qry"'
)
SQL5 = (
    f'{_PL} UNION ALL SELECT \'6. Net Profit/Loss\',\'Net Profit/Loss\','
    'net."t.Transaction Date",'
    'SUM(CASE WHEN net."PL Section" IN (\'1. Operating Income\',\'4. Non Operating Income\') '
    'THEN net."Amount" ELSE -net."Amount" END),net."Channel" '
    f'FROM ({_PL}) AS net GROUP BY net."t.Transaction Date",net."Channel"'
)

# ============================================================
# Execute
# ============================================================
print("\n--- 1. Channel Revenue Qry ---")
v1 = create("Channel Revenue Qry", SQL1)

print("\n--- 2. Channel COGS Alloc Qry ---")
v2 = create("Channel COGS Alloc Qry", SQL2)

print("\n--- 3. Channel Opex Alloc Qry ---")
v3 = create("Channel Opex Alloc Qry", SQL3)

print("\n--- 4. Channel Other Exp Qry ---")
v4 = create("Channel Other Exp Qry", SQL4)

print("\n--- 5. Channel PL Qry ---")
v5 = create("Channel PL Qry", SQL5)

print("\n--- 6. Channel Profitability pivot ---")
v6 = create("Channel Profitability", None, is_report=True, base="Channel PL Qry")

print(f"\n{'='*50}")
for name, vid in [
    ("Channel Revenue Qry", v1), ("Channel COGS Alloc Qry", v2),
    ("Channel Opex Alloc Qry", v3), ("Channel Other Exp Qry", v4),
    ("Channel PL Qry", v5), ("Channel Profitability", v6),
]:
    print(f"  {name}: {vid}")
