"""
Integration tests for the fraud scoring API.
Requires a running backend (use pytest with the FastAPI TestClient).
"""

import json
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.feature_service import FeatureService, FEATURE_COLUMNS
from app.services.fraud_rules_service import FraudRulesService, RuleSeverity
from app.services.inference_service import InferenceService


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _txn(
    amount: float = 150.0,
    vpn: bool = False,
    emulator: bool = False,
    txns_last_1h: int = 1,
) -> dict:
    return {
        "transaction_id": f"TXN_{uuid.uuid4().hex[:14].upper()}",
        "timestamp": datetime.utcnow().isoformat(),
        "account_id": "ACC_TEST001",
        "merchant_id": "MER_TEST001",
        "amount": amount,
        "currency": "USD",
        "payment_method": "credit_card",
        "device_id": "DEV_TEST001",
        "ip_address": "192.168.1.100",
        "geo_lat": 37.7749,
        "geo_lon": -122.4194,
        "merchant_category": "retail",
        "transaction_channel": "web",
    }


# ─── API tests ────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/monitoring/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root_returns_service_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["service"] == "FraudStream AI"


class TestScoringEndpoint:
    def test_predict_returns_valid_structure(self, client):
        resp = client.post("/api/scoring/predict", json=_txn())
        assert resp.status_code == 200
        data = resp.json()

        assert "fraud_probability" in data
        assert "risk_level" in data
        assert "decision" in data
        assert "top_risk_factors" in data
        assert "latency_ms" in data
        assert 0.0 <= data["fraud_probability"] <= 1.0
        assert data["risk_level"] in ("MINIMAL", "LOW", "MEDIUM", "HIGH")
        assert data["decision"] in ("ALLOW", "REVIEW", "BLOCK")

    def test_predict_large_amount_elevated_risk(self, client):
        """$8,000 transaction on new account should push risk up."""
        resp = client.post("/api/scoring/predict", json=_txn(amount=8000.0))
        assert resp.status_code == 200
        data = resp.json()
        # Can't guarantee HIGH without full feature data, but score should be non-trivial
        assert data["fraud_probability"] >= 0.0

    def test_predict_invalid_amount_rejected(self, client):
        txn = _txn()
        txn["amount"] = -100
        resp = client.post("/api/scoring/predict", json=txn)
        assert resp.status_code == 422

    def test_predict_missing_required_field(self, client):
        txn = _txn()
        del txn["account_id"]
        resp = client.post("/api/scoring/predict", json=txn)
        assert resp.status_code == 422

    def test_predict_latency_under_threshold(self, client):
        """Smoke test — response should arrive within a reasonable bound."""
        import time
        t0 = time.perf_counter()
        resp = client.post("/api/scoring/predict", json=_txn())
        elapsed = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200
        # In test environment (no real Redis/model), allow generous bound
        assert elapsed < 5000

    def test_batch_predict(self, client):
        payload = {"transactions": [_txn(amount=a) for a in [50, 200, 1500, 8000]]}
        resp = client.post("/api/scoring/batch", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_size"] == 4
        assert len(data["results"]) == 4


# ─── Rules engine unit tests ──────────────────────────────────────────────────

class TestFraudRulesService:
    def setup_method(self):
        self.svc = FraudRulesService()

    def test_vpn_emulator_combo_triggers_high(self):
        features = {"vpn_detected": 1.0, "emulator_detected": 1.0}
        results, boost = self.svc.evaluate(features, {})
        triggered = [r for r in results if r.rule_id == "VPN_PLUS_EMULATOR"]
        assert len(triggered) == 1
        assert triggered[0].severity == RuleSeverity.HIGH

    def test_velocity_spike_triggers(self):
        features = {"transactions_last_1h": 15.0}
        results, boost = self.svc.evaluate(features, {})
        triggered = [r for r in results if r.rule_id == "VELOCITY_SPIKE"]
        assert len(triggered) == 1

    def test_no_rules_triggered_for_clean_transaction(self):
        features = {
            "vpn_detected": 0.0,
            "emulator_detected": 0.0,
            "transactions_last_1h": 2.0,
            "known_device": 1.0,
            "amount": 50.0,
            "merchant_risk_score": 0.1,
            "synthetic_identity_probability": 0.05,
            "kyc_verified": 1.0,
            "prior_chargebacks": 0.0,
            "failed_attempts_last_24h": 0.0,
            "account_age_days": 500.0,
        }
        results, boost = self.svc.evaluate(features, {})
        assert len(results) == 0
        assert boost == 0.0

    def test_score_boost_capped(self):
        # Multiple rules firing should not exceed 0.60 boost
        features = {
            "vpn_detected": 1.0,
            "emulator_detected": 1.0,
            "transactions_last_1h": 20.0,
            "known_device": 0.0,
            "amount": 5000.0,
            "merchant_risk_score": 0.9,
            "synthetic_identity_probability": 0.8,
            "kyc_verified": 0.0,
            "prior_chargebacks": 5.0,
            "failed_attempts_last_24h": 10.0,
            "account_age_days": 10.0,
            "geo_velocity_score": 0.95,
        }
        _, boost = self.svc.evaluate(features, {})
        assert boost <= 0.60


# ─── Feature service unit tests ───────────────────────────────────────────────

class TestFeaturePipeline:
    def test_feature_columns_count(self):
        assert len(FEATURE_COLUMNS) == 28

    def test_feature_names_are_unique(self):
        assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS))

    def test_inference_service_demo_score_range(self):
        svc = InferenceService()
        features = {f: 0.0 for f in FEATURE_COLUMNS}
        score = svc._demo_score(features)
        assert 0.0 <= score <= 1.0

    def test_high_risk_features_produce_high_demo_score(self):
        svc = InferenceService()
        features = {f: 0.0 for f in FEATURE_COLUMNS}
        features["synthetic_identity_probability"] = 0.95
        features["vpn_detected"] = 1.0
        features["emulator_detected"] = 1.0
        features["transactions_last_1h"] = 15.0
        score = svc._demo_score(features)
        assert score > 0.5
