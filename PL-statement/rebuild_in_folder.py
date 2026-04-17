"""Rebuild all Channel Profitability query tables inside a Zoho Analytics folder."""
import json
import urllib.request
import urllib.parse
import time

TOKEN = "1000.f0f31712cd198cd31f3e6825f11bfbd9.e59f8c86ea5e89494f101cf37b8e6247"
ORG = "712029089"
WS = "2350577000000005001"
FOLDER_ID = "2350577000032146061"
BASE = f"https://analyticsapi.zoho.com/restapi/v2/workspaces/{WS}"

HEADERS = {
    "ZANALYTICS-ORGID": ORG,
    "Authorization": f"Zoho-oauthtoken {TOKEN}",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Current view IDs to delete (reverse dependency order)
DELETE_IDS = [
    "2350577000032154059",  # Channel Profitability pivot
    "2350577000032144027",  # Channel PL Qry
    "2350577000032154049",  # Channel COGS Alloc Qry
    "2350577000032150027",  # Channel Revenue Qry
    "2350577000032154023",  # Entity Channel Bridge Qry
    "2350577000032152029",  # Invoice Channel Bridge Qry
    "2350577000032155062",  # Channel Opex Payroll Qry
    "2350577000032153094",  # Channel Opex Alloc Qry
    "2350577000032144016",  # Channel Opex Unalloc Qry
    "2350577000032147036",  # Channel Other Exp Qry
]

# Also delete the test QT if it exists
DELETE_IDS.insert(0, "2350577000032148094")


def api_call(method, url, config=None):
    data = None
    if config is not None:
        data = urllib.parse.urlencode({"CONFIG": json.dumps(config)}).encode()
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            return json.loads(body) if body.strip() else {"status": "success"}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body) if body.strip() else {"error": str(e)}
        except:
            return {"error": body or str(e)}


def delete_view(view_id):
    url = f"{BASE}/views/{view_id}"
    result = api_call("DELETE", url, {})
    status = result.get("status", result.get("summary", "?"))
    print(f"  DELETE {view_id}: {status}")


def create_qt(name, sql):
    url = f"{BASE}/querytables"
    config = {"queryTableName": name, "sqlQuery": sql, "folderId": FOLDER_ID}
    result = api_call("POST", url, config)
    vid = result.get("data", {}).get("viewId", "FAILED")
    print(f"  CREATE {name}: {vid}")
    if vid == "FAILED":
        print(f"    Error: {result}")
    return vid


def create_report(title, base_table, report_type, axis_columns, user_filters=None):
    url = f"{BASE}/reports"
    config = {
        "baseTableName": base_table,
        "title": title,
        "reportType": report_type,
        "axisColumns": axis_columns,
        "folderId": FOLDER_ID,
    }
    if user_filters:
        config["userFilters"] = user_filters
    result = api_call("POST", url, config)
    vid = result.get("data", {}).get("viewId", "FAILED")
    print(f"  CREATE REPORT {title}: {vid}")
    if vid == "FAILED":
        print(f"    Error: {result}")
    return vid


# ============================================================
# SQL definitions
# ============================================================

SQL_INVOICE_BRIDGE = (
    'SELECT "Invoice ID","Sales Person ID",'
    '"Sales Order #" AS "SO Number" '
    'FROM "Invoices (Zoho Inventory)"'
)

SQL_ENTITY_BRIDGE = (
    'SELECT "Invoice ID" AS "Entity ID","Sales Person ID","SO Number",'
    "'invoice' AS \"Type\" "
    'FROM "Invoice Channel Bridge Qry" '
    "UNION ALL "
    'SELECT "CreditNotes ID","Sales Person ID",'
    "'' AS \"SO Number\",'creditnote' AS \"Type\" "
    'FROM "Credit Notes (Zoho Inventory)"'
)

