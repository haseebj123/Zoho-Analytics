"""
Refactor all Channel Profitability query tables to use Channel Profitability Inputs
config table instead of hardcoded values.

Tables rebuilt:
1. Channel Revenue Qry - SP IDs, vendor IDs, costco accounts from config
2. Channel Opex Payroll Qry - percentages from config
3. Channel Opex Alloc Qry - ad/payment/commission accounts from config
4. Channel Opex Unalloc Qry - account list from config
5. Channel Other Exp Qry - account list from config
6. Channel PL Qry - UNION ALL (unchanged logic)
7. Channel Profitability pivot

Unchanged: Invoice Channel Bridge, Entity Channel Bridge, Item Avg PO Cost,
           Channel PO Cost (already uses config), Channel COGS Alloc (uses PO Cost)
"""
import json, urllib.request, urllib.parse, time, sys

# ============================================================
# Auth
# ============================================================
def get_token():
    data = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'client_id': '1000.LQPSANXX3UYZ2T9IAZQEZ0YIZGNIEW',
        'client_secret': '175c6141a81c8ef20abf52c57772ef9c0b6af13b7a',
        'refresh_token': '1000.1975e5d0a4ad36c8314dee91361192ae.07278eb068b68a826dbf52f4360ac45c'
    }).encode()
    req = urllib.request.Request('https://accounts.zoho.com/oauth/v2/token', data=data, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())['access_token']

TOKEN = get_token()
print(f"Token: {TOKEN[:20]}...")

ORG = '712029089'
WS = '2350577000000005001'
FOLDER_ID = '2350577000032146061'
CFG = 'Channel Profitability Inputs'

