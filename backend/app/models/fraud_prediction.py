from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, Index
from ..database import Base


class FraudPrediction(Base):
    __tablename__ = "fraud_predictions"

    prediction_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=False)
    fraud_probability = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    top_risk_factors = Column(JSON)
    rule_triggers = Column(JSON)
    feature_vector = Column(JSON)
    shap_values = Column(JSON)
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_predictions_created_at", "created_at"),
        Index("ix_predictions_risk_level", "risk_level"),
    )


class AuditLog(Base):
    __tablename__ = "transaction_audit_logs"

    log_id = Column(String, primary_key=True)
    transaction_id = Column(String, nullable=False, index=True)
    prediction_id = Column(String, nullable=False)
    reviewer_id = Column(String)
    action = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    version_id = Column(String, primary_key=True)
    model_name = Column(String, nullable=False)
    artifact_path = Column(String)
    feature_schema = Column(JSON)
    training_auc = Column(Float)
    training_precision = Column(Float)
    training_recall = Column(Float)
    training_f1 = Column(Float)
    is_active = Column(Integer, default=0)
    trained_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class DriftEvent(Base):
    __tablename__ = "drift_events"

    drift_id = Column(String, primary_key=True)
    feature_name = Column(String, nullable=False)
    psi_score = Column(Float)
    baseline_mean = Column(Float)
    current_mean = Column(Float)
    drift_detected = Column(Integer, default=0)
    alert_level = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
