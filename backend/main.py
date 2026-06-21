"""
Sentinel: AI agent for operational alert triage
FastAPI backend handling Claude integration and decision persistence
"""

import logging
import os
import uuid
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from models import AlertPayload, TriageResponse, TriageDecision
from database import init_db, get_db, save_triage_record, get_recent_records, get_record_by_alert_id
from agent import triage_alert
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Sentinel Alert Triage",
    description="AI-powered operational alert triage with Claude",
    version="1.0.0",
)

# CORS — allows dashboard to call the API from any origin (HF Spaces, localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logger.info(f"Database initialized: {settings.database_url}")
    logger.info(f"Confidence threshold: {settings.confidence_threshold}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": settings.anthropic_model,
        "confidence_threshold": settings.confidence_threshold,
    }


@app.post("/triage", response_model=TriageResponse)
async def triage_endpoint(alert: AlertPayload, db: Session = Depends(get_db)):
    """
    Receive an alert and triage it using Claude.

    The agent will:
    1. Analyze the alert severity, message, and metadata
    2. Decide: auto_resolve, escalate, or needs_more_info
    3. Optionally call tools for mock remediation
    4. Persist the full decision trace for audit trail

    Returns the decision and full reasoning for dashboard display.
    """
    # Generate unique alert ID if not provided
    alert_id = str(uuid.uuid4())

    logger.info(f"Processing alert {alert_id}: {alert.source} - {alert.severity}")

    try:
        # Call the Claude-based triage agent
        result = await triage_alert(
            alert_source=alert.source,
            severity=alert.severity,
            message=alert.message,
            metadata=alert.metadata,
        )

        # Create decision object
        decision = TriageDecision(
            action=result["action"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            recommended_action=result.get("recommended_action"),
        )

        # Persist to database
        record = save_triage_record(
            db=db,
            alert_id=alert_id,
            source=alert.source,
            severity=alert.severity,
            message=alert.message,
            metadata=alert.metadata,
            action=decision.action,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            trace=result["trace"],
        )

        logger.info(f"Triage complete for {alert_id}: {decision.action} (confidence: {decision.confidence})")

        return TriageResponse(
            alert_id=alert_id,
            decision=decision,
            trace=result["trace"],
        )

    except Exception as e:
        logger.error(f"Error triaging alert {alert_id}: {e}", exc_info=True)
        # Return 500 but include error in response so n8n can handle it
        raise HTTPException(
            status_code=500,
            detail=f"Triage processing failed: {str(e)}",
        )


@app.get("/alerts")
async def get_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """
    Fetch recent triage records for the dashboard.
    Returns latest alerts with their decisions and reasoning.
    """
    records = get_recent_records(db, limit=limit)
    return {
        "total": len(records),
        "alerts": [record.to_dict() for record in records],
    }


@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Fetch a specific alert and its triage decision."""
    record = get_record_by_alert_id(db, alert_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return record.to_dict()


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get summary statistics on triage decisions."""
    records = get_recent_records(db, limit=1000)

    if not records:
        return {
            "total_alerts": 0,
            "auto_resolve_count": 0,
            "escalate_count": 0,
            "needs_more_info_count": 0,
            "avg_confidence": 0.0,
        }

    auto_resolve = sum(1 for r in records if r.action == "auto_resolve")
    escalate = sum(1 for r in records if r.action == "escalate")
    needs_info = sum(1 for r in records if r.action == "needs_more_info")
    avg_confidence = sum(r.confidence for r in records) / len(records)

    return {
        "total_alerts": len(records),
        "auto_resolve_count": auto_resolve,
        "escalate_count": escalate,
        "needs_more_info_count": needs_info,
        "avg_confidence": round(avg_confidence, 3),
    }


# Serve the dashboard as static files when running on HF Spaces (or Docker)
# The static/ directory is created by the HF Dockerfile (copies dashboard/ there)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/dashboard", StaticFiles(directory=_static_dir, html=True), name="dashboard")

    @app.get("/")
    async def serve_dashboard():
        return FileResponse(os.path.join(_static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
