"""
Synthetic fintech dataset generator for FraudStream AI.

Generates realistic transaction data with correlated fraud patterns,
velocity anomalies, synthetic identity signals, and device/geo features.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid
import random
import hashlib
import json
from pathlib import Path

np.random.seed(42)
random.seed(42)

OUTPUT_DIR = Path(__file__).parent

# ─── Config ──────────────────────────────────────────────────────────────────
N_ACCOUNTS = 5_000
N_MERCHANTS = 800
N_DEVICES = 6_000
N_TRANSACTIONS = 100_000
FRAUD_RATE = 0.035  # 3.5% base fraud rate — realistic fintech range

# ─── Merchant categories ─────────────────────────────────────────────────────
MERCHANT_CATEGORIES = {
    "electronics": 0.08,    # high chargeback risk
    "gambling": 0.12,
    "crypto": 0.10,
    "travel": 0.04,
    "retail": 0.02,
    "grocery": 0.005,
    "gas_station": 0.015,
    "restaurant": 0.01,
    "healthcare": 0.005,
    "subscription": 0.03,
}

PAYMENT_METHODS = ["credit_card", "debit_card", "ach", "wire", "crypto", "buy_now_pay_later"]
TRANSACTION_CHANNELS = ["web", "mobile_app", "in_store", "api", "atm"]
OS_LIST = ["iOS", "Android", "Windows", "macOS", "Linux"]
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]
COUNTRIES = ["US", "CA", "GB", "DE", "FR", "MX", "BR", "NG", "RU", "CN"]


# ─────────────────────────────────────────────────────────────────────────────
# Accounts
# ─────────────────────────────────────────────────────────────────────────────

def generate_accounts(n: int) -> pd.DataFrame:
    account_ids = [f"ACC_{uuid.uuid4().hex[:10].upper()}" for _ in range(n)]

    # ~5% synthetic identity accounts — will be fraud-prone
    is_synthetic = np.random.random(n) < 0.05

    credit_scores = np.where(
        is_synthetic,
        np.random.randint(300, 600, n),
        np.clip(np.random.normal(680, 80, n).astype(int), 300, 850)
    )

    email_domains = np.random.choice(
        ["gmail.com", "yahoo.com", "outlook.com", "protonmail.com", "tempmail.io", "throwaway.email"],
        n,
        p=[0.45, 0.20, 0.15, 0.08, 0.07, 0.05]
    )
    email_domain_risk = np.where(
        np.isin(email_domains, ["tempmail.io", "throwaway.email"]), 0.85,
        np.where(np.isin(email_domains, ["protonmail.com"]), 0.4, 0.1)
    )

    phone_risk = np.where(
        is_synthetic,
        np.random.uniform(0.6, 1.0, n),
        np.random.uniform(0.0, 0.3, n)
    )

    identity_consistency = np.where(
        is_synthetic,
        np.random.uniform(0.1, 0.5, n),
        np.random.uniform(0.6, 1.0, n)
    )

    prior_chargebacks = np.where(
        is_synthetic,
        np.random.poisson(3, n),
        np.random.poisson(0.1, n)
    )

    linked_accounts = np.where(
        is_synthetic,
        np.random.randint(2, 8, n),
        np.random.randint(0, 2, n)
    )

    synthetic_identity_prob = np.where(
        is_synthetic,
        np.random.uniform(0.65, 0.98, n),
        np.random.uniform(0.01, 0.15, n)
    )

    return pd.DataFrame({
        "account_id": account_ids,
        "account_age_days": np.random.randint(1, 3650, n),
        "kyc_verified": np.where(is_synthetic, np.random.random(n) < 0.3, np.random.random(n) < 0.92),
        "credit_score": credit_scores,
        "email_domain": email_domains,
        "email_domain_risk": np.round(email_domain_risk, 4),
        "phone_risk_score": np.round(phone_risk, 4),
        "identity_consistency_score": np.round(identity_consistency, 4),
        "prior_chargebacks": prior_chargebacks,
        "linked_accounts": linked_accounts,
        "synthetic_identity_probability": np.round(synthetic_identity_prob, 4),
        "is_synthetic_identity": is_synthetic,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Devices
# ─────────────────────────────────────────────────────────────────────────────

def generate_devices(n: int) -> pd.DataFrame:
    device_ids = [f"DEV_{uuid.uuid4().hex[:12].upper()}" for _ in range(n)]

    # ~8% compromised/emulated devices
    is_emulated = np.random.random(n) < 0.08
    vpn_detected = np.where(
        is_emulated,
        np.random.random(n) < 0.7,
        np.random.random(n) < 0.12
    )

    device_trust = np.where(
        is_emulated,
        np.random.uniform(0.05, 0.35, n),
        np.clip(np.random.normal(0.78, 0.15, n), 0.1, 1.0)
    )

    velocity_risk = np.where(
        is_emulated,
        np.random.uniform(0.5, 1.0, n),
        np.random.uniform(0.0, 0.3, n)
    )

    browser_fps = [hashlib.md5(f"fp_{i}_{random.random()}".encode()).hexdigest()[:16] for i in range(n)]

    return pd.DataFrame({
        "device_id": device_ids,
        "device_trust_score": np.round(device_trust, 4),
        "browser_fingerprint": browser_fps,
        "os": np.random.choice(OS_LIST, n, p=[0.30, 0.35, 0.20, 0.12, 0.03]),
        "vpn_detected": vpn_detected.astype(bool),
        "emulator_detected": is_emulated,
        "velocity_risk": np.round(velocity_risk, 4),
        "known_device": np.where(is_emulated, False, np.random.random(n) < 0.75),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Merchants
# ─────────────────────────────────────────────────────────────────────────────

def generate_merchants(n: int) -> pd.DataFrame:
    merchant_ids = [f"MER_{uuid.uuid4().hex[:8].upper()}" for _ in range(n)]
    categories = list(MERCHANT_CATEGORIES.keys())
    cat_probs = [1 / len(categories)] * len(categories)
    assigned_cats = np.random.choice(categories, n, p=cat_probs)

    chargeback_rates = np.array([MERCHANT_CATEGORIES[c] for c in assigned_cats])
    chargeback_rates += np.random.normal(0, 0.01, n)
    chargeback_rates = np.clip(chargeback_rates, 0, 0.25)

    merchant_risk = np.clip(chargeback_rates * 6 + np.random.normal(0, 0.05, n), 0, 1)

    return pd.DataFrame({
        "merchant_id": merchant_ids,
        "merchant_risk_score": np.round(merchant_risk, 4),
        "industry": assigned_cats,
        "country": np.random.choice(COUNTRIES, n, p=[0.55, 0.08, 0.07, 0.06, 0.05, 0.04, 0.04, 0.04, 0.04, 0.03]),
        "historical_chargeback_rate": np.round(chargeback_rates, 4),
        "mcc_code": np.random.randint(1000, 9999, n),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Transactions (core dataset)
# ─────────────────────────────────────────────────────────────────────────────

def _random_ip(is_vpn: bool = False) -> str:
    if is_vpn:
        # VPN exit node ranges (simulated)
        prefixes = ["185.220", "194.165", "45.142", "195.206"]
        return f"{random.choice(prefixes)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
    return f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"


def _random_geo(is_fraud: bool = False) -> tuple[float, float]:
    if is_fraud and random.random() < 0.4:
        # Fraud geo clusters: Nigeria, Russia, Eastern Europe
        fraud_geos = [
            (6.5244, 3.3792),   # Lagos
            (55.7558, 37.6176), # Moscow
            (50.4501, 30.5234), # Kyiv
            (23.8859, 45.0792), # Riyadh
        ]
        base = random.choice(fraud_geos)
        return (round(base[0] + random.gauss(0, 0.5), 4),
                round(base[1] + random.gauss(0, 0.5), 4))
    # US/Europe normal distribution
    lat = random.gauss(38.5, 8.0)
    lon = random.gauss(-98.0, 15.0)
    return (round(lat, 4), round(lon, 4))


def generate_transactions(
    n: int,
    accounts: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (transactions_df, velocity_features_df)"""

    account_ids = accounts["account_id"].tolist()
    merchant_ids = merchants["merchant_id"].tolist()
    device_ids = devices["device_id"].tolist()

    # Account lookup for fast join
    acc_lookup = accounts.set_index("account_id")
    dev_lookup = devices.set_index("device_id")
    mer_lookup = merchants.set_index("merchant_id")

    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2025, 12, 31)
    date_range_sec = int((end_dt - start_dt).total_seconds())

    records = []
    velocity_tracker: dict[str, list] = {}  # account_id → list of timestamps

    for i in range(n):
        acc_id = random.choice(account_ids)
        mer_id = random.choice(merchant_ids)
        dev_id = random.choice(device_ids)

        acc = acc_lookup.loc[acc_id]
        dev = dev_lookup.loc[dev_id]
        mer = mer_lookup.loc[mer_id]

        ts = start_dt + timedelta(seconds=random.randint(0, date_range_sec))

        # ── Fraud labeling ────────────────────────────────────────────────────
        # Combine multiple fraud signals
        fraud_score = FRAUD_RATE

        if acc["synthetic_identity_probability"] > 0.6:
            fraud_score += 0.25
        if acc["prior_chargebacks"] > 2:
            fraud_score += 0.15
        if dev["emulator_detected"]:
            fraud_score += 0.20
        if dev["vpn_detected"] and dev["velocity_risk"] > 0.5:
            fraud_score += 0.15
        if mer["merchant_risk_score"] > 0.5:
            fraud_score += 0.10
        if acc["account_age_days"] < 30:
            fraud_score += 0.12

        is_fraud = random.random() < min(fraud_score, 0.85)

        # ── Amount ────────────────────────────────────────────────────────────
        if is_fraud:
            # Fraud amounts: either very small (testing) or very large (cash-out)
            if random.random() < 0.3:
                amount = round(random.uniform(0.01, 5.00), 2)
            else:
                amount = round(random.uniform(500, 8000), 2)
        else:
            amount = round(np.random.lognormal(4.5, 1.2), 2)
            amount = min(amount, 15_000)

        # ── Geo ───────────────────────────────────────────────────────────────
        geo_lat, geo_lon = _random_geo(is_fraud=is_fraud)
        ip = _random_ip(is_vpn=bool(dev["vpn_detected"]))

        # ── Track velocity ────────────────────────────────────────────────────
        if acc_id not in velocity_tracker:
            velocity_tracker[acc_id] = []
        velocity_tracker[acc_id].append(ts)

        records.append({
            "transaction_id": f"TXN_{uuid.uuid4().hex[:14].upper()}",
            "timestamp": ts.isoformat(),
            "account_id": acc_id,
            "merchant_id": mer_id,
            "amount": amount,
            "currency": random.choice(CURRENCIES) if not is_fraud else random.choice(["USD", "EUR"]),
            "payment_method": random.choice(PAYMENT_METHODS),
            "device_id": dev_id,
            "ip_address": ip,
            "geo_lat": geo_lat,
            "geo_lon": geo_lon,
            "merchant_category": mer["industry"],
            "transaction_channel": random.choice(TRANSACTION_CHANNELS),
            "is_fraud": int(is_fraud),
        })

    txn_df = pd.DataFrame(records)
    txn_df = txn_df.sort_values("timestamp").reset_index(drop=True)

    # ── Velocity features ─────────────────────────────────────────────────────
    velocity_records = []
    for acc_id, timestamps in velocity_tracker.items():
        timestamps_sorted = sorted(timestamps)
        last_ts = timestamps_sorted[-1]
        window_1h = sum(1 for t in timestamps_sorted if (last_ts - t).total_seconds() <= 3600)
        window_24h = sum(1 for t in timestamps_sorted if (last_ts - t).total_seconds() <= 86400)

        amounts_for_acc = txn_df[txn_df["account_id"] == acc_id]["amount"]
        avg_amount = amounts_for_acc.mean() if len(amounts_for_acc) > 0 else 0.0

        velocity_records.append({
            "account_id": acc_id,
            "transactions_last_1h": window_1h,
            "transactions_last_24h": window_24h,
            "avg_transaction_amount": round(avg_amount, 2),
            "failed_attempts_last_24h": random.randint(0, 5),
            "geo_velocity_score": round(random.uniform(0, 1), 4),
        })

    velocity_df = pd.DataFrame(velocity_records)
    return txn_df, velocity_df


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Generating synthetic fintech datasets...")

    print(f"  → {N_ACCOUNTS} accounts...")
    accounts = generate_accounts(N_ACCOUNTS)
    accounts.to_csv(OUTPUT_DIR / "accounts.csv", index=False)

    print(f"  → {N_DEVICES} devices...")
    devices = generate_devices(N_DEVICES)
    devices.to_csv(OUTPUT_DIR / "devices.csv", index=False)

    print(f"  → {N_MERCHANTS} merchants...")
    merchants = generate_merchants(N_MERCHANTS)
    merchants.to_csv(OUTPUT_DIR / "merchants.csv", index=False)

    print(f"  → {N_TRANSACTIONS} transactions (this takes ~30s)...")
    transactions, velocity = generate_transactions(N_TRANSACTIONS, accounts, merchants, devices)
    transactions.to_csv(OUTPUT_DIR / "transactions.csv", index=False)
    velocity.to_csv(OUTPUT_DIR / "transaction_velocity_features.csv", index=False)

    # ── Summary stats ─────────────────────────────────────────────────────────
    fraud_count = transactions["is_fraud"].sum()
    fraud_pct = fraud_count / len(transactions) * 100
    print(f"\nDataset summary:")
    print(f"  Transactions: {len(transactions):,}")
    print(f"  Fraud:        {fraud_count:,} ({fraud_pct:.2f}%)")
    print(f"  Accounts:     {len(accounts):,}")
    print(f"  Merchants:    {len(merchants):,}")
    print(f"  Devices:      {len(devices):,}")
    print(f"\nFiles saved to: {OUTPUT_DIR}")

    # ── Save data stats for README ─────────────────────────────────────────────
    stats = {
        "n_transactions": len(transactions),
        "n_fraud": int(fraud_count),
        "fraud_rate_pct": round(fraud_pct, 2),
        "n_accounts": len(accounts),
        "n_merchants": len(merchants),
        "n_devices": len(devices),
        "date_range": {
            "start": transactions["timestamp"].min(),
            "end": transactions["timestamp"].max(),
        }
    }
    with open(OUTPUT_DIR / "dataset_stats.json", "w") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
