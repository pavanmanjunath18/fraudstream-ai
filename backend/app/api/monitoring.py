"""Infrastructure monitoring and model health endpoints."""

from fastapi import APIRouter, Request
from ..services.monitoring_service import MonitoringService
from ..services.inference_service import InferenceService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "fraudstream-api"}


@router.get("/metrics")
async def metrics(request: Request):
    monitoring_svc: MonitoringService = request.app.state.monitoring_service
    return monitoring_svc.get_dashboard_metrics()


@router.get("/model-info")
async def model_info(request: Request):
    inference_svc: InferenceService = request.app.state.inference_service
    return {
        "is_loaded": inference_svc.is_loaded,
        "version": inference_svc.model_version,
        "metadata": inference_svc.metadata,
    }
