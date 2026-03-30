# KPI: Voice Missed Call Callback Tracker

## Overview
For every missed inbound call, shows whether the customer was called back, how many minutes it took, and which agent made the callback — either by calling the customer outbound, or by answering when the customer called back in. Helps identify how quickly the team responds to missed calls and holds individual agents accountable.

## Workspace
**Zoho Voice Analytics** — Workspace ID: `2350577000025614008`

## Views

### Query Table 0: `KPI Voice Outgoing Agent Map`
**View ID:** `2350577000030853035`

Pre-expands the `AgentMetrics` outgoing rows by duplicating each row at 11 different timestamps (the original `Agent Called Time` plus offsets of 1 through 10 seconds). This allows a downstream equality JOIN on `StartTime` to match even when the two systems record the same call with a slight timestamp difference.

#### SQL
```sql
SELECT sub.out_time, sub.agent_name FROM (
  SELECT a.`Agent Called Time` AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 1 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 2 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 3 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 4 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 5 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 6 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 7 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 8 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 9 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
  UNION ALL
  SELECT DATE_ADD(a.`Agent Called Time`, INTERVAL 10 SECOND) AS out_time, ag.`Name` AS agent_name
  FROM `AgentMetrics` a LEFT JOIN `Agents` ag ON a.`Agent` = ag.`AgentId`
  WHERE a.`CallType` = 'outgoing' AND a.`Agent` IS NOT NULL AND a.`Agent` != ''
) sub
```

#### Why 11 UNION ALL branches (INTERVAL 0 through INTERVAL 10 SECOND)?
`AgentMetrics.Agent Called Time` is consistently recorded a few seconds **before** `CallLogs.StartTime` for the same outgoing call. The offset is not fixed — it varies from 1 to 8+ seconds depending on the call. Zoho Analytics does not support inequality JOIN conditions (`>`, `<`, `BETWEEN`) — attempting them produces error 7410. A range-based join is therefore impossible. The workaround is to pre-expand each agent row into 11 copies, each shifted by one additional second (0–10), so that an equality JOIN on `StartTime` can match whichever offset applies to a given call.

---

### Query Table 1: `KPI Voice Outgoing Each`
**View ID:** `2350577000030851132`

One row per outgoing call with the customer number and agent name. Used as the outbound callback lookup source.

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

### Query Table 2: `KPI Voice Incoming Answered Each`
**View ID:** `2350577000030860002`

One row per answered incoming call with the customer number and agent name. Used as the inbound callback lookup source — captures cases where a customer calls back in after a miss and an agent answers.

#### SQL
```sql
SELECT sub.log_id, sub.customer_number, sub.in_time, sub.agent_name FROM (
  SELECT cl.`Log Id` AS log_id, MAX(cl.`Customer Number`) AS customer_number,
         MAX(cl.`StartTime`) AS in_time,
         GROUP_CONCAT(DISTINCT ag.`Name` ORDER BY ag.`Name` SEPARATOR ', ') AS agent_name
  FROM `CallLogs` cl
  LEFT JOIN `AgentMetrics` am ON cl.`Log Id` = am.`CallLog UniqueID`
  LEFT JOIN `Agents` ag ON am.`Agent` = ag.`AgentId`
  WHERE cl.`CallType` = 'incoming' AND cl.`Customer Number` IS NOT NULL AND cl.`Customer Number` != ''
    AND am.`Hangup Cause` = 'answered'
  GROUP BY cl.`Log Id`
) sub
```

#### Why a separate table for incoming answered calls?
A missed call is "returned" not only when an agent calls the customer back outbound, but also when the customer calls in again and an agent answers. This table isolates those answered incoming calls so they can be joined into the callback tracker alongside outgoing calls.

---

### Query Table 3: `KPI Voice Missed Callback`
**View ID:** `2350577000030851246`

Cross-joins each missed call against every outgoing call AND every answered incoming call to the same customer number. `mins_to_callback` is NULL when the matching call occurred before the missed call, and a positive integer when it occurred after. A `call_direction` column distinguishes whether the callback was outbound (agent called the customer) or inbound (customer called back and was answered). The summary table uses `MIN(mins_to_callback)` to find the time to first callback after each specific miss.

