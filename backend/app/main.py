"""
FraudStream AI — FastAPI application entry point.

Startup sequence:
  1. Create DB tables
  2. Load model + SHAP explainer into memory
  3. Connect Redis
  4. Seed demo users (dev only)
  5. Wire app state
"""

import logging
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .database import Base, engine, SessionLocal
from .models import transaction, fraud_prediction, user  # noqa: F401 — registers tables
from .services.inference_service import InferenceService
from .services.monitoring_service import MonitoringService
from .services.drift_detection_service import DriftDetectionService
from .api import auth, scoring, analytics, monitoring, drift

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("FraudStream AI starting up...")

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    # Load ML model
    inference_svc = InferenceService()
    inference_svc.load()
    app.state.inference_service = inference_svc

    # Connect Redis
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}) — feature cache disabled")
        app.state.redis = _FallbackRedis()

    # Monitoring service
    monitoring_svc = MonitoringService()
    monitoring_svc.set_model_version(inference_svc.model_version)
    app.state.monitoring_service = monitoring_svc

    # Drift service
    drift_svc = DriftDetectionService()
    app.state.drift_service = drift_svc

    # Seed demo users in dev
    if settings.app_env == "development":
        _seed_demo_users()

    logger.info("Startup complete — ready to score transactions")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down...")
    if hasattr(app.state, "redis") and not isinstance(app.state.redis, _FallbackRedis):
        await app.state.redis.close()


def _seed_demo_users():
    from .models.user import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    demo_users = [
        {"email": "admin@fraudstream.ai", "password": "admin123", "role": "admin", "full_name": "Admin User"},
        {"email": "analyst@fraudstream.ai", "password": "analyst123", "role": "fraud_analyst", "full_name": "Fraud Analyst"},
        {"email": "reviewer@fraudstream.ai", "password": "reviewer123", "role": "reviewer", "full_name": "Risk Reviewer"},
        {"email": "viewer@fraudstream.ai", "password": "viewer123", "role": "viewer", "full_name": "Dashboard Viewer"},
    ]
    db = SessionLocal()
    try:
        for u in demo_users:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                db.add(User(
                    user_id=f"USR_{uuid.uuid4().hex[:10].upper()}",
                    email=u["email"],
                    hashed_password=pwd_context.hash(u["password"]),
                    full_name=u["full_name"],
                    role=u["role"],
                ))
        db.commit()
        logger.info("Demo users seeded")
    finally:
        db.close()


class _FallbackRedis:
    """No-op Redis stub when Redis is unavailable — features degrade to defaults."""
    async def get(self, key: str):
        return None

    async def set(self, *args, **kwargs):
        pass

    async def ping(self):
        return True


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FraudStream AI",
    description="Real-Time Transaction Risk Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    # In production, set ALLOWED_ORIGINS="https://your-app.vercel.app"
    # "*" is safe here because this API uses JWT tokens for auth, not cookies.
    allow_origins=settings.origins_list if settings.origins_list != ["*"] else ["*"],
    allow_credentials=False if "*" in settings.origins_list else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(scoring.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(drift.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "FraudStream AI",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }
