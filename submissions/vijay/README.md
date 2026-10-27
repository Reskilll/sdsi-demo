# SOC alert triage agent

This dependency-free Python agent triages a JSON alert queue. It assigns a
severity with a stated reason, groups alerts with a shared incident ID (or a
matching asset and configured indicator family), and flags alerts at or above
the `high` threshold for a human analyst.

Alert text is treated only as untrusted evidence. The agent does not execute
content, follow instructions found in alerts, or take response actions.
Severity is rule-based and is not a substitute for analyst judgment.

## Run

Provide a JSON object with an `alerts` array through standard input or a file:

```json
{
  "alerts": [
    {
      "id": "a-101",
      "incident_id": "inc-7",
      "asset": "workstation-12",
      "title": "Possible ransomware activity",
      "description": "Unusual file changes observed"
    },
    {
      "id": "a-102",
      "incident_id": "inc-7",
      "asset": "workstation-12",
      "title": "Multiple failed logins",
      "description": "Review the account activity"
    }
  ]
}
```

```powershell
python submissions\vijay\agent.py alerts.json
Get-Content alerts.json | python submissions\vijay\agent.py
```

The threshold can be set to `low`, `medium`, `high`, or `critical` using
`escalation_threshold`. Output includes per-alert severity and rationale,
groups, and a human-review escalation list. Invalid JSON or input shapes are
reported as errors.

## Test

```powershell
python -m unittest discover -s submissions\vijay -p "test_*.py"
```
