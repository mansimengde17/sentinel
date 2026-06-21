"""
Claude-based triage agent with tool use for mock remediation actions.
Note: Tool execution is simulated in code comments - see README for design rationale.
"""

import json
import logging
from typing import Literal
import anthropic
from config import settings

logger = logging.getLogger(__name__)

# Mock tool definitions - these simulate real infrastructure operations.
TOOLS = [
    {
        "name": "restart_service",
        "description": "Restart a failing service or container. [SIMULATED - logs only]",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service (e.g., 'checkout-api', 'notification-worker')",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the restart",
                },
            },
            "required": ["service_name", "reason"],
        },
    },
    {
        "name": "clear_queue",
        "description": "Clear a stuck message queue to unblock processing. [SIMULATED - logs only]",
        "input_schema": {
            "type": "object",
            "properties": {
                "queue_name": {
                    "type": "string",
                    "description": "Name of the queue (e.g., 'email-queue', 'batch-jobs')",
                },
                "max_items": {
                    "type": "integer",
                    "description": "Maximum items to clear (default 1000)",
                },
            },
            "required": ["queue_name"],
        },
    },
    {
        "name": "scale_replica_count",
        "description": "Scale up replicas for a deployment to handle load. [SIMULATED - logs only]",
        "input_schema": {
            "type": "object",
            "properties": {
                "deployment_name": {
                    "type": "string",
                    "description": "Name of the deployment (e.g., 'api-server')",
                },
                "target_replicas": {
                    "type": "integer",
                    "description": "Number of replicas to scale to",
                },
            },
            "required": ["deployment_name", "target_replicas"],
        },
    },
]

SYSTEM_PROMPT = """You are an operational alert triage agent. Your job is to classify incoming
infrastructure alerts and decide whether to auto-remediate or escalate to a human operator.

You have access to limited auto-remediation tools:
- restart_service: restart a failing service
- clear_queue: clear a stuck queue
- scale_replica_count: scale up replicas under load

CRITICAL: Only use a tool if you are VERY CONFIDENT (>80%) that it will fix the issue without risk.
Otherwise, recommend escalation to a human. Your confidence threshold is non-negotiable.

When analyzing an alert:
1. Understand the root cause from the alert message and metadata
2. Determine the appropriate action: auto_resolve, escalate, or needs_more_info
3. Provide a clear confidence score (0.0-1.0)
4. Explain your reasoning succinctly

Output format (after tool calls if any):
DECISION: <auto_resolve|escalate|needs_more_info>
CONFIDENCE: <0.0-1.0>
REASONING: <brief explanation>
RECOMMENDED_ACTION: <optional action if auto_resolve>"""


def _process_tool_call(tool_name: str, tool_input: dict) -> str:
    """
    Process a tool call. This is SIMULATED - in production would call real APIs.
    See README: "What this agent does NOT do" section.
    """
    logger.info(f"[SIMULATED TOOL CALL] {tool_name}({tool_input})")

    # Simulate tool success
    if tool_name == "restart_service":
        service = tool_input.get("service_name", "unknown")
        return json.dumps({
            "status": "success",
            "message": f"Service '{service}' restart initiated (SIMULATED)",
            "note": "In production, this would execute: kubectl restart deployment {service}",
        })
    elif tool_name == "clear_queue":
        queue = tool_input.get("queue_name", "unknown")
        return json.dumps({
            "status": "success",
            "message": f"Queue '{queue}' cleared (SIMULATED)",
            "items_removed": 0,
            "note": "In production, this would drain the message queue",
        })
    elif tool_name == "scale_replica_count":
        deployment = tool_input.get("deployment_name", "unknown")
        replicas = tool_input.get("target_replicas", 1)
        return json.dumps({
            "status": "success",
            "message": f"Scaling '{deployment}' to {replicas} replicas (SIMULATED)",
            "previous_replicas": 1,
            "note": "In production: kubectl scale deployment {deployment} --replicas={replicas}",
        })
    else:
        return json.dumps({"status": "error", "message": f"Unknown tool: {tool_name}"})


def parse_decision(response_text: str) -> tuple[str, float, str, str | None]:
    """
    Parse agent response to extract decision, confidence, reasoning, and recommended action.
    Returns: (action, confidence, reasoning, recommended_action)
    """
    lines = response_text.strip().split("\n")
    action = "needs_more_info"
    confidence = 0.0
    reasoning = ""
    recommended_action = None

    for line in lines:
        if line.startswith("DECISION:"):
            action = line.replace("DECISION:", "").strip().lower()
        elif line.startswith("CONFIDENCE:"):
            try:
                confidence = float(line.replace("CONFIDENCE:", "").strip())
            except ValueError:
                confidence = 0.0
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()
        elif line.startswith("RECOMMENDED_ACTION:"):
            recommended_action = line.replace("RECOMMENDED_ACTION:", "").strip()

    return action, confidence, reasoning, recommended_action


async def triage_alert(alert_source: str, severity: str, message: str, metadata: dict) -> dict:
    """
    Analyze an alert using Claude and return a triage decision.

    Returns:
        {
            "action": "auto_resolve" | "escalate" | "needs_more_info",
            "confidence": float,
            "reasoning": str,
            "recommended_action": str | None,
            "trace": str,  # Full Claude reasoning for audit trail
        }
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    user_message = f"""Alert from {alert_source}:
Severity: {severity}
Message: {message}
Metadata: {json.dumps(metadata)}

Please analyze this alert and decide the appropriate action."""

    try:
        # Call Claude with tool use enabled
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            tools=TOOLS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            timeout=settings.request_timeout_seconds,
        )

        # Process tool calls if any
        tool_results = []
        trace = ""
        action = "needs_more_info"
        confidence = 0.0
        reasoning = ""
        recommended_action = None

        # Collect all response content for trace
        for block in response.content:
            if hasattr(block, "text"):
                trace += block.text + "\n"

        # Handle tool use
        if response.stop_reason == "tool_use":
            # Process tool calls and run agentic loop
            messages = [{"role": "user", "content": user_message}]
            messages.append({"role": "assistant", "content": response.content})

            for block in response.content:
                if block.type == "tool_use":
                    tool_result = _process_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result,
                    })

            # Continue conversation with tool results
            messages.append({"role": "user", "content": tool_results})

            final_response = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
                timeout=settings.request_timeout_seconds,
            )

            # Parse final decision
            for block in final_response.content:
                if hasattr(block, "text"):
                    trace += "\n[FINAL DECISION]\n" + block.text
                    action, confidence, reasoning, recommended_action = parse_decision(block.text)

        else:
            # No tool use, parse decision from initial response
            for block in response.content:
                if hasattr(block, "text"):
                    action, confidence, reasoning, recommended_action = parse_decision(block.text)

        # Apply confidence threshold: if below threshold, always escalate
        if confidence < settings.confidence_threshold and action != "escalate":
            logger.warning(
                f"Confidence {confidence} below threshold {settings.confidence_threshold}. "
                f"Escalating to human despite {action} recommendation."
            )
            action = "escalate"
            reasoning += (
                f" [ESCALATED: confidence {confidence} below threshold "
                f"{settings.confidence_threshold}]"
            )

        return {
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "recommended_action": recommended_action,
            "trace": trace.strip(),
        }

    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        # Graceful degradation: escalate on API failure
        return {
            "action": "escalate",
            "confidence": 0.0,
            "reasoning": f"API error contacting Claude: {str(e)}. Escalating to human for manual triage.",
            "recommended_action": None,
            "trace": f"ERROR: {str(e)}",
        }
