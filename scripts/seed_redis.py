"""
Seeds Redis with account, device, and merchant profiles from the synthetic CSVs.

Run once before starting the backend to warm the feature cache:
    python scripts/seed_redis.py

production_equivalent: Replace with a feature store loader that runs as a
Flink/Spark job on the events stream, keeping Redis current with sub-second lag.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import redis

DATA_DIR = Path(__file__).parent.parent / "synthetic-data"
REDIS_URL = "redis://localhost:6379/0"


def seed(r: redis.Redis) -> None:
    # ── Accounts ──────────────────────────────────────────────────────────────
    print("Seeding account profiles...")
    accounts = pd.read_csv(DATA_DIR / "accounts.csv")
    pipe = r.pipeline(transaction=False)
    for _, row in accounts.iterrows():
        key = f"account:{row['account_id']}"
        data = {
            "account_age_days": int(row["account_age_days"]),
            "credit_score": int(row["credit_score"]),
            "kyc_verified": int(row["kyc_verified"]),
            "email_domain_risk": float(row["email_domain_risk"]),
            "phone_risk_score": float(row["phone_risk_score"]),
            "identity_consistency_score": float(row["identity_consistency_score"]),
            "prior_chargebacks": int(row["prior_chargebacks"]),
            "linked_accounts": int(row["linked_accounts"]),
            "synthetic_identity_probability": float(row["synthetic_identity_probability"]),
        }
        pipe.setex(key, 86400, json.dumps(data))  # TTL: 24h
    pipe.execute()
    print(f"  → {len(accounts):,} accounts cached")

    # ── Devices ───────────────────────────────────────────────────────────────
    print("Seeding device profiles...")
    devices = pd.read_csv(DATA_DIR / "devices.csv")
    pipe = r.pipeline(transaction=False)
    for _, row in devices.iterrows():
        key = f"device:{row['device_id']}"
        data = {
            "device_trust_score": float(row["device_trust_score"]),
            "vpn_detected": bool(row["vpn_detected"]),
            "emulator_detected": bool(row["emulator_detected"]),
            "velocity_risk": float(row["velocity_risk"]),
            "known_device": bool(row["known_device"]),
        }
        pipe.setex(key, 86400, json.dumps(data))
    pipe.execute()
    print(f"  → {len(devices):,} devices cached")

    # ── Merchants ─────────────────────────────────────────────────────────────
    print("Seeding merchant profiles...")
    merchants = pd.read_csv(DATA_DIR / "merchants.csv")
    pipe = r.pipeline(transaction=False)
    for _, row in merchants.iterrows():
        key = f"merchant:{row['merchant_id']}"
        data = {
            "merchant_risk_score": float(row["merchant_risk_score"]),
            "historical_chargeback_rate": float(row["historical_chargeback_rate"]),
            "industry": str(row["industry"]),
            "country": str(row["country"]),
        }
        pipe.setex(key, 86400, json.dumps(data))
    pipe.execute()
    print(f"  → {len(merchants):,} merchants cached")

    # ── Velocity features ─────────────────────────────────────────────────────
    print("Seeding velocity features...")
    velocity = pd.read_csv(DATA_DIR / "transaction_velocity_features.csv")
    pipe = r.pipeline(transaction=False)
    for _, row in velocity.iterrows():
        key = f"velocity:{row['account_id']}"
        data = {
            "transactions_last_1h": int(row["transactions_last_1h"]),
            "transactions_last_24h": int(row["transactions_last_24h"]),
            "avg_transaction_amount": float(row["avg_transaction_amount"]),
            "failed_attempts_last_24h": int(row["failed_attempts_last_24h"]),
            "geo_velocity_score": float(row["geo_velocity_score"]),
        }
        pipe.setex(key, 3600, json.dumps(data))  # Velocity TTL: 1h
    pipe.execute()
    print(f"  → {len(velocity):,} velocity profiles cached")


def main():
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
    except Exception as e:
        print(f"Redis connection failed: {e}")
        sys.exit(1)

    seed(r)
    print("\nRedis seeded successfully.")


if __name__ == "__main__":
    main()
