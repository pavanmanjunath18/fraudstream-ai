"""
Core inference service — loads the XGBoost model, runs predictions,
and fuses ML probability with rule engine results into a final decision.

The model + explainer are loaded once at startup and held in memory.
production_equivalent: Replace with Triton Inference Server or TorchServe
for multi-GPU serving with batching and A/B model routing.
"""

import json
import logging
import pickle
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import shap
import xgboost as xgb

from ..config import get_settings
from .explainability_service import ExplainabilityService
from .feature_service import FEATURE_COLUMNS
from .fraud_rules_service import FraudRulesService, RuleSeverity

logger = logging.getLogger(__name__)
settings = get_settings()


class InferenceService:
    """Singleton-style service — instantiated once at FastAPI startup."""

    def __init__(self):
        self._model: xgb.XGBClassifier | None = None
        self._explainer: shap.TreeExplainer | None = None
        self._metadata: dict = {}
        self._fraud_threshold: float = settings.fraud_threshold
        self._high_risk_threshold: float = settings.high_risk_threshold
        self._rules_service = FraudRulesService()
        self._explainability_service: ExplainabilityService | None = None
        self._model_version: str = "unknown"

    def load(self) -> None:
        model_path = Path(settings.model_path)
        metadata_path = Path(settings.model_metadata_path)
        explainer_path = model_path.parent / "shap_explainer.pkl"

        if not model_path.exists():
            logger.warning(f"Model not found at {model_path} — running in demo mode")
            return

        t0 = time.perf_counter()

        with open(model_path, "rb") as f:
            self._model = pickle.load(f)

        if explainer_path.exists():
            with open(explainer_path, "rb") as f:
                self._explainer = pickle.load(f)
            self._explainability_service = ExplainabilityService(self._explainer)
        else:
            logger.warning("SHAP explainer not found — explainability will use fallback")

        if metadata_path.exists():
            with open(metadata_path) as f:
                self._metadata = json.load(f)
            self._fraud_threshold = self._metadata.get("thresholds", {}).get(
                "fraud_threshold", settings.fraud_threshold
            )
            self._high_risk_threshold = self._metadata.get("thresholds", {}).get(
                "high_risk_threshold", settings.high_risk_threshold
            )
            self._model_version = self._metadata.get("version", "1.0.0")

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"Model loaded in {elapsed:.1f}ms | version={self._model_version} | threshold={self._fraud_threshold}")

    def predict(
        self,
        feature_dict: dict[str, float],
        transaction: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Full inference pass:
          1. Build feature array
          2. XGBoost prediction
          3. Rules engine
          4. Decision fusion
          5. Explainability
        Returns structured prediction dict.
        """
        t0 = time.perf_counter()
        prediction_id = f"PRED_{uuid.uuid4().hex[:14].upper()}"

        # ── Feature vector ────────────────────────────────────────────────────
        feature_vector = np.array(
            [feature_dict.get(f, 0.0) for f in FEATURE_COLUMNS],
            dtype=np.float32
        )

        # ── ML inference ──────────────────────────────────────────────────────
        if self._model is not None:
            fraud_prob = float(
                self._model.predict_proba(feature_vector.reshape(1, -1))[0, 1]
            )
        else:
            # Demo mode — synthesize a plausible score from key features
            fraud_prob = self._demo_score(feature_dict)

        # ── Rules engine ──────────────────────────────────────────────────────
        rule_results, score_boost = self._rules_service.evaluate(feature_dict, transaction)
        has_critical = self._rules_service.has_critical_rule(rule_results)

        # ── Decision fusion ───────────────────────────────────────────────────
        adjusted_prob = min(fraud_prob + score_boost, 0.999)

        if has_critical or adjusted_prob >= self._high_risk_threshold:
            risk_level = "HIGH"
            decision = "BLOCK"
        elif adjusted_prob >= self._fraud_threshold:
            risk_level = "MEDIUM"
            decision = "REVIEW"
        elif adjusted_prob >= 0.25:
            risk_level = "LOW"
            decision = "ALLOW"
        else:
            risk_level = "MINIMAL"
            decision = "ALLOW"

        # ── Explainability ────────────────────────────────────────────────────
        top_risk_factors = []
        shap_vector = {}
        if self._explainability_service:
            top_risk_factors = self._explainability_service.get_top_risk_factors(
                feature_vector, feature_dict
            )
            shap_vector = self._explainability_service.get_full_shap_vector(feature_vector)

        # Add triggered rules as additional context
        rule_descriptions = [
            {"rule_id": r.rule_id, "reason": r.reason, "severity": r.severity.value}
            for r in rule_results
        ]

        # Merge rule triggers into top factors (deduplicated labels)
        rule_labels = [r.reason for r in rule_results]
        shap_labels = [f["label"] for f in top_risk_factors]
        all_top_factors = shap_labels + [r for r in rule_labels if r not in shap_labels]

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "prediction_id": prediction_id,
            "transaction_id": transaction["transaction_id"],
            "fraud_probability": round(adjusted_prob, 4),
            "raw_ml_score": round(fraud_prob, 4),
            "risk_level": risk_level,
            "decision": decision,
            "top_risk_factors": all_top_factors[:5],
            "shap_factors": top_risk_factors,
            "rule_triggers": rule_descriptions,
            "feature_vector": feature_dict,
            "shap_values": shap_vector,
            "model_version": self._model_version,
            "latency_ms": latency_ms,
        }

    def _demo_score(self, features: dict[str, float]) -> float:
        """Heuristic score when model artifact isn't loaded (dev/demo mode)."""
        score = 0.05
        score += features.get("synthetic_identity_probability", 0) * 0.4
        score += features.get("vpn_detected", 0) * 0.2
        score += features.get("emulator_detected", 0) * 0.2
        score += min(features.get("transactions_last_1h", 0) / 20, 0.3)
        score += features.get("merchant_risk_score", 0) * 0.15
        score += max(features.get("amount_zscore", 0) / 8, 0)
        score += features.get("prior_chargebacks", 0) * 0.05
        return min(score, 0.95)

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def metadata(self) -> dict:
        return self._metadata