#### SQL
```sql
SELECT cl.`Log Id` AS missed_id, cl.`Customer Number` AS customer_number,
       cl.`StartTime` AS missed_at, YEAR(cl.`StartTime`) AS yr, MONTH(cl.`StartTime`) AS mth,
       cl.`Missed Call Returned` AS was_returned,
       oc.`sub.out_time` AS out_time,
       oc.`sub.agent_name` AS callback_agent,
       CASE WHEN oc.`sub.out_time` > cl.`StartTime`
            THEN TIMESTAMPDIFF(MINUTE, cl.`StartTime`, oc.`sub.out_time`)
            ELSE NULL END AS mins_to_callback,
       'outgoing' AS call_direction
FROM `CallLogs` cl
LEFT JOIN `KPI Voice Outgoing Each` oc ON cl.`Customer Number` = oc.`sub.customer_number`
WHERE cl.`CallType` = 'missed' AND cl.`Customer Number` IS NOT NULL AND cl.`Customer Number` != ''
UNION ALL
SELECT cl.`Log Id` AS missed_id, cl.`Customer Number` AS customer_number,
       cl.`StartTime` AS missed_at, YEAR(cl.`StartTime`) AS yr, MONTH(cl.`StartTime`) AS mth,
       cl.`Missed Call Returned` AS was_returned,
       ic.`sub.in_time` AS out_time,
       ic.`sub.agent_name` AS callback_agent,
       CASE WHEN ic.`sub.in_time` > cl.`StartTime`
            THEN TIMESTAMPDIFF(MINUTE, cl.`StartTime`, ic.`sub.in_time`)
            ELSE NULL END AS mins_to_callback,
       'incoming' AS call_direction
FROM `CallLogs` cl
LEFT JOIN `KPI Voice Incoming Answered Each` ic ON cl.`Customer Number` = ic.`sub.customer_number`
WHERE cl.`CallType` = 'missed' AND cl.`Customer Number` IS NOT NULL AND cl.`Customer Number` != ''
```

#### Key Design Decisions

**Why a UNION instead of a single join?**
Callbacks can happen in two directions: the agent calls the customer (outgoing) or the customer calls back and gets answered (incoming). A UNION keeps the logic for each direction clean and separate, and allows the `call_direction` column to distinguish them downstream.

**Why a cross-join instead of MIN in the lookup table?**
An earlier version stored `MIN(StartTime)` per customer in the lookup. This broke when a customer had previously been called by the team before a later missed call — the historical MIN was older than the miss, so no match was found. Storing individual rows and using `CASE WHEN` ensures pre-miss calls produce NULL, which MIN ignores.

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
| `out_time` | DateTime | Timestamp of an outgoing or answered incoming call to this customer |
| `callback_agent` | Text | Agent who made the outgoing call or answered the incoming call |
| `mins_to_callback` | Number | Minutes from miss to matching call (NULL = call was before the miss) |
| `call_direction` | Text | `'outgoing'` if agent called the customer; `'incoming'` if customer called back and was answered |

---

### Query Table 4: `KPI Voice Callback Summary`
**View ID:** `2350577000030846189`

Collapses the `KPI Voice Missed Callback` cross-join back to one row per missed call. `MIN(mins_to_callback)` gives the time to the first callback. `GROUP_CONCAT` produces a combined `all_agents` string that prefixes `incoming: ` for any agent who answered a customer-initiated callback, so the direction is visible in the final pivot.

#### SQL
```sql
SELECT sub.missed_id, sub.customer_number, sub.missed_at, sub.yr, sub.mth,
       sub.was_returned, sub.all_agents, sub.mins_to_callback FROM (
  SELECT mc.missed_id AS missed_id, MAX(mc.customer_number) AS customer_number,
         MAX(mc.missed_at) AS missed_at, MAX(mc.yr) AS yr, MAX(mc.mth) AS mth,
         MAX(mc.was_returned) AS was_returned,
         GROUP_CONCAT(DISTINCT
           CASE WHEN mc.call_direction = 'incoming'
                THEN CONCAT('incoming: ', mc.callback_agent)
                ELSE mc.callback_agent
           END
           ORDER BY mc.mins_to_callback SEPARATOR ', ') AS all_agents,
         MIN(mc.mins_to_callback) AS mins_to_callback
  FROM `KPI Voice Missed Callback` mc GROUP BY mc.missed_id
) sub
```

#### How `all_agents` is formatted

| Scenario | Example value |
|----------|---------------|
| Agent called customer back outbound | `Valeriia` |
| Customer called back in, agent answered | `incoming: Noor` |
| Both happened | `Valeriia, incoming: Noor` |

Agents listed without a prefix called the customer outbound. Agents prefixed with `incoming:` answered when the customer called back in.