SQL_CHANNEL_REVENUE = (
    "SELECT CASE WHEN a.\"Account Type\"='Income' THEN '1. Operating Income' "
    "WHEN a.\"Account Type\"='Cost Of Goods Sold' THEN '2. Cost of Goods Sold' "
    "WHEN a.\"Account Type\"='Other Income' THEN '4. Non Operating Income' END AS \"PL Section\","
    "a.\"Account Name\",t.\"Transaction Date\","
    "CASE WHEN a.\"Account Type\" IN ('Income','Other Income') THEN t.\"Credit - Debit\" "
    "ELSE t.\"Debit - Credit\" END AS \"Amount\","
    "CASE WHEN inv.\"Entity ID\" IS NULL AND a.\"Account Name\" IN ("
    "'Discount - Costco Sales','Shipping, Freight -Costco','Cost of Labour - Costco',"
    "'Sales of Product Income Costco','Cost of Goods Sold Costco','Other Charges -Shipping Discount'"
    ") THEN 'Costco' "
    "WHEN inv.\"Entity ID\" IS NULL AND t.\"Vendor ID\" IN ("
    "1979954000016532592,1979954000033457005,1979954000097951129,1979954000102131941,"
    "1979954000105760457,1979954000117210664,1979954000123962742,1979954000123962839,"
    "1979954000123337029,1979954000130643333,1979954000131857648) THEN 'Retail' "
    "WHEN inv.\"Entity ID\" IS NULL AND a.\"Account Type\"='Cost Of Goods Sold' "
    "AND a.\"Account Name\"<>'Subcontractors - COGS' "
    "AND t.\"Entity Type\"<>'inventory_adjustment_by_quantity' THEN 'ProRataAlloc' "
    "WHEN inv.\"Entity ID\" IS NULL THEN 'Unallocated' "
    "WHEN inv.\"Sales Person ID\" IN ('1979954000002036262','1979954000044158860') THEN 'B2B' "
    "WHEN inv.\"Sales Person ID\" IN ('1979954000047575788','1979954000053988204') THEN 'Costco' "
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
    "WHERE a.\"Account Type\" IN ('Income','Cost Of Goods Sold','Other Income')"
)

SQL_COGS_ALLOC = (
    "SELECT \"PL Section\",\"a.Account Name\",\"t.Transaction Date\","
    "\"Amount\"*0.372511 AS \"Amount\",'B2B' AS \"Channel\" "
    "FROM \"Channel Revenue Qry\" WHERE \"Channel\"='ProRataAlloc' "
    "UNION ALL SELECT \"PL Section\",\"a.Account Name\",\"t.Transaction Date\","
    "\"Amount\"*0.49946 AS \"Amount\",'Retail' AS \"Channel\" "
    "FROM \"Channel Revenue Qry\" WHERE \"Channel\"='ProRataAlloc' "
    "UNION ALL SELECT \"PL Section\",\"a.Account Name\",\"t.Transaction Date\","
    "\"Amount\"*0.128029 AS \"Amount\",'Costco' AS \"Channel\" "
    "FROM \"Channel Revenue Qry\" WHERE \"Channel\"='ProRataAlloc'"
)

_PAYROLL_ACCOUNTS = (
    "'Payroll Expense','Payroll Expense:Taxes','Payroll Expense:Wages',"
    "'Salaries and Employee Wages','EHT Expense','Work Safe BC Expense',"
    "'Payroll-SRED Wages Reimbursement'"
)
_PAYROLL_BASE = (
    "SELECT '3. Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    "t.\"Debit - Credit\"*{pct},'{ch}' "
    "FROM \"Accrual Transactions (Zoho Inventory)\" t "
    "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    "WHERE a.\"Account Type\"='Expense' AND a.\"Account Name\" IN ({accts})"
)
SQL_OPEX_PAYROLL = " UNION ALL ".join(
    _PAYROLL_BASE.format(pct=p, ch=c, accts=_PAYROLL_ACCOUNTS)
    for p, c in [("0.306944", "B2B"), ("0.365278", "Retail"), ("0.077778", "Costco"), ("0.25", "Unallocated")]
)

