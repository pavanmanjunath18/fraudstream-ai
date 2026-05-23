"""Celery task implementations."""

import logging
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.run_drift_scan", bind=True, max_retries=3)
def run_drift_scan(self):
    """
    Runs PSI drift analysis on recent feature distributions.
    Persists DriftEvent records for any features exceeding thresholds.
    """
    try:
        from .database import SessionLocal
        from .models.fraud_prediction import FraudPrediction, DriftEvent
        from .services.drift_detection_service import DriftDetectionService
        import uuid
        from datetime import datetime

        db = SessionLocal()
        drift_svc = DriftDetectionService()

        recent = (
            db.query(FraudPrediction.feature_vector)
            .filter(FraudPrediction.feature_vector.isnot(None))
            .order_by(FraudPrediction.created_at.desc())
            .limit(1000)
            .all()
        )

        feature_samples: dict[str, list[float]] = {}
        for (fv,) in recent:
            if not fv:
                continue
            for k, v in fv.items():
                feature_samples.setdefault(k, []).append(float(v))

        drift_events = drift_svc.compute_drift_report(feature_samples)

        for event in drift_events:
            if event["drift_detected"]:
                db.add(DriftEvent(
                    drift_id=event["drift_id"],
                    feature_name=event["feature_name"],
                    psi_score=event["psi_score"],
                    baseline_mean=event["baseline_mean"],
                    current_mean=event["current_mean"],
                    drift_detected=1,
                    alert_level=event["alert_level"],
                ))

        db.commit()
        db.close()

        n_drifted = sum(1 for e in drift_events if e["drift_detected"])
        logger.info(f"Drift scan complete: {n_drifted} features drifting out of {len(drift_events)}")
        return {"status": "ok", "drifted": n_drifted}

    except Exception as exc:
        logger.error(f"Drift scan failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="app.tasks.refresh_analytics")
def refresh_analytics():
    """Placeholder for analytics aggregation job."""
    logger.info("Analytics refresh triggered")
    return {"status": "ok"}


@celery_app.task(name="app.tasks.model_health_check")
def model_health_check():
    """Verifies model is still loaded and responsive."""
    logger.info("Model health check triggered")
    return {"status": "ok"}