#### Columns

| Column | Type | Description |
|--------|------|-------------|
| `missed_id` | Text | UUID of the missed call |
| `customer_number` | Text | Customer phone number |
| `missed_at` | DateTime | When the call was missed |
| `yr` / `mth` | Number | Year and month integers for filtering |
| `was_returned` | Text | Zoho Voice native flag (`true`/`false`) |
| `all_agents` | Text | Comma-separated agent names (outbound agents by name only; inbound answerers prefixed with `incoming: `) |
| `mins_to_callback` | Number | Minutes from miss to first callback (NULL = no callback found after the miss) |

---

### Pivot Report: `KPI Voice Missed Call Callback Tracker`
**View ID:** `2350577000030857010`
**Base Table:** `KPI Voice Callback Summary`

| Axis | Column | Operation |
|------|--------|-----------|
| Row | `customer_number` | Actual |
| Row | `missed_id` | Actual |
| Data | `mins_to_callback` | MIN |
| Data | `all_agents` | Actual |
| Data | `was_returned` | Actual |
| User Filter | `missed_at` | Year |

Each row in the pivot is one missed call. `MIN(mins_to_callback)` reflects the time to the first callback (outgoing or incoming) after that specific miss. `all_agents` shows who was involved, with direction indicated by the `incoming: ` prefix.

#### How to Read the Report

| Value | Meaning |
|-------|---------|
| `mins_to_callback = NULL` | No callback was made or answered after the miss |
| `mins_to_callback = 0–60` | First callback within one hour |
| `all_agents = "Valeriia"` | Agent Valeriia called the customer back outbound |
| `all_agents = "incoming: Noor"` | Customer called back and Noor answered |
| `all_agents = "Valeriia, incoming: Noor"` | Both happened; Valeriia called outbound and Noor answered inbound |
| `was_returned = true` | Zoho Voice also flagged this as returned |

#### Recommended Manual Steps (UI only)
1. Add **conditional formatting**: highlight rows where `mins_to_callback` is NULL in red (never called back)
2. Add a **chart version** with a reference line at 60 minutes (1-hour callback SLA)
3. Add a **callback rate** column formula: count of rows where `mins_to_callback IS NOT NULL` / total missed calls

## Data Flow

```
CallLogs (CallType = 'missed')
         |                    \
         | JOIN ON             \ JOIN ON
         | Customer Number =    \ Customer Number =
         | sub.customer_number   \ sub.customer_number
         |                        \
KPI Voice Outgoing Each    KPI Voice Incoming Answered Each
(agent called customer)    (customer called back, answered)
         |                        |
         +-------UNION ALL--------+
                          |
               KPI Voice Missed Callback
       (one row per missed x outgoing/incoming pair)
       call_direction = 'outgoing' | 'incoming'
                          |
              CASE WHEN out_time > missed_at
              THEN TIMESTAMPDIFF(MINUTE, ...)
              ELSE NULL
                          |
            KPI Voice Callback Summary
     GROUP BY missed_id, MIN(mins_to_callback)
     GROUP_CONCAT with 'incoming: ' prefix for inbound
                          |
         Pivot: MIN(mins_to_callback), all_agents
         = minutes to first callback + who handled it
```

## Known Issues / Design Decisions

### Timestamp offset between AgentMetrics and CallLogs for outgoing calls

`AgentMetrics.Agent Called Time` is consistently recorded a few seconds **before** `CallLogs.StartTime` for the same outgoing call. The offset is not fixed — the observed range is 1–8+ seconds and varies per call. This means a simple equality JOIN between `AgentMetrics.Agent Called Time` and `CallLogs.StartTime` will miss most outgoing calls entirely.

Zoho Analytics does not support inequality JOIN conditions (`>`, `<`, `BETWEEN`) in query tables — attempting them returns error 7410. A range-based join (e.g. `JOIN ON StartTime BETWEEN Agent Called Time AND DATE_ADD(Agent Called Time, INTERVAL 10 SECOND)`) is therefore impossible.

**Workaround — pre-expand with UNION ALL:** The `KPI Voice Outgoing Agent Map` query table duplicates every outgoing agent row 11 times, once at the original `Agent Called Time` and once more for each additional second from +1 through +10. This means that for any given call, at least one of those 11 rows will have an `out_time` that matches `CallLogs.StartTime` exactly, allowing the downstream equality JOIN to succeed regardless of which specific offset applies to that call.
