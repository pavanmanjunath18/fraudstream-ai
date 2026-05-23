"""
FraudStream AI — Locust load test suite.

Simulates concurrent fraud scoring requests to measure:
  - Requests/second throughput
  - p50 / p95 / p99 latency
  - API stability under sustained load

Usage:
    pip install locust
    locust -f scripts/load_test.py --host http://localhost:8000 --headless \
           -u 50 -r 10 --run-time 60s

    # UI mode (opens http://localhost:8089)
    locust -f scripts/load_test.py --host http://localhost:8000

Target SLOs:
  p50 latency: < 30ms
  p95 latency: < 100ms
  error rate:  < 0.1%
"""

import random
import uuid
from datetime import datetime

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


PAYMENT_METHODS = ["credit_card", "debit_card", "ach", "wire"]
CHANNELS = ["web", "mobile_app", "in_store", "api"]
ACCOUNT_POOL = [f"ACC_{uuid.uuid4().hex[:10].upper()}" for _ in range(500)]
MERCHANT_POOL = [f"MER_{uuid.uuid4().hex[:8].upper()}" for _ in range(100)]
DEVICE_POOL = [f"DEV_{uuid.uuid4().hex[:12].upper()}" for _ in range(300)]


def _make_transaction(
    amount: float | None = None,
    high_risk: bool = False,
) -> dict:
    if amount is None:
        amount = round(random.lognormal(4.5, 1.2), 2) if not high_risk else round(random.uniform(2000, 8000), 2)

    return {
        "transaction_id": f"TXN_{uuid.uuid4().hex[:14].upper()}",
        "timestamp": datetime.utcnow().isoformat(),
        "account_id": random.choice(ACCOUNT_POOL),
        "merchant_id": random.choice(MERCHANT_POOL),
        "amount": min(amount, 50_000),
        "currency": "USD",
        "payment_method": random.choice(PAYMENT_METHODS),
        "device_id": random.choice(DEVICE_POOL),
        "ip_address": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
        "geo_lat": round(random.uniform(25, 50), 4),
        "geo_lon": round(random.uniform(-125, -70), 4),
        "merchant_category": random.choice(["retail", "electronics", "grocery", "travel"]),
        "transaction_channel": random.choice(CHANNELS),
    }


class FraudScoringUser(HttpUser):
    """
    Simulates a transaction processing service calling the fraud API.
    80% normal transactions, 20% high-risk transactions.
    """
    wait_time = between(0.05, 0.2)  # 5-200ms think time

    @task(8)
    def score_normal_transaction(self):
        txn = _make_transaction()
        with self.client.post(
            "/api/scoring/predict",
            json=txn,
            catch_response=True,
            name="POST /scoring/predict [normal]",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if "fraud_probability" not in data:
                    resp.failure("Missing fraud_probability in response")
                else:
                    resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def score_high_risk_transaction(self):
        """High-value transactions — more likely to trigger rules."""
        txn = _make_transaction(high_risk=True)
        with self.client.post(
            "/api/scoring/predict",
            json=txn,
            catch_response=True,
            name="POST /scoring/predict [high-risk]",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def check_health(self):
        with self.client.get(
            "/api/monitoring/health",
            catch_response=True,
            name="GET /health",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def get_analytics(self):
        with self.client.get(
            "/api/analytics/overview",
            catch_response=True,
            name="GET /analytics/overview",
        ) as resp:
            if resp.status_code in (200, 401, 422):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class BatchScoringUser(HttpUser):
    """
    Simulates batch scoring — like a nightly fraud sweep or import job.
    Lower concurrency, larger payloads.
    """
    wait_time = between(1, 3)
    weight = 1  # 1 batch user per ~10 single-request users

    @task
    def batch_score(self):
        batch_size = random.randint(5, 20)
        payload = {"transactions": [_make_transaction() for _ in range(batch_size)]}

        with self.client.post(
            "/api/scoring/batch",
            json=payload,
            catch_response=True,
            name=f"POST /scoring/batch [n={batch_size}]",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("batch_size") == len(payload["transactions"]):
                    resp.success()
                else:
                    resp.failure("Batch size mismatch")
            else:
                resp.failure(f"HTTP {resp.status_code}")


# ── Stats reporting ───────────────────────────────────────────────────────────

@events.quitting.add_listener
def print_summary(environment, **kwargs):
    stats = environment.runner.stats.total
    print("\n" + "=" * 60)
    print("FRAUDSTREAM AI — LOAD TEST SUMMARY")
    print("=" * 60)
    print(f"  Total requests:   {stats.num_requests:,}")
    print(f"  Failures:         {stats.num_failures:,} ({stats.fail_ratio * 100:.2f}%)")
    print(f"  Avg RPS:          {stats.current_rps:.1f}")
    print(f"  Median latency:   {stats.median_response_time}ms")
    print(f"  p95 latency:      {stats.get_response_time_percentile(0.95)}ms")
    print(f"  p99 latency:      {stats.get_response_time_percentile(0.99)}ms")
    print(f"  Min latency:      {stats.min_response_time}ms")
    print(f"  Max latency:      {stats.max_response_time}ms")
    print("=" * 60)

    # Fail the test if SLOs are violated
    p95 = stats.get_response_time_percentile(0.95)
    error_rate = stats.fail_ratio

    violations = []
    if p95 and p95 > 100:
        violations.append(f"p95 latency {p95}ms > 100ms SLO")
    if error_rate > 0.001:
        violations.append(f"Error rate {error_rate*100:.2f}% > 0.1% SLO")

    if violations:
        print("\nSLO VIOLATIONS:")
        for v in violations:
            print(f"  ✗ {v}")
        environment.process_exit_code = 1
    else:
        print("\nAll SLOs met.")
        environment.process_exit_code = 0
