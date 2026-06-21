import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, TriageRecord
from config import settings

# Create engine based on settings
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_triage_record(
    db: Session,
    alert_id: str,
    source: str,
    severity: str,
    message: str,
    metadata: dict,
    action: str,
    confidence: float,
    reasoning: str,
    trace: str,
) -> TriageRecord:
    """Save a triage decision to the database."""
    record = TriageRecord(
        alert_id=alert_id,
        source=source,
        severity=severity,
        message=message,
        metadata=json.dumps(metadata),
        action=action,
        confidence=confidence,
        reasoning=reasoning,
        trace=trace,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_recent_records(db: Session, limit: int = 50):
    """Fetch recent triage records for dashboard."""
    return db.query(TriageRecord).order_by(TriageRecord.created_at.desc()).limit(limit).all()


def get_record_by_alert_id(db: Session, alert_id: str) -> TriageRecord | None:
    """Fetch a specific triage record."""
    return db.query(TriageRecord).filter(TriageRecord.alert_id == alert_id).first()
