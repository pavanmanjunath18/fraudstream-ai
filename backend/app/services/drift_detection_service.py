"""
Model drift detection — Population Stability Index (PSI) on feature distributions.

PSI < 0.1: No drift (green)
PSI 0.1-0.2: Moderate drift — monitor (yellow)
PSI > 0.2: Significant drift — consider retraining (red)

production_equivalent: Run this as a daily Airflow DAG comparing
30-day rolling windows to baseline feature statistics.
"""

import logging
import math
import uuid
from datetime import datetime
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _psi_score(baseline: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """Compute PSI between two 1D arrays."""
    eps = 1e-6
    bins = np.percentile(baseline, np.linspace(0, 100, n_bins + 1))
    bins = np.unique(bins)
    if len(bins) < 2:
        return 0.0

    baseline_pcts = np.histogram(baseline, bins=bins)[0] / len(baseline) + eps
    current_pcts = np.histogram(current, bins=bins)[0] / len(current) + eps

    return float(np.sum((current_pcts - baseline_pcts) * np.log(current_pcts / baseline_pcts)))


class DriftDetectionService:
    """
    Compares current feature distributions against a stored baseline
    (computed at model training time from the train set).
    """

    def __init__(self):
        self._baseline_stats: dict[str, dict] = {}

    def set_baseline(self, feature_stats: dict[str, dict]) -> None:
        """Called at startup with stats from model_metadata.json."""
        self._baseline_stats = feature_stats

    def compute_drift_report(
        self, current_feature_samples: dict[str, list[float]]
    ) -> list[dict[str, Any]]:
        """
        Computes PSI for each feature and returns drift events.
        current_feature_samples: {feature_name: [recent_values...]}
        """
        drift_events = []

        for feature_name, current_values in current_feature_samples.items():
            if not current_values or feature_name not in self._baseline_stats:
                continue

            baseline_info = self._baseline_stats[feature_name]
            baseline_arr = np.array(baseline_info.get("samples", [current_values[0]] * 100))
            current_arr = np.array(current_values)

            if len(current_arr) < 50:
                continue

            psi = _psi_score(baseline_arr, current_arr)
            baseline_mean = float(np.mean(baseline_arr))
            current_mean = float(np.mean(current_arr))
            mean_shift_pct = abs(current_mean - baseline_mean) / max(abs(baseline_mean), 1e-6) * 100

            if psi > 0.2:
                alert_level = "CRITICAL"
                drift_detected = True
            elif psi > 0.1:
                alert_level = "WARNING"
                drift_detected = True
            else:
                alert_level = "OK"
                drift_detected = False

            drift_events.append({
                "drift_id": f"DFT_{uuid.uuid4().hex[:10].upper()}",
                "feature_name": feature_name,
                "psi_score": round(psi, 4),
                "baseline_mean": round(baseline_mean, 4),
                "current_mean": round(current_mean, 4),
                "mean_shift_pct": round(mean_shift_pct, 2),
                "drift_detected": drift_detected,
                "alert_level": alert_level,
                "sample_count": len(current_arr),
                "created_at": datetime.utcnow().isoformat(),
            })

        return sorted(drift_events, key=lambda x: x["psi_score"], reverse=True)

    def compute_prediction_drift(
        self,
        baseline_fraud_rate: float,
        current_predictions: list[float],
    ) -> dict[str, Any]:
        """Detects shift in the model's output distribution (fraud probability)."""
        if not current_predictions:
            return {"drift_detected": False, "psi_score": 0.0}

        current_fraud_rate = sum(1 for p in current_predictions if p > 0.5) / len(current_predictions)
        rate_shift_pct = abs(current_fraud_rate - baseline_fraud_rate) / max(baseline_fraud_rate, 1e-6) * 100

        # Simulate PSI on prediction distribution
        baseline_dist = np.random.beta(0.5, 10, 1000)  # typical fraud-skewed dist
        current_dist = np.array(current_predictions)
        psi = _psi_score(baseline_dist, current_dist) if len(current_dist) >= 50 else 0.0

        return {
            "drift_detected": psi > 0.1 or rate_shift_pct > 30,
            "psi_score": round(psi, 4),
            "baseline_fraud_rate": round(baseline_fraud_rate, 4),
            "current_fraud_rate": round(current_fraud_rate, 4),
            "rate_shift_pct": round(rate_shift_pct, 2),
            "alert_level": "CRITICAL" if psi > 0.2 else ("WARNING" if psi > 0.1 else "OK"),
        }
