"""Rebuild Channel Opex Alloc Qry with Commissions and fees as Retail-only."""
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
            'ZANALYTICS-ORGID': ORG, 'Authorization': f'Zoho-oauthtoken {TOKEN}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            r = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        r = json.loads(e.read().decode())
    vid = r.get('data', {}).get('viewId', 'FAILED')
    print(f"  {name}: {vid}")
    if vid == 'FAILED': print(f"    Error: {r}")
    return vid

def create_report(title, base):
    config = json.dumps({
        'baseTableName': base, 'title': title, 'reportType': 'pivot', 'folderId': FOLDER_ID,
        'axisColumns': [
            {'type': 'row', 'columnName': 'PL Section', 'operation': 'actual'},
            {'type': 'row', 'columnName': 'a.Account Name', 'operation': 'actual'},
            {'type': 'column', 'columnName': 'Channel', 'operation': 'actual'},
            {'type': 'data', 'columnName': 'Amount', 'operation': 'sum'},
        ],
        'userFilters': [{'tableName': base, 'columnName': 't.Transaction Date', 'operation': 'range'}],
    })
    data = urllib.parse.urlencode({'CONFIG': config}).encode()
    req = urllib.request.Request(
        f'https://analyticsapi.zoho.com/restapi/v2/workspaces/{WS}/reports',
        data=data, headers={
            'ZANALYTICS-ORGID': ORG, 'Authorization': f'Zoho-oauthtoken {TOKEN}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            r = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        r = json.loads(e.read().decode())
    vid = r.get('data', {}).get('viewId', 'FAILED')
    print(f"  {title}: {vid}")
    if vid == 'FAILED': print(f"    Error: {r}")
    return vid

# Account lists
_PAYROLL = (
    "'Payroll Expense','Payroll Expense:Taxes','Payroll Expense:Wages',"
    "'Salaries and Employee Wages','EHT Expense','Work Safe BC Expense',"
    "'Payroll-SRED Wages Reimbursement',"
    "'Payroll-IRAP -WSBC - BCTech -ECO Wages Reimbursement',"
    "'Payroll-IRAP Wages Reimbursement'"
)
_ADS = "'Advertising','Advertising And Marketing','Promotional'"
_PAYMENT = (
    "'Stripe Fee','Stripe Fees','Stripe Fees  US $','Card Fee',"
    "'Paypal charges','QuickBooks Payments Fees',"
    "'QuickBooks Payments Fees ( 71 )',"
    "'Shipearly Fee','Shopify Fee','PayPlan Fee','Amazon Fee charges',"
    "'Commissions and fees'"
)
_EXCL = f"{_PAYROLL},{_ADS},{_PAYMENT},'Exchange Gain or Loss'"

_BASE = (
    'SELECT \'3. Operating Expense\',a."Account Name",t."Transaction Date",'
    't."Debit - Credit"*{pct},\'{ch}\' '
    'FROM "Accrual Transactions (Zoho Inventory)" t '
    'JOIN "Accounts (Zoho Inventory)" a ON t."Account ID"=a."Account ID" '
    'WHERE a."Account Type"=\'Expense\''
)

sql = ' UNION ALL '.join([
    # Advertising B2B 10%
    f"{_BASE.format(pct='0.1', ch='B2B')} AND a.\"Account Name\" IN ({_ADS})",
    # Advertising Retail 90%
    f"{_BASE.format(pct='0.9', ch='Retail')} AND a.\"Account Name\" IN ({_ADS})",
    # Payment processing + Commissions 100% Retail
    f"{_BASE.format(pct='1', ch='Retail').replace('*1', '')} AND a.\"Account Name\" IN ({_PAYMENT})",
    # Other OpEx B2B
    f"{_BASE.format(pct='0.372511', ch='B2B')} AND a.\"Account Name\" NOT IN ({_EXCL})",
    # Other OpEx Retail
    f"{_BASE.format(pct='0.499460', ch='Retail')} AND a.\"Account Name\" NOT IN ({_EXCL})",
    # Other OpEx Costco
    f"{_BASE.format(pct='0.128029', ch='Costco')} AND a.\"Account Name\" NOT IN ({_EXCL})",
])

# Fix the payment section (remove the *1 artifact)
sql = sql.replace("t.\"Debit - Credit\"*1", "t.\"Debit - Credit\"")

print("Creating Channel Opex Alloc Qry...")
v1 = create_qt("Channel Opex Alloc Qry", sql)
time.sleep(2)

# Channel PL Qry
_PL = (
    'SELECT * FROM "Channel Revenue Qry" WHERE "Channel"<>\'ProRataAlloc\' '
    'UNION ALL SELECT * FROM "Channel Opex Payroll Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Alloc Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Unalloc Qry" '
    'UNION ALL SELECT * FROM "Channel Other Exp Qry" '
    'UNION ALL SELECT * FROM "Channel COGS Alloc Qry"'
)
sql_pl = (
    f'{_PL} UNION ALL SELECT \'6. Net Profit/Loss\',\'Net Profit/Loss\','
    'net."t.Transaction Date",'
    'SUM(CASE WHEN net."PL Section" IN (\'1. Operating Income\',\'4. Non Operating Income\') '
    'THEN net."Amount" ELSE -net."Amount" END),net."Channel" '
    f'FROM ({_PL}) AS net GROUP BY net."t.Transaction Date",net."Channel"'
)
print("Creating Channel PL Qry...")
v2 = create_qt("Channel PL Qry", sql_pl)
time.sleep(2)

print("Creating Channel Profitability pivot...")
v3 = create_report("Channel Profitability", "Channel PL Qry")

print(f"\n=== RESULTS ===")
print(f"  Channel Opex Alloc Qry: {v1}")
print(f"  Channel PL Qry: {v2}")
print(f"  Channel Profitability: {v3}")