def api(method, endpoint, config, retry=3):
    data = urllib.parse.urlencode({'CONFIG': json.dumps(config)}).encode()
    for attempt in range(retry):
        req = urllib.request.Request(
            f'https://analyticsapi.zoho.com/restapi/v2/workspaces/{WS}/{endpoint}',
            data=data, headers={
                'ZANALYTICS-ORGID': ORG, 'Authorization': f'Zoho-oauthtoken {TOKEN}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode()
                if not body.strip():
                    return {'status': 'success'}
                r = json.loads(body)
                return r
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                r = json.loads(body) if body.strip() else {'error': str(e)}
            except:
                r = {'error': body or str(e)}
            if r.get('data', {}).get('errorCode') == 8543:  # Rate limit
                wait = 310
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            return r
    return r

def delete_view(vid, name=""):
    r = api('DELETE', f'views/{vid}', {})
    status = r.get('status', r.get('summary', '?'))
    print(f"  DELETE {name} ({vid}): {status}")
    time.sleep(1)

def create_qt(name, sql):
    print(f"  Creating {name} ({len(sql)} chars)...")
    r = api('POST', 'querytables', {'queryTableName': name, 'sqlQuery': sql, 'folderId': FOLDER_ID})
    vid = r.get('data', {}).get('viewId', 'FAILED')
    if vid == 'FAILED':
        print(f"    ERROR: {r}")
    else:
        print(f"    OK: {vid}")
    time.sleep(2)
    return vid

def create_pivot(title, base):
    r = api('POST', 'reports', {
        'baseTableName': base, 'title': title, 'reportType': 'pivot', 'folderId': FOLDER_ID,
        'axisColumns': [
            {'type': 'row', 'columnName': 'PL Section', 'operation': 'actual'},
            {'type': 'row', 'columnName': 'a.Account Name', 'operation': 'actual'},
            {'type': 'column', 'columnName': 'Channel', 'operation': 'actual'},
            {'type': 'data', 'columnName': 'Amount', 'operation': 'sum'},
        ],
        'userFilters': [{'tableName': base, 'columnName': 't.Transaction Date', 'operation': 'range'}],
    })
    vid = r.get('data', {}).get('viewId', 'FAILED')
    print(f"  Pivot {title}: {vid}")
    time.sleep(2)
    return vid


# ============================================================
# SQL Definitions - all referencing config table
# ============================================================

# 1. Channel Revenue Qry
#    - costco_account, vendor, salesperson from config JOINs
#    - cogs_unalloc from config JOIN
#    - SO prefix + defaults still structural (rarely change)
SQL_REVENUE = (
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

# 2. Channel Opex Payroll Qry
#    - JOIN to payroll_pct: each transaction * percentage, auto-generates 4 rows per channel
SQL_PAYROLL = (
    "SELECT '3. Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    "t.\"Debit - Credit\"*cfg.\"Value\",cfg.\"Channel\" "
    "FROM \"Accrual Transactions (Zoho Inventory)\" t "
    "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    f"JOIN \"{CFG}\" cfg ON cfg.\"Type\"='payroll_pct' AND cfg.\"Key\"=a.\"Account Name\" "
    "WHERE a.\"Account Type\"='Expense'"
)

# 3. Channel Opex Alloc Qry
#    - Advertising: JOIN to ad_pct config
#    - Payment processing: JOIN to payment_account config
#    - Commissions: JOIN to commission_fee config + dynamic revenue subquery (B2B/Retail only)
#    - Other OpEx: dynamic revenue split, excluding all config-managed accounts

# Revenue subqueries for commission split (B2B/Retail only, no Costco)
_REV_BR = '(SELECT SUM(r."Amount") FROM "Channel Revenue Qry" r WHERE r."PL Section"=\'1. Operating Income\' AND r."Channel" IN (\'B2B\',\'Retail\'))'

# Base for each section
_B = (
    'SELECT \'3. Operating Expense\',a."Account Name",t."Transaction Date",'
    '{expr},{ch} '
    'FROM "Accrual Transactions (Zoho Inventory)" t '
    'JOIN "Accounts (Zoho Inventory)" a ON t."Account ID"=a."Account ID" '
    '{join} '
    'WHERE a."Account Type"=\'Expense\'{filt}'
)

# For Other OpEx exclusion: LEFT JOIN to find accounts already handled by other types
_EXCL_JOIN = (
    f'LEFT JOIN (SELECT DISTINCT "Key" FROM "{CFG}" '
    f"WHERE \"Type\" IN ('payroll_pct','ad_pct','payment_account','commission_fee','unalloc_opex')) "
    'excl ON excl."Key"=a."Account Name"'
)

# Revenue subqueries for 3-way split
_REV_ALL = '(SELECT SUM(r."Amount") FROM "Channel Revenue Qry" r WHERE r."PL Section"=\'1. Operating Income\' AND r."Channel" IN (\'B2B\',\'Retail\',\'Costco\'))'
_REV_CH = lambda ch: f'(SELECT SUM(r."Amount") FROM "Channel Revenue Qry" r WHERE r."PL Section"=\'1. Operating Income\' AND r."Channel"=\'{ch}\')'

SQL_OPEX_ALLOC = ' UNION ALL '.join([
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
    # Commissions B2B (dynamic revenue, no Costco)
    _B.format(
        expr=f't."Debit - Credit"*{_REV_CH("B2B")}/{_REV_BR}',
        ch="'B2B'",
        join=f'JOIN "{CFG}" cfg ON cfg."Type"=\'commission_fee\' AND cfg."Key"=a."Account Name" AND cfg."Channel"=\'B2B\'',
        filt=''
    ),
    # Commissions Retail
    _B.format(
        expr=f't."Debit - Credit"*{_REV_CH("Retail")}/{_REV_BR}',
        ch="'Retail'",
        join=f'JOIN "{CFG}" cfg ON cfg."Type"=\'commission_fee\' AND cfg."Key"=a."Account Name" AND cfg."Channel"=\'Retail\'',
        filt=''
    ),
    # Other OpEx B2B (dynamic revenue, excludes all config-managed accounts)
    _B.format(
        expr=f't."Debit - Credit"*{_REV_CH("B2B")}/{_REV_ALL}',
        ch="'B2B'",
        join=_EXCL_JOIN,
        filt=' AND excl."Key" IS NULL'
    ),
    # Other OpEx Retail
    _B.format(
        expr=f't."Debit - Credit"*{_REV_CH("Retail")}/{_REV_ALL}',
        ch="'Retail'",
        join=_EXCL_JOIN,
        filt=' AND excl."Key" IS NULL'
    ),
    # Other OpEx Costco
    _B.format(
        expr=f't."Debit - Credit"*{_REV_CH("Costco")}/{_REV_ALL}',
        ch="'Costco'",
        join=_EXCL_JOIN,
        filt=' AND excl."Key" IS NULL'
    ),
])

# 4. Channel Opex Unalloc Qry - JOIN to config
SQL_OPEX_UNALLOC = (
    "SELECT '3. Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    "t.\"Debit - Credit\",cfg.\"Channel\" "
    "FROM \"Accrual Transactions (Zoho Inventory)\" t "
    "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    f"JOIN \"{CFG}\" cfg ON cfg.\"Type\"='unalloc_opex' AND cfg.\"Key\"=a.\"Account Name\" "
    "WHERE a.\"Account Type\"='Expense'"
)

# 5. Channel Other Exp Qry
#    - Unallocated: JOIN to unalloc_other_exp config
#    - Allocated: dynamic revenue split, exclude unallocated accounts
_OE_EXCL_JOIN = (
    f'LEFT JOIN "{CFG}" excl ON excl."Type"=\'unalloc_other_exp\' AND excl."Key"=a."Account Name"'
)

SQL_OTHER_EXP = ' UNION ALL '.join([
    # Allocated B2B
    (
        f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
        f"t.\"Debit - Credit\"*{_REV_CH('B2B')}/{_REV_ALL},'B2B' "
        f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
        f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
        f"{_OE_EXCL_JOIN} "
        f"WHERE a.\"Account Type\"='Other Expense' AND excl.\"Key\" IS NULL"
    ),
    # Allocated Retail
    (
        f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
        f"t.\"Debit - Credit\"*{_REV_CH('Retail')}/{_REV_ALL},'Retail' "
        f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
        f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
        f"{_OE_EXCL_JOIN} "
        f"WHERE a.\"Account Type\"='Other Expense' AND excl.\"Key\" IS NULL"
    ),
    # Allocated Costco
    (
        f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
        f"t.\"Debit - Credit\"*{_REV_CH('Costco')}/{_REV_ALL},'Costco' "
        f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
        f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
        f"{_OE_EXCL_JOIN} "
        f"WHERE a.\"Account Type\"='Other Expense' AND excl.\"Key\" IS NULL"
    ),
    # Unallocated from config
    (
        f"SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
        f"t.\"Debit - Credit\",cfg.\"Channel\" "
        f"FROM \"Accrual Transactions (Zoho Inventory)\" t "
        f"JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
        f"JOIN \"{CFG}\" cfg ON cfg.\"Type\"='unalloc_other_exp' AND cfg.\"Key\"=a.\"Account Name\" "
        f"WHERE a.\"Account Type\"='Other Expense'"
    ),
])

# 6. Channel PL Qry (with Net P/L)
_PL = (
    'SELECT * FROM "Channel Revenue Qry" WHERE "Channel"<>\'ProRataAlloc\' '
    'UNION ALL SELECT * FROM "Channel Opex Payroll Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Alloc Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Unalloc Qry" '
    'UNION ALL SELECT * FROM "Channel Other Exp Qry" '
    'UNION ALL SELECT * FROM "Channel COGS Alloc Qry"'
)
SQL_PL = (
    f'{_PL} UNION ALL SELECT \'6. Net Profit/Loss\',\'Net Profit/Loss\','
    'net."t.Transaction Date",'
    'SUM(CASE WHEN net."PL Section" IN (\'1. Operating Income\',\'4. Non Operating Income\') '
    'THEN net."Amount" ELSE -net."Amount" END),net."Channel" '
    f'FROM ({_PL}) AS net GROUP BY net."t.Transaction Date",net."Channel"'
)


# ============================================================
# Execute
# ============================================================

# Delete order (reverse dependencies)
DELETE = [
    ("2350577000032149105", "Channel Profitability pivot"),
    ("2350577000032145086", "Channel PL Qry"),
    ("2350577000032145075", "Channel COGS Alloc Qry"),
    ("2350577000032153110", "Channel Revenue Qry"),
    ("2350577000032143069", "Channel Opex Payroll Qry"),
    ("2350577000032144052", "Channel Opex Alloc Qry"),
    ("2350577000032146063", "Channel Opex Unalloc Qry"),
    ("2350577000032146074", "Channel Other Exp Qry"),
]

print("\n=== STEP 1: Delete existing views ===")
for vid, name in DELETE:
    delete_view(vid, name)

print("\n=== STEP 2: Create refactored query tables ===")

print(f"\n--- Channel Revenue Qry ---")
v_rev = create_qt("Channel Revenue Qry", SQL_REVENUE)

print(f"\n--- Channel COGS Alloc Qry ---")
# Re-use existing PO-based dynamic SQL
SQL_COGS = (
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
v_cogs = create_qt("Channel COGS Alloc Qry", SQL_COGS)

print(f"\n--- Channel Opex Payroll Qry ---")
v_pay = create_qt("Channel Opex Payroll Qry", SQL_PAYROLL)

print(f"\n--- Channel Opex Alloc Qry ---")
v_alloc = create_qt("Channel Opex Alloc Qry", SQL_OPEX_ALLOC)

print(f"\n--- Channel Opex Unalloc Qry ---")
v_unalloc = create_qt("Channel Opex Unalloc Qry", SQL_OPEX_UNALLOC)

print(f"\n--- Channel Other Exp Qry ---")
v_other = create_qt("Channel Other Exp Qry", SQL_OTHER_EXP)

print(f"\n--- Channel PL Qry ---")
v_pl = create_qt("Channel PL Qry", SQL_PL)

print(f"\n=== STEP 3: Create pivot ===")
v_pivot = create_pivot("Channel Profitability", "Channel PL Qry")

print(f"\n{'='*60}")
print(f"=== FINAL VIEW IDS ===")
print(f"{'='*60}")
results = [
    ("Channel Revenue Qry", v_rev),
    ("Channel COGS Alloc Qry", v_cogs),
    ("Channel Opex Payroll Qry", v_pay),
    ("Channel Opex Alloc Qry", v_alloc),
    ("Channel Opex Unalloc Qry", v_unalloc),
    ("Channel Other Exp Qry", v_other),
    ("Channel PL Qry", v_pl),
    ("Channel Profitability (pivot)", v_pivot),
]
failed = False
for name, vid in results:
    status = "FAILED" if vid == "FAILED" else "OK"
    print(f"  {name}: {vid} [{status}]")
    if vid == "FAILED":
        failed = True

if failed:
    print("\nSome tables FAILED. Check errors above.")
    sys.exit(1)
else:
    print("\nAll tables created successfully!")
