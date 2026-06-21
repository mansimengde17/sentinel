# Sentinel Triage Node

**n8n custom node for AI-powered operational alert triage**

## Overview

The Sentinel Triage node integrates with the Sentinel backend service to classify incoming operational alerts (from Datadog, Sentry, PagerDuty, etc.) and decide whether to auto-remediate or escalate to humans.

## Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| **Alert Source** | String | Yes | Name of the alert source (e.g., `datadog`, `sentry`, `pagerduty`, `custom`) |
| **Severity** | Select | Yes | Alert urgency level: `critical`, `high`, `medium`, or `low` |
| **Message** | String | Yes | Alert message/description (supports multi-line) |
| **Metadata** | JSON | No | Additional context as valid JSON object (e.g., `{"service": "api", "region": "us-east"}`) |

## Outputs

The node returns the Sentinel backend's decision object:

```json
{
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "decision": {
    "action": "auto_resolve|escalate|needs_more_info",
    "confidence": 0.87,
    "reasoning": "Human-readable explanation of the decision",
    "recommended_action": "restart_service"
  },
  "trace": "Full Claude reasoning for audit trail"
}
```

### Action Types

- **`auto_resolve`**: Agent is confident (≥confidence threshold) that it can fix this automatically
- **`escalate`**: Alert should be reviewed by a human operator
- **`needs_more_info`**: Additional context is required before a decision can be made

### Confidence Score

Score from 0.0 to 1.0 indicating the agent's confidence in its decision.
**Safety mechanism**: Regardless of the action, if confidence falls below the configured threshold (default: 0.75), the decision is automatically escalated to a human.

## Configuration

1. Create a **Sentinel API** credential with:
   - **API Key**: Optional (for future auth enhancement)
   - **Backend URL**: URL of the Sentinel FastAPI service (e.g., `http://localhost:8000`)

2. Add the Sentinel Triage node to your workflow
3. Map your alert fields to the node's inputs
4. Connect downstream nodes to handle each action type

## Example Workflow

```
Webhook (receive alert) 
  ↓
Sentinel Triage (classify & decide)
  ↓
Router (by action)
  ├→ auto_resolve: Log + notify
  ├→ escalate: Send to PagerDuty/Slack
  └→ needs_more_info: Queue for manual review
```

## Error Handling

If the Sentinel backend is unreachable or returns an error:
- The node will throw an error and halt the workflow (default)
- Enable **"Continue on Fail"** to return an error object and continue

## See Also

- [Sentinel Backend README](../../README.md) — Architecture, design decisions, deployment
- [Sentinel Project Root](../../README.md) — Full setup and demo instructions
