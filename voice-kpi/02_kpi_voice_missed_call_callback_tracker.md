# KPI: Voice Missed Call Callback Tracker

## Overview
For every missed inbound call, shows whether the customer was called back, how many minutes it took, and which agent made the callback. Helps identify how quickly the team responds to missed calls and holds individual agents accountable.

## Workspace
**Zoho Voice Analytics** — Workspace ID: `2350577000025614008`

## Views

### Query Table 1: `KPI Voice Outgoing Each`
**View ID:** `2350577000030642916`

One row per outgoing call with the customer number and agent name. Used as the callback lookup source.

#### SQL
```sql
SELECT
  sub.log_id,
  sub.customer_number,
  sub.out_time,
  sub.agent_name
FROM (
  SELECT
    a.`CallLog UniqueID`        AS log_id,
    MAX(cl.`Customer Number`)   AS customer_number,
    MAX(a.`Agent Called Time`)  AS out_time,
    MAX(ag.`Name`)              AS agent_name
  FROM `AgentMetrics` a
  LEFT JOIN `Agents`   ag ON a.`Agent`            = ag.`AgentId`
  LEFT JOIN `CallLogs` cl ON a.`CallLog UniqueID` = cl.`Log Id`
  WHERE a.`CallType` = 'outgoing'
    AND a.`Agent` IS NOT NULL
    AND a.`Agent` != ''
  GROUP BY a.`CallLog UniqueID`, a.`Agent`
) sub
```

#### Why `Customer Number` (not `Destination Number`)
`Destination Number` in `CallLogs` is NULL for outgoing calls. Zoho Voice does not populate it for agent-initiated calls. `Customer Number` is populated for all call types (incoming, outgoing, missed) and always represents the external customer number.

---

### Query Table 2: `KPI Voice Missed Callback`
**View ID:** `2350577000030634199`

Cross-joins each missed call against every outgoing call to the same customer number. `mins_to_callback` is NULL when the outgoing call occurred before the missed call, and a positive integer when it occurred after. The pivot uses `MIN(mins_to_callback)` to find the time to first callback after each specific miss.

#### SQL
```sql
SELECT
  cl.`Log Id`                   AS missed_id,
  cl.`Customer Number`          AS customer_number,
  cl.`StartTime`                AS missed_at,
  YEAR(cl.`StartTime`)          AS yr,
  MONTH(cl.`StartTime`)         AS mth,
  cl.`Missed Call Returned`     AS was_returned,
  oc.`sub.out_time`             AS out_time,
  oc.`sub.agent_name`           AS callback_agent,
  CASE
    WHEN oc.`sub.out_time` > cl.`StartTime`
    THEN TIMESTAMPDIFF(MINUTE, cl.`StartTime`, oc.`sub.out_time`)
    ELSE NULL
  END                           AS mins_to_callback
FROM `CallLogs` cl
LEFT JOIN `KPI Voice Outgoing Each` oc
       ON cl.`Customer Number` = oc.`sub.customer_number`
WHERE cl.`CallType` = 'missed'
  AND cl.`Customer Number` IS NOT NULL
  AND cl.`Customer Number` != ''
```

#### Key Design Decisions

**Why a cross-join instead of MIN in the lookup table?**
An earlier version stored `MIN(StartTime)` per customer in the lookup. This broke when a customer had previously been called by the team before a later missed call — the historical MIN was older than the miss, so no match was found. Storing individual outgoing rows and using `CASE WHEN` ensures pre-miss calls produce NULL, which MIN ignores.

**Why CASE WHEN instead of a JOIN inequality condition?**
Zoho Analytics query tables do not support `>` or `<` operators in JOIN conditions (error 7410). The CASE WHEN approach inside the SELECT achieves equivalent filtering without requiring an inequality JOIN.

#### Columns

| Column | Type | Description |
|--------|------|-------------|
| `missed_id` | Text | UUID of the missed call (matches Zoho Voice Log Detail) |
| `customer_number` | Text | Customer phone number |
| `missed_at` | DateTime | When the call was missed |
| `yr` / `mth` | Number | Year and month integers for filtering |
| `was_returned` | Text | Zoho Voice native flag (`true`/`false`) |
| `out_time` | DateTime | Timestamp of an outgoing call to this customer |
| `callback_agent` | Text | Agent who made that outgoing call |
| `mins_to_callback` | Number | Minutes from miss to outgoing call (NULL = call was before the miss) |

---

### Pivot Report: `KPI Voice Missed Call Callback Tracker`
**View ID:** `2350577000030645441`
**Base Table:** `KPI Voice Missed Callback`

| Axis | Column | Operation |
|------|--------|-----------|
| Row | `customer_number` | Actual |
| Row | `missed_id` | Actual |
| Data | `mins_to_callback` | MIN |
| Data | `callback_agent` | Actual |
| Data | `was_returned` | Actual |
| User Filter | `missed_at` | Year |

Each row in the pivot is one missed call. `MIN(mins_to_callback)` collapses the cross-join back to a single value — the time to the first callback after that specific miss.

#### How to Read the Report

| Value | Meaning |
|-------|---------|
| `mins_to_callback = NULL` | No outgoing call was made to this customer after the miss |
| `mins_to_callback = 0–60` | Called back within one hour |
| `callback_agent` populated | Agent who made the first callback |
| `was_returned = true` | Zoho Voice also flagged this as returned |

#### Recommended Manual Steps (UI only)
1. Add **conditional formatting**: highlight rows where `mins_to_callback` is NULL in red (never called back)
2. Add a **chart version** with a reference line at 60 minutes (1-hour callback SLA)
3. Add a **callback rate** column formula: count of rows where `mins_to_callback IS NOT NULL` / total missed calls

## Data Flow

```
CallLogs (CallType = 'missed')     KPI Voice Outgoing Each
         |                                  |
         | JOIN ON                          |
         | Customer Number =                |
         | sub.customer_number              |
         +----------------------------------+
                          |
               KPI Voice Missed Callback
         (one row per missed x outgoing pair)
                          |
              CASE WHEN out_time > missed_at
              THEN TIMESTAMPDIFF(MINUTE, ...)
              ELSE NULL
                          |
              Pivot: MIN(mins_to_callback)
              = minutes to first callback after the miss
```