_AD_ACCOUNTS = "'Advertising','Advertising And Marketing','Promotional'"
_PAY_ACCOUNTS = (
    "'Stripe Fee','Stripe Fees','Stripe Fees  US $','Card Fee','Paypal charges',"
    "'QuickBooks Payments Fees','QuickBooks Payments Fees ( 71 )',"
    "'Shipearly Fee','Shopify Fee','PayPlan Fee','Amazon Fee charges'"
)
_EXCL_ACCOUNTS = f"{_PAYROLL_ACCOUNTS},'Payroll-IRAP -WSBC - BCTech -ECO Wages Reimbursement','Payroll-IRAP Wages Reimbursement',{_AD_ACCOUNTS},{_PAY_ACCOUNTS},'Exchange Gain or Loss'"
_OPEX_BASE = (
    "SELECT '3. Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    "t.\"Debit - Credit\"*{pct},'{ch}' "
    "FROM \"Accrual Transactions (Zoho Inventory)\" t "
    "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    "WHERE a.\"Account Type\"='Expense' AND a.\"Account Name\" NOT IN ({excl})"
)

SQL_OPEX_ALLOC = " UNION ALL ".join([
    _PAYROLL_BASE.format(pct="0.1", ch="B2B", accts=_AD_ACCOUNTS),
    _PAYROLL_BASE.format(pct="0.9", ch="Retail", accts=_AD_ACCOUNTS),
    (
        "SELECT '3. Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
        "t.\"Debit - Credit\",'Retail' "
        "FROM \"Accrual Transactions (Zoho Inventory)\" t "
        "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
        f"WHERE a.\"Account Type\"='Expense' AND a.\"Account Name\" IN ({_PAY_ACCOUNTS})"
    ),
    _OPEX_BASE.format(pct="0.372511", ch="B2B", excl=_EXCL_ACCOUNTS),
    _OPEX_BASE.format(pct="0.499460", ch="Retail", excl=_EXCL_ACCOUNTS),
    _OPEX_BASE.format(pct="0.128029", ch="Costco", excl=_EXCL_ACCOUNTS),
])

SQL_OPEX_UNALLOC = (
    "SELECT '3. Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    "t.\"Debit - Credit\",'Unallocated' "
    "FROM \"Accrual Transactions (Zoho Inventory)\" t "
    "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    "WHERE a.\"Account Type\"='Expense' AND a.\"Account Name\" IN ("
    "'Exchange Gain or Loss','Payroll-IRAP -WSBC - BCTech -ECO Wages Reimbursement',"
    "'Payroll-IRAP Wages Reimbursement')"
)

_OTHER_EXP_UNALLOC = (
    "'SRED - Flex UL','SRED - MUCEB - MTB','SRED -CLESV','SRED -Snow track',"
    "'SRED- ATMP','SRED- Snowbike kit','SRED-ATV','SRED-CEBP',"
    "'SRED-Hydrofoil Electric Water Mobility','SRED-IOT',"
    "'SRED-Light -e- Mobility Enclosure','SRED-VEEMO','SRED-eCity Bike',"
    "'CanExport','Security','Exchange','IRAP - B.I','IRAP - General','IRAP - eATV',"
    "'Amortization','Provisions for Income Tax','Penalties and settlements',"
    "'Reconciliation Discrepancies'"
)
_OE_BASE = (
    "SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
    "t.\"Debit - Credit\"*{pct},'{ch}' "
    "FROM \"Accrual Transactions (Zoho Inventory)\" t "
    "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
    "WHERE a.\"Account Type\"='Other Expense' AND a.\"Account Name\" NOT IN ({excl})"
)
SQL_OTHER_EXP = " UNION ALL ".join([
    _OE_BASE.format(pct="0.372511", ch="B2B", excl=_OTHER_EXP_UNALLOC),
    _OE_BASE.format(pct="0.499460", ch="Retail", excl=_OTHER_EXP_UNALLOC),
    _OE_BASE.format(pct="0.128029", ch="Costco", excl=_OTHER_EXP_UNALLOC),
    (
        "SELECT '5. Non Operating Expense',a.\"Account Name\",t.\"Transaction Date\","
        "t.\"Debit - Credit\",'Unallocated' "
        "FROM \"Accrual Transactions (Zoho Inventory)\" t "
        "JOIN \"Accounts (Zoho Inventory)\" a ON t.\"Account ID\"=a.\"Account ID\" "
        f"WHERE a.\"Account Type\"='Other Expense' AND a.\"Account Name\" IN ({_OTHER_EXP_UNALLOC})"
    ),
])

