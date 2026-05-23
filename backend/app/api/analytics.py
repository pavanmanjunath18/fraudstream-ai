"""Analytics endpoints for the dashboard — fraud by merchant, geo, time."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.fraud_prediction import FraudPrediction
from ..services.monitoring_service import MonitoringService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _get_monitoring(request: Request) -> MonitoringService:
    return request.app.state.monitoring_service


@router.get("/overview")
async def overview(request: Request, db: Session = Depends(get_db)):
    monitoring_svc = _get_monitoring(request)
    return monitoring_svc.get_dashboard_metrics()


@router.get("/recent-transactions")
async def recent_transactions(request: Request, limit: int = 50):
    monitoring_svc = _get_monitoring(request)
    return monitoring_svc.get_recent_transactions(limit=limit)


@router.get("/fraud-over-time")
async def fraud_over_time(
    hours: int = 24,
    db: Session = Depends(get_db),
):
    """Returns hourly fraud counts + rates for the last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    records = (
        db.query(FraudPrediction)
        .filter(FraudPrediction.created_at >= cutoff)
        .all()
    )

    buckets: dict[str, dict] = {}
    for r in records:
        if not r.created_at:
            continue
        hour_key = r.created_at.strftime("%Y-%m-%dT%H:00:00")
        if hour_key not in buckets:
            buckets[hour_key] = {"hour": hour_key, "total": 0, "fraud": 0}
        buckets[hour_key]["total"] += 1
        if r.decision == "BLOCK":
            buckets[hour_key]["fraud"] += 1

    result = sorted(buckets.values(), key=lambda x: x["hour"])
    for b in result:
        b["fraud_rate"] = round(b["fraud"] / max(b["total"], 1) * 100, 2)

    return result


@router.get("/risk-distribution")
async def risk_distribution(db: Session = Depends(get_db)):
    """Breakdown of decisions across risk levels."""
    counts = (
        db.query(FraudPrediction.risk_level, FraudPrediction.decision, func.count())
        .group_by(FraudPrediction.risk_level, FraudPrediction.decision)
        .all()
    )
    return [
        {"risk_level": row[0], "decision": row[1], "count": row[2]}
        for row in counts
    ]


@router.get("/top-risk-factors")
async def top_risk_factors(limit: int = 10, db: Session = Depends(get_db)):
    """Most frequently cited risk factors across recent predictions."""
    records = (
        db.query(FraudPrediction.top_risk_factors)
        .filter(FraudPrediction.decision == "BLOCK")
        .order_by(FraudPrediction.created_at.desc())
        .limit(1000)
        .all()
    )

    factor_counts: dict[str, int] = {}
    for (factors,) in records:
        if not factors:
            continue
        for factor in (factors if isinstance(factors, list) else []):
            factor_counts[factor] = factor_counts.get(factor, 0) + 1

    sorted_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"factor": f, "count": c} for f, c in sorted_factors[:limit]]


@router.get("/latency-stats")
async def latency_stats(request: Request):
    monitoring_svc = _get_monitoring(request)
    metrics = monitoring_svc.get_dashboard_metrics()
    return {
        "avg_latency_ms": metrics["avg_latency_ms"],
        "p95_latency_ms": metrics["p95_latency_ms"],
        "total_requests": metrics["total_requests"],
    }


@router.get("/probability-distribution")
async def probability_distribution(request: Request):
    monitoring_svc = _get_monitoring(request)
    return monitoring_svc.get_fraud_probability_distribution()
