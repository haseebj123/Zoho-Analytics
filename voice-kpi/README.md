# Voice KPI Reports

Reports built in the **Zoho Voice Analytics** workspace (`2350577000025614008`) to track agent performance on inbound calls.

## Reports

| File | Report Name | View ID | Description |
|------|-------------|---------|-------------|
| [01_kpi_voice_call_pickup_by_agent.md](01_kpi_voice_call_pickup_by_agent.md) | KPI Voice Call Pickup by Agent | `2350577000030633734` | Pickup rate per agent broken down by outcome category |
| [02_kpi_voice_missed_call_callback_tracker.md](02_kpi_voice_missed_call_callback_tracker.md) | KPI Voice Missed Call Callback Tracker | `2350577000030645441` | Per missed call: who called back and how long it took |

## Supporting Query Tables

| Table Name | View ID | Used By |
|------------|---------|---------|
| `KPI Voice Call Log` | `2350577000030636652` | Call Pickup report |
| `KPI Voice Outgoing Each` | `2350577000030642916` | Callback Tracker |
| `KPI Voice Missed Callback` | `2350577000030634199` | Callback Tracker |

## Source Tables (Zoho Voice sync)

| Table | Description |
|-------|-------------|
| `AgentMetrics` | One row per agent per call leg — includes CallType, Hangup Cause, Agent Called Time |
| `Agents` | Agent profiles — AgentId, Name |
| `CallLogs` | One row per call — Caller Number, Customer Number, StartTime, Missed Call Returned |

## Known Constraints

- `Destination Number` in CallLogs is NULL for outgoing calls — use `Customer Number` instead
- Zoho Analytics query tables do not support `GROUP BY` at the top level — wrap in a subquery
- Zoho Analytics query tables do not support JOIN inequality conditions (`>`, `<`) — use `CASE WHEN` in SELECT
- Columns from subquery-based query tables are prefixed with `sub.` (e.g. `sub.agent_name`)
- User filters on datetime columns only support `year` operation — `between`, `month`, `date_range` are not supported
