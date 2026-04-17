"""Import Channel Profitability config data with proper text formatting."""
import json, urllib.request, urllib.parse, http.client, uuid, csv, io

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
BASE = f'https://analyticsapi.zoho.com/restapi/v2/workspaces/{WS}'

# Table already exists
table_id = '2350577000032148135'
print(f"Using table: {table_id}")

# commission_fee rows added below in the rows list

# 2. Build CSV data
rows = [
    ('salesperson','1979954000002036262','B2B','','Mitch Merker - B2B dealer sales rep'),
    ('salesperson','1979954000044158860','B2B','','Serge Giguere - B2B dealer sales rep (Quebec)'),
    ('salesperson','1979954000047575788','Costco','','Costco Online orders'),
    ('salesperson','1979954000053988204','Costco','','Costco RoadShow events'),
    ('vendor','1979954000016532592','Retail','','Rolls Right Industries Ltd.'),
    ('vendor','1979954000033457005','Retail','','Canpar Express'),
    ('vendor','1979954000097951129','Retail','','Han-Lin Yong'),
    ('vendor','1979954000102131941','Retail','','City Business Brokerage LLC'),
    ('vendor','1979954000105760457','Retail','','Worldwide Express GlobalTranz and Unishippers'),
    ('vendor','1979954000117210664','Retail','','Hammad Mansoor'),
    ('vendor','1979954000123337029','Retail','','Bloom'),
    ('vendor','1979954000123962742','Retail','','Jason Avenido'),
    ('vendor','1979954000123962839','Retail','','David Burnett'),
    ('vendor','1979954000130643333','Retail','','Denis Charlebois'),
    ('vendor','1979954000131857648','Retail','','Amir Hossein Qaidzadeh'),
    ('costco_account','Discount - Costco Sales','Costco','','Costco promotional discount journals'),
    ('costco_account','Shipping, Freight -Costco','Costco','','Costco-specific inbound freight'),
    ('costco_account','Cost of Labour - Costco','Costco','','Labour costs specific to Costco'),
    ('costco_account','Sales of Product Income Costco','Costco','','Costco SKU revenue (unmatched only)'),
    ('costco_account','Cost of Goods Sold Costco','Costco','','Costco COGS (unmatched only)'),
    ('costco_account','Other Charges -Shipping Discount','Costco','','Shipping discount reclassification journals'),
    ('so_prefix','0089400','Costco','7','Costco SO prefix (match first 7 chars)'),
    ('so_prefix','SO-EB-','Retail','6','eBike BC SO prefix (match first 6 chars)'),
    ('so_prefix','SO-MB-','Retail','6','Moonbike SO prefix (match first 6 chars)'),
    ('default_channel','blank_sp_invoice','B2B','','Default for invoices with no salesperson'),
    ('default_channel','blank_sp_creditnote','Retail','','Default for credit notes with no salesperson'),
    ('default_channel','other_sp','Retail','','Default for non-mapped salespersons'),
    ('payroll_pct','Payroll Expense','B2B','0.306944','B2B weight 1105/3600'),
    ('payroll_pct','Payroll Expense','Retail','0.365278','Retail weight 1315/3600'),
    ('payroll_pct','Payroll Expense','Costco','0.077778','Costco weight 280/3600'),
    ('payroll_pct','Payroll Expense','Unallocated','0.250000','9 unallocated employees 900/3600'),
    ('payroll_pct','Payroll Expense:Taxes','B2B','0.306944',''),
    ('payroll_pct','Payroll Expense:Taxes','Retail','0.365278',''),
    ('payroll_pct','Payroll Expense:Taxes','Costco','0.077778',''),
    ('payroll_pct','Payroll Expense:Taxes','Unallocated','0.250000',''),
    ('payroll_pct','Payroll Expense:Wages','B2B','0.306944',''),
    ('payroll_pct','Payroll Expense:Wages','Retail','0.365278',''),
    ('payroll_pct','Payroll Expense:Wages','Costco','0.077778',''),
    ('payroll_pct','Payroll Expense:Wages','Unallocated','0.250000',''),
    ('payroll_pct','Salaries and Employee Wages','B2B','0.306944',''),
    ('payroll_pct','Salaries and Employee Wages','Retail','0.365278',''),
    ('payroll_pct','Salaries and Employee Wages','Costco','0.077778',''),
    ('payroll_pct','Salaries and Employee Wages','Unallocated','0.250000',''),
    ('payroll_pct','EHT Expense','B2B','0.306944',''),
    ('payroll_pct','EHT Expense','Retail','0.365278',''),
    ('payroll_pct','EHT Expense','Costco','0.077778',''),
    ('payroll_pct','EHT Expense','Unallocated','0.250000',''),
    ('payroll_pct','Work Safe BC Expense','B2B','0.306944',''),
    ('payroll_pct','Work Safe BC Expense','Retail','0.365278',''),
    ('payroll_pct','Work Safe BC Expense','Costco','0.077778',''),
    ('payroll_pct','Work Safe BC Expense','Unallocated','0.250000',''),
    ('payroll_pct','Payroll-SRED Wages Reimbursement','B2B','0.306944',''),
    ('payroll_pct','Payroll-SRED Wages Reimbursement','Retail','0.365278',''),
    ('payroll_pct','Payroll-SRED Wages Reimbursement','Costco','0.077778',''),
    ('payroll_pct','Payroll-SRED Wages Reimbursement','Unallocated','0.250000',''),
    ('ad_pct','Advertising','B2B','0.10','10% B2B / 90% Retail'),
    ('ad_pct','Advertising','Retail','0.90',''),
    ('ad_pct','Advertising And Marketing','B2B','0.10',''),
    ('ad_pct','Advertising And Marketing','Retail','0.90',''),
    ('ad_pct','Promotional','B2B','0.10',''),
    ('ad_pct','Promotional','Retail','0.90',''),
    ('payment_account','Stripe Fee','Retail','1.0','100% Retail'),
    ('payment_account','Stripe Fees','Retail','1.0',''),
    ('payment_account','Stripe Fees  US $','Retail','1.0','Two spaces before US'),
    ('payment_account','Card Fee','Retail','1.0',''),
    ('payment_account','Paypal charges','Retail','1.0',''),
    ('payment_account','QuickBooks Payments Fees','Retail','1.0',''),
    ('payment_account','QuickBooks Payments Fees ( 71 )','Retail','1.0',''),
    ('payment_account','Shipearly Fee','Retail','1.0',''),
    ('payment_account','Shopify Fee','Retail','1.0',''),
    ('payment_account','PayPlan Fee','Retail','1.0',''),
    ('payment_account','Amazon Fee charges','Retail','1.0',''),
    ('unalloc_opex','Exchange Gain or Loss','Unallocated','','OpEx kept 100% Unallocated'),
    ('unalloc_opex','Payroll-IRAP -WSBC - BCTech -ECO Wages Reimbursement','Unallocated','','IRAP grant reimbursement'),
    ('unalloc_opex','Payroll-IRAP Wages Reimbursement','Unallocated','','IRAP wage reimbursement'),
    ('unalloc_other_exp','SRED - Flex UL','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED - MUCEB - MTB','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED -CLESV','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED -Snow track','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED- ATMP','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED- Snowbike kit','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED-ATV','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED-CEBP','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED-Hydrofoil Electric Water Mobility','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED-IOT','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED-Light -e- Mobility Enclosure','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED-VEEMO','Unallocated','','SRED project'),
    ('unalloc_other_exp','SRED-eCity Bike','Unallocated','','SRED project'),
    ('unalloc_other_exp','CanExport','Unallocated','','Government export grant'),
    ('unalloc_other_exp','Security','Unallocated','','Security expense'),
    ('unalloc_other_exp','Exchange','Unallocated','','Foreign exchange gains/losses'),
    ('unalloc_other_exp','IRAP - B.I','Unallocated','','IRAP grant project'),
    ('unalloc_other_exp','IRAP - General','Unallocated','','IRAP grant project'),
    ('unalloc_other_exp','IRAP - eATV','Unallocated','','IRAP grant project'),
    ('unalloc_other_exp','Amortization','Unallocated','','Asset amortization'),
    ('unalloc_other_exp','Provisions for Income Tax','Unallocated','','Tax provision'),
    ('unalloc_other_exp','Penalties and settlements','Unallocated','','Legal/regulatory penalties'),
    ('unalloc_other_exp','Reconciliation Discrepancies','Unallocated','','Accounting adjustments'),
    ('cogs_unalloc','Subcontractors - COGS','Unallocated','','Adam Nunn - keep Unallocated'),
    ('cogs_unalloc','inventory_adjustment_by_quantity','Unallocated','','Entity type - stock adjustments'),
    ('commission_fee','Commissions and fees','B2B','','Revenue-based split B2B/Retail only (no Costco)'),
    ('commission_fee','Commissions and fees','Retail','','Revenue-based split B2B/Retail only (no Costco)'),
]

buf = io.StringIO()
writer = csv.writer(buf)
writer.writerow(['Type','Key','Channel','Value','Description'])
for r in rows:
    writer.writerow(r)
csv_data = buf.getvalue()

# 3. Import via multipart upload
boundary = uuid.uuid4().hex
parts = []
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="CONFIG"\r\n\r\n')
parts.append(json.dumps({'importType': 'APPEND', 'fileType': 'csv', 'autoIdentify': 'false', 'delimiter': '0', 'quoted': '2'}))
parts.append(f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="FILE"; filename="data.csv"\r\nContent-Type: text/csv\r\n\r\n')
parts.append(csv_data)
parts.append(f'\r\n--{boundary}--\r\n')
body = ''.join(parts).encode('utf-8')

conn = http.client.HTTPSConnection('analyticsapi.zoho.com')
conn.request('POST', f'/restapi/v2/workspaces/{WS}/views/{table_id}/data',
    body=body,
    headers={
        'ZANALYTICS-ORGID': ORG,
        'Authorization': f'Zoho-oauthtoken {TOKEN}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    })
resp = conn.getresponse()
result = resp.read().decode()
print(f'Import: {result[:500]}')
print(f'Total rows: {len(rows)}')
