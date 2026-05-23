"""
Rule-based risk engine — deterministic checks that run alongside the ML model.

Rules can OVERRIDE a low ML score (hard blocks) or BOOST a medium score.
The final decision engine in inference_service.py combines both signals.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleSeverity(str, Enum):
    CRITICAL = "CRITICAL"   # Force BLOCK regardless of ML score
    HIGH = "HIGH"           # Push score toward HIGH/BLOCK
    MEDIUM = "MEDIUM"       # Informational, adds to risk factors
    LOW = "LOW"


@dataclass
class RuleResult:
    triggered: bool
    rule_id: str
    severity: RuleSeverity
    reason: str
    score_boost: float = 0.0  # Added to ML prob if triggered


RULES: list[dict] = [
    {
        "id": "IMPOSSIBLE_GEO_VELOCITY",
        "severity": RuleSeverity.CRITICAL,
        "score_boost": 0.50,
        "description": "Transactions in physically impossible locations within <10 min",
    },
    {
        "id": "VPN_PLUS_EMULATOR",
        "severity": RuleSeverity.HIGH,
        "score_boost": 0.35,
        "description": "VPN detected AND emulator detected simultaneously",
    },
    {
        "id": "VELOCITY_SPIKE",
        "severity": RuleSeverity.HIGH,
        "score_boost": 0.25,
        "description": ">10 transactions in last hour from same account",
    },
    {
        "id": "NEW_DEVICE_HIGH_AMOUNT",
        "severity": RuleSeverity.HIGH,
        "score_boost": 0.20,
        "description": "Unrecognized device + transaction amount > $2,000",
    },
    {
        "id": "HIGH_RISK_MERCHANT",
        "severity": RuleSeverity.MEDIUM,
        "score_boost": 0.15,
        "description": "Merchant risk score exceeds 0.70",
    },
    {
        "id": "SYNTHETIC_IDENTITY",
        "severity": RuleSeverity.HIGH,
        "score_boost": 0.30,
        "description": "Account synthetic identity probability > 0.70",
    },
    {
        "id": "UNVERIFIED_KYC_HIGH_AMOUNT",
        "severity": RuleSeverity.MEDIUM,
        "score_boost": 0.18,
        "description": "KYC not verified + amount > $1,000",
    },
    {
        "id": "PRIOR_CHARGEBACKS",
        "severity": RuleSeverity.MEDIUM,
        "score_boost": 0.12,
        "description": "Account has >3 prior chargebacks",
    },
    {
        "id": "FAILED_ATTEMPTS_SPIKE",
        "severity": RuleSeverity.MEDIUM,
        "score_boost": 0.15,
        "description": ">3 failed payment attempts in last 24h",
    },
    {
        "id": "NEW_ACCOUNT_HIGH_AMOUNT",
        "severity": RuleSeverity.MEDIUM,
        "score_boost": 0.15,
        "description": "Account < 30 days old + amount > $500",
    },
]


class FraudRulesService:
    def evaluate(
        self,
        features: dict[str, Any],
        transaction: dict[str, Any],
    ) -> tuple[list[RuleResult], float]:
        """
        Returns (triggered_rules, total_score_boost).
        """
        results = []
        total_boost = 0.0

        for rule_def in RULES:
            result = self._check_rule(rule_def, features, transaction)
            if result.triggered:
                results.append(result)
                total_boost += rule_def["score_boost"]

        return results, min(total_boost, 0.60)  # cap boost to prevent over-inflation

    def _check_rule(
        self,
        rule_def: dict,
        features: dict[str, Any],
        transaction: dict[str, Any],
    ) -> RuleResult:
        rule_id = rule_def["id"]
        triggered = False

        if rule_id == "IMPOSSIBLE_GEO_VELOCITY":
            triggered = features.get("geo_velocity_score", 0) > 0.90

        elif rule_id == "VPN_PLUS_EMULATOR":
            triggered = (
                features.get("vpn_detected", 0) > 0.5
                and features.get("emulator_detected", 0) > 0.5
            )

        elif rule_id == "VELOCITY_SPIKE":
            triggered = features.get("transactions_last_1h", 0) > 10

        elif rule_id == "NEW_DEVICE_HIGH_AMOUNT":
            triggered = (
                features.get("known_device", 1) < 0.5
                and features.get("amount", 0) > 2000
            )

        elif rule_id == "HIGH_RISK_MERCHANT":
            triggered = features.get("merchant_risk_score", 0) > 0.70

        elif rule_id == "SYNTHETIC_IDENTITY":
            triggered = features.get("synthetic_identity_probability", 0) > 0.70

        elif rule_id == "UNVERIFIED_KYC_HIGH_AMOUNT":
            triggered = (
                features.get("kyc_verified", 1) < 0.5
                and features.get("amount", 0) > 1000
            )

        elif rule_id == "PRIOR_CHARGEBACKS":
            triggered = features.get("prior_chargebacks", 0) > 3

        elif rule_id == "FAILED_ATTEMPTS_SPIKE":
            triggered = features.get("failed_attempts_last_24h", 0) > 3

        elif rule_id == "NEW_ACCOUNT_HIGH_AMOUNT":
            triggered = (
                features.get("account_age_days", 365) < 30
                and features.get("amount", 0) > 500
            )

        return RuleResult(
            triggered=triggered,
            rule_id=rule_id,
            severity=rule_def["severity"],
            reason=rule_def["description"],
            score_boost=rule_def["score_boost"] if triggered else 0.0,
        )

    @staticmethod
    def has_critical_rule(rule_results: list[RuleResult]) -> bool:
        return any(r.severity == RuleSeverity.CRITICAL for r in rule_results)
