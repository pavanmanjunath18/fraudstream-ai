from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class TransactionRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    account_id: str = Field(..., description="Account identifier")
    merchant_id: str = Field(..., description="Merchant identifier")
    amount: float = Field(..., gt=0, le=1_000_000, description="Transaction amount in currency units")
    currency: str = Field(default="USD", max_length=3)
    payment_method: str = Field(..., description="credit_card | debit_card | ach | wire | crypto")
    device_id: str = Field(..., description="Device fingerprint identifier")
    ip_address: str = Field(..., description="Client IP address")
    geo_lat: Optional[float] = Field(None, ge=-90, le=90)
    geo_lon: Optional[float] = Field(None, ge=-180, le=180)
    merchant_category: Optional[str] = None
    transaction_channel: Optional[str] = Field(None, description="web | mobile_app | in_store | api | atm")

    @field_validator("amount")
    @classmethod
    def amount_precision(cls, v: float) -> float:
        return round(v, 2)


class RiskFactor(BaseModel):
    feature: str
    label: str
    shap_value: float
    feature_value: float
    direction: str


class RuleTrigger(BaseModel):
    rule_id: str
    reason: str
    severity: str


class ScoringResponse(BaseModel):
    transaction_id: str
    prediction_id: str
    fraud_probability: float = Field(..., ge=0, le=1)
    raw_ml_score: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., description="MINIMAL | LOW | MEDIUM | HIGH")
    decision: str = Field(..., description="ALLOW | REVIEW | BLOCK")
    top_risk_factors: list[str]
    shap_factors: list[RiskFactor]
    rule_triggers: list[RuleTrigger]
    model_version: str
    latency_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class BatchScoringRequest(BaseModel):
    transactions: list[TransactionRequest] = Field(..., min_length=1, max_length=100)


class BatchScoringResponse(BaseModel):
    results: list[ScoringResponse]
    batch_size: int
    total_latency_ms: float
    fraud_count: int
    block_count: int
