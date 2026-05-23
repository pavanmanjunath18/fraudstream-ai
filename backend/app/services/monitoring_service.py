"""
In-process metrics collection — Prometheus-compatible counters and histograms.

production_equivalent: Replace with prometheus_client push gateway + Grafana
for multi-instance aggregation. This implementation uses thread-safe in-memory
accumulators that expose a /metrics endpoint.
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class LatencyHistogram:
    buckets: list[float] = field(default_factory=lambda: [10, 25, 50, 100, 200, 500, 1000])
    counts: dict[float, int] = field(default_factory=lambda: defaultdict(int))
    total_count: int = 0
    total_sum: float = 0.0

    def observe(self, value_ms: float) -> None:
        self.total_count += 1
        self.total_sum += value_ms
        for b in self.buckets:
            if value_ms <= b:
                self.counts[b] += 1

    def p95(self) -> float:
        if self.total_count == 0:
            return 0.0
        target = int(self.total_count * 0.95)
        cumulative = 0
        for b in sorted(self.buckets):
            cumulative += self.counts.get(b, 0)
            if cumulative >= target:
                return b
        return self.buckets[-1]

    def mean(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.total_sum / self.total_count


class MonitoringService:
    """Thread-safe metrics aggregator."""

    def __init__(self, window_minutes: int = 60):
        self._lock = threading.Lock()
        self._window = timedelta(minutes=window_minutes)

        # Rolling window of predictions for real-time stats
        self._recent_predictions: deque[dict] = deque(maxlen=10_000)

        # Cumulative counters
        self._total_requests = 0
        self._total_fraud_blocked = 0
        self._total_errors = 0

        # Latency histogram (last N requests)
        self._latency = LatencyHistogram()

        # Fraud rate by risk level
        self._decision_counts: dict[str, int] = defaultdict(int)

        # Model health
        self._model_version = "unknown"
        self._last_prediction_at: datetime | None = None

    def record_prediction(self, prediction: dict[str, Any]) -> None:
        with self._lock:
            now = datetime.utcnow()
            self._total_requests += 1
            self._last_prediction_at = now

            decision = prediction.get("decision", "ALLOW")
            self._decision_counts[decision] += 1

            if decision == "BLOCK":
                self._total_fraud_blocked += 1

            if prediction.get("latency_ms"):
                self._latency.observe(prediction["latency_ms"])

            self._recent_predictions.append({
                "ts": now,
                "fraud_probability": prediction.get("fraud_probability", 0),
                "risk_level": prediction.get("risk_level", "MINIMAL"),
                "decision": decision,
                "latency_ms": prediction.get("latency_ms", 0),
                "transaction_id": prediction.get("transaction_id", ""),
            })

    def record_error(self) -> None:
        with self._lock:
            self._total_errors += 1

    def set_model_version(self, version: str) -> None:
        self._model_version = version

    def get_dashboard_metrics(self) -> dict[str, Any]:
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - self._window

            recent = [p for p in self._recent_predictions if p["ts"] >= cutoff]
            n_recent = len(recent)

            fraud_rate = 0.0
            if n_recent > 0:
                fraud_count = sum(1 for p in recent if p["decision"] == "BLOCK")
                fraud_rate = fraud_count / n_recent

            recent_probs = [p["fraud_probability"] for p in recent]
            avg_fraud_prob = sum(recent_probs) / len(recent_probs) if recent_probs else 0.0

            return {
                "total_requests": self._total_requests,
                "total_blocked": self._total_fraud_blocked,
                "total_errors": self._total_errors,
                "requests_last_hour": n_recent,
                "fraud_rate_pct": round(fraud_rate * 100, 2),
                "avg_fraud_probability": round(avg_fraud_prob, 4),
                "avg_latency_ms": round(self._latency.mean(), 2),
                "p95_latency_ms": round(self._latency.p95(), 2),
                "decision_distribution": dict(self._decision_counts),
                "model_version": self._model_version,
                "last_prediction_at": self._last_prediction_at.isoformat() if self._last_prediction_at else None,
                "model_healthy": self._total_errors / max(self._total_requests, 1) < 0.05,
            }

    def get_recent_transactions(self, limit: int = 50) -> list[dict]:
        with self._lock:
            recent = list(self._recent_predictions)
            recent.sort(key=lambda x: x["ts"], reverse=True)
            return [
                {**r, "ts": r["ts"].isoformat()}
                for r in recent[:limit]
            ]

    def get_fraud_probability_distribution(self) -> list[dict]:
        """Returns probability histogram for drift monitoring dashboard."""
        with self._lock:
            probs = [p["fraud_probability"] for p in self._recent_predictions]
            if not probs:
                return []

            bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            distribution = []
            for i in range(len(bins) - 1):
                count = sum(1 for p in probs if bins[i] <= p < bins[i + 1])
                distribution.append({
                    "bucket": f"{bins[i]:.1f}-{bins[i+1]:.1f}",
                    "count": count,
                    "pct": round(count / len(probs) * 100, 2),
                })
            return distribution
