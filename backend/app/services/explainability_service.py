"""
SHAP-based explainability — produces human-readable risk factors
from the XGBoost model's feature contributions.
"""

import logging
from typing import Any

import numpy as np
import shap

logger = logging.getLogger(__name__)

# Human-readable labels for each feature
FEATURE_LABELS = {
    "amount": "Transaction amount",
    "amount_log": "Transaction amount (log scale)",
    "amount_zscore": "Unusual transaction size vs. account history",
    "hour_of_day": "Transaction time (hour)",
    "day_of_week": "Day of week",
    "is_weekend": "Weekend transaction",
    "account_age_days": "Account age",
    "account_age_log": "Account age (log scale)",
    "credit_score": "Credit score",
    "prior_chargebacks": "Prior chargeback history",
    "synthetic_identity_probability": "Synthetic identity risk",
    "identity_consistency_score": "Identity consistency",
    "email_domain_risk": "High-risk email domain",
    "phone_risk_score": "Phone risk score",
    "kyc_verified": "KYC verification status",
    "linked_accounts": "Number of linked accounts",
    "device_trust_score": "Device trust score",
    "vpn_detected": "VPN usage detected",
    "emulator_detected": "Device emulator detected",
    "velocity_risk": "Device velocity risk",
    "known_device": "New/unknown device",
    "merchant_risk_score": "Merchant risk score",
    "historical_chargeback_rate": "Merchant chargeback rate",
    "transactions_last_1h": "Transaction velocity (1h)",
    "transactions_last_24h": "Transaction velocity (24h)",
    "avg_transaction_amount": "Avg transaction amount",
    "failed_attempts_last_24h": "Failed payment attempts (24h)",
    "geo_velocity_score": "Geographic velocity anomaly",
}

FEATURE_COLUMNS = list(FEATURE_LABELS.keys())


class ExplainabilityService:
    def __init__(self, explainer: shap.TreeExplainer):
        self._explainer = explainer

    def get_top_risk_factors(
        self,
        feature_vector: np.ndarray,
        feature_dict: dict[str, float],
        top_n: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Returns top N SHAP-based risk factors sorted by absolute contribution.
        Positive SHAP → increases fraud probability.
        """
        try:
            shap_vals = self._explainer.shap_values(
                feature_vector.reshape(1, -1)
            )[0]
        except Exception as e:
            logger.warning(f"SHAP computation failed: {e} — using feature importance fallback")
            return self._fallback_risk_factors(feature_dict, top_n)

        factors = []
        for i, (feature, shap_val) in enumerate(zip(FEATURE_COLUMNS, shap_vals)):
            if shap_val > 0.001:  # only include fraud-increasing contributions
                factors.append({
                    "feature": feature,
                    "label": FEATURE_LABELS.get(feature, feature),
                    "shap_value": round(float(shap_val), 4),
                    "feature_value": round(float(feature_dict.get(feature, 0)), 4),
                    "direction": "increases_risk",
                })

        factors.sort(key=lambda x: x["shap_value"], reverse=True)
        return factors[:top_n]

    def get_full_shap_vector(self, feature_vector: np.ndarray) -> dict[str, float]:
        """Returns full feature → SHAP value mapping for the dashboard."""
        try:
            shap_vals = self._explainer.shap_values(
                feature_vector.reshape(1, -1)
            )[0]
            return {
                feat: round(float(val), 6)
                for feat, val in zip(FEATURE_COLUMNS, shap_vals)
            }
        except Exception as e:
            logger.warning(f"SHAP full vector failed: {e}")
            return {}

    def _fallback_risk_factors(
        self,
        feature_dict: dict[str, float],
        top_n: int,
    ) -> list[dict[str, Any]]:
        """Heuristic fallback if SHAP explainer unavailable."""
        risk_map = {
            "synthetic_identity_probability": feature_dict.get("synthetic_identity_probability", 0) * 2,
            "vpn_detected": feature_dict.get("vpn_detected", 0) * 1.5,
            "emulator_detected": feature_dict.get("emulator_detected", 0) * 1.5,
            "transactions_last_1h": min(feature_dict.get("transactions_last_1h", 0) / 10, 1),
            "amount_zscore": max(feature_dict.get("amount_zscore", 0) / 5, 0),
            "prior_chargebacks": min(feature_dict.get("prior_chargebacks", 0) / 5, 1),
        }
        sorted_factors = sorted(risk_map.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "feature": f,
                "label": FEATURE_LABELS.get(f, f),
                "shap_value": round(v, 4),
                "feature_value": round(float(feature_dict.get(f, 0)), 4),
                "direction": "increases_risk",
            }
            for f, v in sorted_factors[:top_n]
            if v > 0
        ]
