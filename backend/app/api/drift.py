"""Drift detection endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.fraud_prediction import FraudPrediction, DriftEvent
from ..services.drift_detection_service import DriftDetectionService
from ..services.monitoring_service import MonitoringService

router = APIRouter(prefix="/drift", tags=["drift"])


@router.get("/report")
async def drift_report(request: Request, db: Session = Depends(get_db)):
    """Runs PSI drift analysis on recent predictions vs. baseline."""
    monitoring_svc: MonitoringService = request.app.state.monitoring_service
    drift_svc: DriftDetectionService = request.app.state.drift_service

    # Pull recent feature samples from predictions
    recent = (
        db.query(FraudPrediction.feature_vector)
        .filter(FraudPrediction.feature_vector.isnot(None))
        .order_by(FraudPrediction.created_at.desc())
        .limit(500)
        .all()
    )

    feature_samples: dict[str, list[float]] = {}
    for (fv,) in recent:
        if not fv:
            continue
        for k, v in fv.items():
            feature_samples.setdefault(k, []).append(float(v))

    drift_events = drift_svc.compute_drift_report(feature_samples)

    # Prediction distribution drift
    recent_preds = (
        db.query(FraudPrediction.fraud_probability)
        .order_by(FraudPrediction.created_at.desc())
        .limit(1000)
        .all()
    )
    probs = [float(p[0]) for p in recent_preds if p[0] is not None]
    pred_drift = drift_svc.compute_prediction_drift(
        baseline_fraud_rate=0.035,
        current_predictions=probs,
    )

    return {
        "feature_drift": drift_events,
        "prediction_drift": pred_drift,
        "total_features_checked": len(drift_events),
        "drifted_features": sum(1 for e in drift_events if e["drift_detected"]),
    }


@router.get("/events")
async def drift_events(db: Session = Depends(get_db), limit: int = 50):
    events = (
        db.query(DriftEvent)
        .order_by(DriftEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "drift_id": e.drift_id,
            "feature_name": e.feature_name,
            "psi_score": e.psi_score,
            "baseline_mean": e.baseline_mean,
            "current_mean": e.current_mean,
            "drift_detected": bool(e.drift_detected),
            "alert_level": e.alert_level,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
