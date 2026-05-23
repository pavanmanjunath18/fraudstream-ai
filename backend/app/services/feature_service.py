"""
Feature enrichment pipeline — combines transaction data with account,
device, merchant, and velocity signals into an inference-ready vector.

production_equivalent: Replace Redis lookups with a real feature store
(e.g., Feast, Tecton, or Redis Enterprise with TTL-based feature groups).
"""

import json
import math
import logging
from typing import Any

import numpy as np
import redis.asyncio as aioredis

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Feature names must match training schema exactly
FEATURE_COLUMNS = [
    "amount", "amount_log", "amount_zscore",
    "hour_of_day", "day_of_week", "is_weekend",
    "account_age_days", "account_age_log", "credit_score",
    "prior_chargebacks", "synthetic_identity_probability",
    "identity_consistency_score", "email_domain_risk", "phone_risk_score",
    "kyc_verified", "linked_accounts",
    "device_trust_score", "vpn_detected", "emulator_detected",
    "velocity_risk", "known_device",
    "merchant_risk_score", "historical_chargeback_rate",
    "transactions_last_1h", "transactions_last_24h",
    "avg_transaction_amount", "failed_attempts_last_24h",
    "geo_velocity_score",
]


class FeatureService:
    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client

    async def build_feature_vector(self, transaction: dict[str, Any]) -> dict[str, float]:
        """
        Assembles a 28-feature vector from transaction payload + enriched profiles.
        Returns a dict keyed by feature name for SHAP explainability alignment.
        """
        account_profile = await self._get_account_profile(transaction["account_id"])
        device_profile = await self._get_device_profile(transaction["device_id"])
        merchant_profile = await self._get_merchant_profile(transaction["merchant_id"])
        velocity = await self._get_velocity_features(transaction["account_id"])

        from datetime import datetime
        ts = datetime.fromisoformat(transaction["timestamp"].replace("Z", "+00:00"))

        amount = float(transaction["amount"])
        avg_hist = velocity.get("avg_transaction_amount", amount)
        std_hist = max(avg_hist * 0.3, 1.0)  # fallback std estimate
        amount_zscore = (amount - avg_hist) / std_hist

        acct_age = account_profile.get("account_age_days", 365)

        features = {
            # Transaction
            "amount": amount,
            "amount_log": math.log1p(amount),
            "amount_zscore": float(np.clip(amount_zscore, -5, 10)),
            "hour_of_day": float(ts.hour),
            "day_of_week": float(ts.weekday()),
            "is_weekend": float(ts.weekday() >= 5),
            # Account
            "account_age_days": float(acct_age),
            "account_age_log": math.log1p(acct_age),
            "credit_score": float(account_profile.get("credit_score", 650)),
            "prior_chargebacks": float(account_profile.get("prior_chargebacks", 0)),
            "synthetic_identity_probability": float(account_profile.get("synthetic_identity_probability", 0.05)),
            "identity_consistency_score": float(account_profile.get("identity_consistency_score", 0.8)),
            "email_domain_risk": float(account_profile.get("email_domain_risk", 0.1)),
            "phone_risk_score": float(account_profile.get("phone_risk_score", 0.1)),
            "kyc_verified": float(account_profile.get("kyc_verified", 1)),
            "linked_accounts": float(account_profile.get("linked_accounts", 0)),
            # Device
            "device_trust_score": float(device_profile.get("device_trust_score", 0.75)),
            "vpn_detected": float(device_profile.get("vpn_detected", 0)),
            "emulator_detected": float(device_profile.get("emulator_detected", 0)),
            "velocity_risk": float(device_profile.get("velocity_risk", 0.1)),
            "known_device": float(device_profile.get("known_device", 1)),
            # Merchant
            "merchant_risk_score": float(merchant_profile.get("merchant_risk_score", 0.1)),
            "historical_chargeback_rate": float(merchant_profile.get("historical_chargeback_rate", 0.02)),
            # Velocity
            "transactions_last_1h": float(velocity.get("transactions_last_1h", 1)),
            "transactions_last_24h": float(velocity.get("transactions_last_24h", 5)),
            "avg_transaction_amount": float(avg_hist),
            "failed_attempts_last_24h": float(velocity.get("failed_attempts_last_24h", 0)),
            "geo_velocity_score": float(velocity.get("geo_velocity_score", 0.0)),
        }

        return features

    def to_numpy(self, feature_dict: dict[str, float]) -> np.ndarray:
        return np.array([feature_dict[f] for f in FEATURE_COLUMNS], dtype=np.float32)

    # ── Redis helpers ─────────────────────────────────────────────────────────

    async def _get_account_profile(self, account_id: str) -> dict:
        key = f"account:{account_id}"
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return {}  # will use defaults above; production: fallback to Postgres

    async def _get_device_profile(self, device_id: str) -> dict:
        key = f"device:{device_id}"
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return {}

    async def _get_merchant_profile(self, merchant_id: str) -> dict:
        key = f"merchant:{merchant_id}"
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return {}

    async def _get_velocity_features(self, account_id: str) -> dict:
        key = f"velocity:{account_id}"
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return {}
