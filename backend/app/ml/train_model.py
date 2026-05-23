"""
XGBoost fraud detection model training pipeline.

Trains on synthetic fintech data with proper class-imbalance handling,
threshold tuning, SHAP background precomputation, and model registry artifacts.

Usage:
    python -m app.ml.train_model
    python -m app.ml.train_model --data-dir ../../synthetic-data --model-dir ../../models
"""

import argparse
import json
import pickle
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score,
    f1_score, confusion_matrix, average_precision_score,
)
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

DEFAULT_DATA_DIR = Path(__file__).parents[3] / "synthetic-data"
DEFAULT_MODEL_DIR = Path(__file__).parents[3] / "models"

# ─── Feature schema ───────────────────────────────────────────────────────────
# These 28 features mirror what feature_service.py builds at inference time.
FEATURE_COLUMNS = [
    # Transaction features
    "amount",
    "amount_log",
    "amount_zscore",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    # Account features
    "account_age_days",
    "account_age_log",
    "credit_score",
    "prior_chargebacks",
    "synthetic_identity_probability",
    "identity_consistency_score",
    "email_domain_risk",
    "phone_risk_score",
    "kyc_verified",
    "linked_accounts",
    # Device features
    "device_trust_score",
    "vpn_detected",
    "emulator_detected",
    "velocity_risk",
    "known_device",
    # Merchant features
    "merchant_risk_score",
    "historical_chargeback_rate",
    # Velocity features
    "transactions_last_1h",
    "transactions_last_24h",
    "avg_transaction_amount",
    "failed_attempts_last_24h",
    "geo_velocity_score",
]

LABEL_COLUMN = "is_fraud"


def load_and_merge(data_dir: Path) -> pd.DataFrame:
    print("Loading datasets...")
    txns = pd.read_csv(data_dir / "transactions.csv")
    accounts = pd.read_csv(data_dir / "accounts.csv")
    devices = pd.read_csv(data_dir / "devices.csv")
    merchants = pd.read_csv(data_dir / "merchants.csv")
    velocity = pd.read_csv(data_dir / "transaction_velocity_features.csv")

    print(f"  Transactions: {len(txns):,} | Fraud rate: {txns['is_fraud'].mean()*100:.2f}%")

    df = (
        txns
        .merge(accounts[["account_id", "account_age_days", "credit_score",
                          "kyc_verified", "email_domain_risk", "phone_risk_score",
                          "identity_consistency_score", "prior_chargebacks",
                          "linked_accounts", "synthetic_identity_probability"]],
               on="account_id", how="left")
        .merge(devices[["device_id", "device_trust_score", "vpn_detected",
                         "emulator_detected", "velocity_risk", "known_device"]],
               on="device_id", how="left")
        .merge(merchants[["merchant_id", "merchant_risk_score",
                           "historical_chargeback_rate"]],
               on="merchant_id", how="left")
        .merge(velocity[["account_id", "transactions_last_1h", "transactions_last_24h",
                          "avg_transaction_amount", "failed_attempts_last_24h",
                          "geo_velocity_score"]],
               on="account_id", how="left")
    )

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    df["amount_log"] = np.log1p(df["amount"])
    df["account_age_log"] = np.log1p(df["account_age_days"])

    # Amount z-score relative to account's own history
    acct_stats = df.groupby("account_id")["amount"].agg(["mean", "std"]).reset_index()
    acct_stats.columns = ["account_id", "acct_mean_amount", "acct_std_amount"]
    acct_stats["acct_std_amount"] = acct_stats["acct_std_amount"].fillna(1).clip(lower=1e-6)
    df = df.merge(acct_stats, on="account_id", how="left")
    df["amount_zscore"] = (df["amount"] - df["acct_mean_amount"]) / df["acct_std_amount"]

    # Boolean → int
    for col in ["vpn_detected", "emulator_detected", "known_device", "kyc_verified"]:
        df[col] = df[col].astype(int)

    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].fillna(0)

    return df


def compute_class_weight(y: pd.Series) -> float:
    neg, pos = (y == 0).sum(), (y == 1).sum()
    return neg / pos


