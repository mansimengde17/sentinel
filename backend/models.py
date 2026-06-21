from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# Pydantic schemas for API
class AlertPayload(BaseModel):
    """Incoming alert from PagerDuty/Sentry/Datadog."""

    source: str  # e.g., "datadog", "sentry", "custom"
    severity: Literal["critical", "high", "medium", "low"]
    message: str
    metadata: dict = {}
    timestamp: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "source": "datadog",
                "severity": "high",
                "message": "API response time > 2s for 5 min",
                "metadata": {"service": "checkout-api", "alert_id": "12345"},
            }
        }


class TriageDecision(BaseModel):
    """Decision made by the agent."""

    action: Literal["auto_resolve", "escalate", "needs_more_info"]
    confidence: float  # 0.0 to 1.0
    reasoning: str
    recommended_action: Optional[str] = None  # e.g., "restart_service"


class TriageResponse(BaseModel):
    """Response from the triage endpoint."""

    alert_id: str
    decision: TriageDecision
    trace: str  # Full Claude reasoning for dashboard display


# SQLAlchemy models
class TriageRecord(Base):
    """Persisted alert triage history."""

    __tablename__ = "triage_records"

    id = Column(Integer, primary_key=True)
    alert_id = Column(String, unique=True, nullable=False)
    source = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    metadata = Column(String, default="{}")  # JSON stringified

    action = Column(String, nullable=False)  # auto_resolve, escalate, needs_more_info
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    trace = Column(Text, nullable=False)  # Full Claude reasoning

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "source": self.source,
            "severity": self.severity,
            "message": self.message,
            "metadata": self.metadata,
            "action": self.action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "trace": self.trace,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
