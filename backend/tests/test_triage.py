"""
Tests for the triage agent and decision logic.
"""

import pytest
from unittest.mock import patch, MagicMock
from agent import parse_decision, triage_alert


def test_parse_decision_basic():
    """Test parsing a well-formed decision string."""
    response = """
    DECISION: auto_resolve
    CONFIDENCE: 0.92
    REASONING: Service health check passed after restart.
    RECOMMENDED_ACTION: restart_service
    """
    action, confidence, reasoning, recommended = parse_decision(response)

    assert action == "auto_resolve"
    assert confidence == 0.92
    assert "health check" in reasoning
    assert recommended == "restart_service"


def test_parse_decision_escalate():
    """Test parsing an escalation decision."""
    response = """
    DECISION: escalate
    CONFIDENCE: 0.45
    REASONING: Multiple services affected; needs human investigation.
    """
    action, confidence, reasoning, _ = parse_decision(response)

    assert action == "escalate"
    assert confidence == 0.45


def test_parse_decision_needs_more_info():
    """Test parsing a needs-more-info decision."""
    response = """
    DECISION: needs_more_info
    CONFIDENCE: 0.55
    REASONING: Insufficient context to determine root cause.
    """
    action, confidence, reasoning, _ = parse_decision(response)

    assert action == "needs_more_info"
    assert confidence == 0.55


def test_parse_decision_invalid_confidence():
    """Test graceful handling of invalid confidence value."""
    response = """
    DECISION: auto_resolve
    CONFIDENCE: not_a_number
    REASONING: Test
    """
    action, confidence, reasoning, _ = parse_decision(response)

    assert action == "auto_resolve"
    assert confidence == 0.0  # Falls back to 0.0


@pytest.mark.asyncio
async def test_triage_alert_api_error_escalates():
    """Test that API errors gracefully escalate to human."""
    with patch("agent.anthropic.Anthropic") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        # Simulate API error
        from anthropic import APIError

        mock_instance.messages.create.side_effect = APIError("API timeout")

        result = await triage_alert("test", "critical", "Test message", {})

        assert result["action"] == "escalate"
        assert result["confidence"] == 0.0
        assert "API error" in result["reasoning"]


@pytest.mark.asyncio
async def test_triage_alert_below_confidence_threshold_escalates():
    """Test that low confidence decisions are escalated."""
    with patch("agent.anthropic.Anthropic") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        # Mock response with low confidence auto_resolve
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [
            MagicMock(
                type="text",
                text="""
                DECISION: auto_resolve
                CONFIDENCE: 0.5
                REASONING: Might work.
                """,
            )
        ]
        mock_instance.messages.create.return_value = mock_response

        result = await triage_alert("test", "high", "Test message", {})

        # Should be escalated due to low confidence
        assert result["action"] == "escalate"
        # Note: actual confidence would be 0.5, but escalation reason is added
        assert "below threshold" in result["reasoning"]


def test_confidence_threshold_logic():
    """
    Verify that the confidence threshold (default 0.75) is properly applied.
    This test documents the safety mechanism for production use.
    """
    from config import settings

    assert settings.confidence_threshold == 0.75
    # Any decision with confidence < 0.75 should trigger escalation
    # This is enforced in triage_alert() function