_PL_TABLES = (
    'SELECT * FROM "Channel Revenue Qry" WHERE "Channel"<>\'ProRataAlloc\' '
    'UNION ALL SELECT * FROM "Channel Opex Payroll Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Alloc Qry" '
    'UNION ALL SELECT * FROM "Channel Opex Unalloc Qry" '
    'UNION ALL SELECT * FROM "Channel Other Exp Qry" '
    'UNION ALL SELECT * FROM "Channel COGS Alloc Qry"'
)
SQL_CHANNEL_PL = (
    f"{_PL_TABLES} "
    "UNION ALL SELECT '6. Net Profit/Loss','Net Profit/Loss',"
    "net.\"t.Transaction Date\","
    "SUM(CASE WHEN net.\"PL Section\" IN ('1. Operating Income','4. Non Operating Income') "
    "THEN net.\"Amount\" ELSE -net.\"Amount\" END),net.\"Channel\" "
    f"FROM ({_PL_TABLES}) AS net "
    "GROUP BY net.\"t.Transaction Date\",net.\"Channel\""
)


# ============================================================
# Execute
# ============================================================

print("=== STEP 1: Delete existing views ===")
for vid in DELETE_IDS:
    delete_view(vid)
    time.sleep(0.3)

print("\n=== STEP 2: Create query tables in folder ===")

v1 = create_qt("Invoice Channel Bridge Qry", SQL_INVOICE_BRIDGE)
time.sleep(1)

v2 = create_qt("Entity Channel Bridge Qry", SQL_ENTITY_BRIDGE)
time.sleep(1)

v3 = create_qt("Channel Revenue Qry", SQL_CHANNEL_REVENUE)
time.sleep(1)

v4 = create_qt("Channel COGS Alloc Qry", SQL_COGS_ALLOC)
time.sleep(1)

v5 = create_qt("Channel Opex Payroll Qry", SQL_OPEX_PAYROLL)
time.sleep(1)

v6 = create_qt("Channel Opex Alloc Qry", SQL_OPEX_ALLOC)
time.sleep(1)

v7 = create_qt("Channel Opex Unalloc Qry", SQL_OPEX_UNALLOC)
time.sleep(1)

v8 = create_qt("Channel Other Exp Qry", SQL_OTHER_EXP)
time.sleep(1)

v9 = create_qt("Channel PL Qry", SQL_CHANNEL_PL)
time.sleep(1)

print("\n=== STEP 3: Create pivot report ===")
v10 = create_report(
    "Channel Profitability",
    "Channel PL Qry",
    "pivot",
    [
        {"type": "row", "columnName": "PL Section", "operation": "actual"},
        {"type": "row", "columnName": "a.Account Name", "operation": "actual"},
        {"type": "column", "columnName": "Channel", "operation": "actual"},
        {"type": "data", "columnName": "Amount", "operation": "sum"},
    ],
    [{"tableName": "Channel PL Qry", "columnName": "t.Transaction Date", "operation": "range"}],
)

print("\n=== FINAL VIEW IDS ===")
names = [
    "Invoice Channel Bridge Qry", "Entity Channel Bridge Qry",
    "Channel Revenue Qry", "Channel COGS Alloc Qry",
    "Channel Opex Payroll Qry", "Channel Opex Alloc Qry",
    "Channel Opex Unalloc Qry", "Channel Other Exp Qry",
    "Channel PL Qry", "Channel Profitability (pivot)",
]
for name, vid in zip(names, [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10]):
    print(f"  {name}: {vid}")