def train(data_dir: Path, model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)

    df = load_and_merge(data_dir)
    df = engineer_features(df)

    X = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scale_pos_weight = compute_class_weight(y_train)
    print(f"\nClass ratio (neg/pos): {scale_pos_weight:.1f}x — using as scale_pos_weight")

    # ── Model params ──────────────────────────────────────────────────────────
    params = {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "gamma": 0.1,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "scale_pos_weight": scale_pos_weight,
        "use_label_encoder": False,
        "eval_metric": "aucpr",
        "tree_method": "hist",
        "random_state": 42,
        "n_jobs": -1,
    }

    print("\nTraining XGBoost classifier...")
    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # ── Threshold tuning ──────────────────────────────────────────────────────
    y_proba = model.predict_proba(X_test)[:, 1]

    thresholds = np.arange(0.3, 0.75, 0.01)
    best_f1, best_thresh = 0.0, 0.5
    for t in thresholds:
        preds = (y_proba >= t).astype(int)
        f1 = f1_score(y_test, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t

    y_pred = (y_proba >= best_thresh).astype(int)

    # ── Metrics ───────────────────────────────────────────────────────────────
    metrics = {
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
        "avg_precision": round(average_precision_score(y_test, y_proba), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "optimal_threshold": round(float(best_thresh), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "test_fraud_rate": round(float(y_test.mean()), 4),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    print("\n── Evaluation Metrics ──────────────────────────────────────")
    print(f"  ROC-AUC:        {metrics['roc_auc']}")
    print(f"  Avg Precision:  {metrics['avg_precision']}")
    print(f"  Precision:      {metrics['precision']}")
    print(f"  Recall:         {metrics['recall']}")
    print(f"  F1 Score:       {metrics['f1']}")
    print(f"  Optimal thresh: {metrics['optimal_threshold']}")
    print(f"  Confusion:\n    {metrics['confusion_matrix']}")

    # ── SHAP background dataset ───────────────────────────────────────────────
    # Precompute a 200-sample background for TreeExplainer — speeds up inference.
    print("\nPrecomputing SHAP background dataset...")
    background_sample = X_train.sample(n=200, random_state=42)
    explainer = shap.TreeExplainer(model, data=background_sample)
    shap_values_test = explainer.shap_values(X_test.head(500))

    # Global feature importance via SHAP
    mean_abs_shap = np.abs(shap_values_test).mean(axis=0)
    feature_importance = {
        feat: round(float(imp), 6)
        for feat, imp in sorted(
            zip(FEATURE_COLUMNS, mean_abs_shap),
            key=lambda x: x[1],
            reverse=True
        )
    }

    # ── Save artifacts ────────────────────────────────────────────────────────
    model_path = model_dir / "xgboost_fraud_v1.pkl"
    explainer_path = model_dir / "shap_explainer.pkl"
    background_path = model_dir / "shap_background.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f, protocol=5)

    with open(explainer_path, "wb") as f:
        pickle.dump(explainer, f, protocol=5)

    with open(background_path, "wb") as f:
        pickle.dump(background_sample, f, protocol=5)

    # Also save as XGBoost native format (faster load)
    model.save_model(str(model_dir / "xgboost_fraud_v1.json"))

    # ── Model metadata ────────────────────────────────────────────────────────
    metadata = {
        "model_name": "xgboost_fraud_v1",
        "version": "1.0.0",
        "algorithm": "XGBoostClassifier",
        "trained_at": datetime.utcnow().isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
        "params": {k: v for k, v in params.items() if k not in ["use_label_encoder"]},
        "metrics": metrics,
        "feature_importance": feature_importance,
        "artifacts": {
            "model_pkl": str(model_path),
            "model_json": str(model_dir / "xgboost_fraud_v1.json"),
            "shap_explainer": str(explainer_path),
            "shap_background": str(background_path),
        },
        "thresholds": {
            "fraud_threshold": metrics["optimal_threshold"],
            "high_risk_threshold": 0.75,
            "low_risk_threshold": 0.25,
        },
    }

    with open(model_dir / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nArtifacts saved to: {model_dir}")
    print(f"  model:      xgboost_fraud_v1.pkl ({model_path.stat().st_size // 1024} KB)")
    print(f"  explainer:  shap_explainer.pkl")
    print(f"  metadata:   model_metadata.json")
    print("\nTraining complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    train(args.data_dir, args.model_dir)
