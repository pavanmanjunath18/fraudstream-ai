"""
Core fraud scoring API — the hot path.

POST /api/scoring/predict     - single transaction
POST /api/scoring/batch       - up to 100 transactions
GET  /api/scoring/history     - recent predictions
"""

import time
import uuid
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models.fraud_prediction import FraudPrediction, AuditLog
from ..schemas.scoring_schema import (
    TransactionRequest, ScoringResponse,
    BatchScoringRequest, BatchScoringResponse,
    RiskFactor, RuleTrigger,
)
from ..services.feature_service import FeatureService
from ..services.inference_service import InferenceService
from ..services.monitoring_service import MonitoringService

router = APIRouter(prefix="/scoring", tags=["scoring"])
settings = get_settings()


def _get_inference_service(request: Request) -> InferenceService:
    return request.app.state.inference_service


def _get_monitoring_service(request: Request) -> MonitoringService:
    return request.app.state.monitoring_service


async def _get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


async def _persist_prediction(db: Session, prediction: dict) -> None:
    record = FraudPrediction(
        prediction_id=prediction["prediction_id"],
        transaction_id=prediction["transaction_id"],
        model_version=prediction["model_version"],
        fraud_probability=prediction["fraud_probability"],
        risk_level=prediction["risk_level"],
        decision=prediction["decision"],
        top_risk_factors=prediction["top_risk_factors"],
        rule_triggers=prediction.get("rule_triggers", []),
        feature_vector={k: v for k, v in (prediction.get("feature_vector") or {}).items()
                        if k in ["amount", "vpn_detected", "emulator_detected",
                                 "transactions_last_1h", "synthetic_identity_probability"]},
        shap_values=prediction.get("shap_values"),
        latency_ms=prediction.get("latency_ms"),
    )
    db.add(record)

    audit = AuditLog(
        log_id=f"LOG_{uuid.uuid4().hex[:12].upper()}",
        transaction_id=prediction["transaction_id"],
        prediction_id=prediction["prediction_id"],
        action="AUTO_SCORED",
    )
    db.add(audit)
    db.commit()


def _build_response(prediction: dict) -> ScoringResponse:
    shap_factors = [
        RiskFactor(**f) for f in prediction.get("shap_factors", [])
    ]
    rule_triggers = [
        RuleTrigger(**r) for r in prediction.get("rule_triggers", [])
    ]
    return ScoringResponse(
        transaction_id=prediction["transaction_id"],
        prediction_id=prediction["prediction_id"],
        fraud_probability=prediction["fraud_probability"],
        raw_ml_score=prediction["raw_ml_score"],
        risk_level=prediction["risk_level"],
        decision=prediction["decision"],
        top_risk_factors=prediction["top_risk_factors"],
        shap_factors=shap_factors,
        rule_triggers=rule_triggers,
        model_version=prediction["model_version"],
        latency_ms=prediction["latency_ms"],
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/predict", response_model=ScoringResponse, status_code=200)
async def predict(
    body: TransactionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Real-time fraud scoring endpoint.
    Target: < 100ms end-to-end under normal load.
    """
    inference_svc: InferenceService = _get_inference_service(request)
    monitoring_svc: MonitoringService = _get_monitoring_service(request)
    redis_client: aioredis.Redis = await _get_redis(request)

    feature_svc = FeatureService(redis_client)
    txn_dict = body.model_dump()

    try:
        feature_dict = await feature_svc.build_feature_vector(txn_dict)
        prediction = inference_svc.predict(feature_dict, txn_dict)
    except Exception as e:
        monitoring_svc.record_error()
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")

    monitoring_svc.record_prediction(prediction)

    # Persist asynchronously — don't block the response path
    background_tasks.add_task(_persist_prediction, db, prediction)

    return _build_response(prediction)


@router.post("/batch", response_model=BatchScoringResponse)
async def batch_predict(
    body: BatchScoringRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Batch scoring — up to 100 transactions per call."""
    inference_svc: InferenceService = _get_inference_service(request)
    monitoring_svc: MonitoringService = _get_monitoring_service(request)
    redis_client: aioredis.Redis = await _get_redis(request)

    feature_svc = FeatureService(redis_client)
    t0 = time.perf_counter()
    results = []

    for txn in body.transactions:
        txn_dict = txn.model_dump()
        try:
            feature_dict = await feature_svc.build_feature_vector(txn_dict)
            prediction = inference_svc.predict(feature_dict, txn_dict)
            monitoring_svc.record_prediction(prediction)
            results.append(_build_response(prediction))
        except Exception as e:
            monitoring_svc.record_error()

    total_ms = round((time.perf_counter() - t0) * 1000, 2)

    return BatchScoringResponse(
        results=results,
        batch_size=len(results),
        total_latency_ms=total_ms,
        fraud_count=sum(1 for r in results if r.fraud_probability > 0.5),
        block_count=sum(1 for r in results if r.decision == "BLOCK"),
    )


@router.get("/history")
async def prediction_history(
    limit: int = 50,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(FraudPrediction).order_by(FraudPrediction.created_at.desc())
    if risk_level:
        query = query.filter(FraudPrediction.risk_level == risk_level.upper())
    records = query.limit(min(limit, 200)).all()

    return [
        {
            "prediction_id": r.prediction_id,
            "transaction_id": r.transaction_id,
            "fraud_probability": r.fraud_probability,
            "risk_level": r.risk_level,
            "decision": r.decision,
            "top_risk_factors": r.top_risk_factors,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
