from pathlib import Path
import json

import joblib
import numpy as np


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = PROJECT_ROOT / "outputs" / "fraud_sgd_bundle.joblib"

POLICY_PATH = PROJECT_ROOT / "outputs" / "risk_policy.json"


# Must match the training feature order exactly.
EXPECTED_FEATURES = [
    "log_amount",
    "orig_balance_emptied",
    "orig_balance_error_signed_log",
    "dest_balance_error_signed_log",
    "orig_balance_mismatch",
    "dest_balance_mismatch",
    "type_CASH_IN",
    "type_CASH_OUT",
    "type_DEBIT",
    "type_PAYMENT",
    "type_TRANSFER",
]


# ============================================================
# 2. FRAUD RISK ENGINE
# ============================================================

class FraudRiskEngine:

    def __init__(self):

        if not MODEL_PATH.exists():
            raise FileNotFoundError(MODEL_PATH)

        if not POLICY_PATH.exists():
            raise FileNotFoundError(POLICY_PATH)

        # Load the saved model and preprocessing scaler.
        self.bundle = joblib.load(MODEL_PATH)

        self.model = self.bundle["model"]
        self.scaler = self.bundle["scaler"]

        # Load the risk policy.
        with POLICY_PATH.open("r", encoding="utf-8") as file:
            self.policy = json.load(file)

        self.transaction_types = self.bundle["transaction_types"]

        self.medium_threshold = float(
            self.policy["thresholds"]["medium"]
        )

        self.high_threshold = float(
            self.policy["thresholds"]["high"]
        )

        # Verify feature compatibility.
        if self.bundle["feature_names"] != EXPECTED_FEATURES:
            raise ValueError(
                "Model feature order does not match Risk Engine."
            )

        if self.high_threshold <= self.medium_threshold:
            raise ValueError("Invalid risk thresholds.")


    # ========================================================
    # 3. INPUT VALIDATION
    # ========================================================

    @staticmethod
    def validate_transaction(transaction):

        if not isinstance(transaction, dict):
            raise TypeError("Transaction must be a dictionary.")

        required_fields = [
            "type",
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
        ]

        missing = [
            field for field in required_fields
            if field not in transaction
        ]

        if missing:
            raise ValueError(
                f"Missing transaction fields: {missing}"
            )

        transaction_type = transaction["type"]

        if transaction_type not in [
            "CASH_IN",
            "CASH_OUT",
            "DEBIT",
            "PAYMENT",
            "TRANSFER",
        ]:
            raise ValueError(
                f"Unsupported transaction type: {transaction_type}"
            )

        numeric_fields = [
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
        ]

        values = {}

        for field in numeric_fields:

            try:
                value = float(transaction[field])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Invalid numeric value for {field}."
                )

            if not np.isfinite(value):
                raise ValueError(
                    f"Non-finite value detected in {field}."
                )

            if value < 0:
                raise ValueError(
                    f"Negative value detected in {field}."
                )

            values[field] = value

        return transaction_type, values


    # ========================================================
    # 4. FEATURE ENGINEERING FOR ONE TRANSACTION
    # ========================================================

    def build_transaction_features(self, transaction):

        transaction_type, values = (
            self.validate_transaction(transaction)
        )

        amount = values["amount"]

        old_origin = values["oldbalanceOrg"]
        new_origin = values["newbalanceOrig"]

        old_destination = values["oldbalanceDest"]
        new_destination = values["newbalanceDest"]

        # H1: Transaction amount transformation.
        log_amount = np.log1p(amount)

        # H2: Origin balance emptied.
        origin_emptied = int(
            old_origin > 0 and new_origin == 0
        )

        # H3: Origin balance discrepancy.
        origin_error = (
            old_origin - amount - new_origin
        )

        # H4: Destination balance discrepancy.
        destination_error = (
            old_destination + amount - new_destination
        )

        origin_mismatch = int(
            abs(origin_error) > 0.01
        )

        destination_mismatch = int(
            abs(destination_error) > 0.01
        )

        # Signed logarithmic transformations.
        origin_error_log = (
            np.sign(origin_error)
            * np.log1p(abs(origin_error))
        )

        destination_error_log = (
            np.sign(destination_error)
            * np.log1p(abs(destination_error))
        )

        # One-hot encoding using the original training order.
        type_features = [
            int(transaction_type == category)
            for category in self.transaction_types
        ]

        feature_values = [
            log_amount,
            origin_emptied,
            origin_error_log,
            destination_error_log,
            origin_mismatch,
            destination_mismatch,
            *type_features,
        ]

        X = np.asarray(
            feature_values,
            dtype=np.float64
        ).reshape(1, -1)

        if not np.isfinite(X).all():
            raise ValueError("Invalid engineered feature values.")

        return X


    # ========================================================
    # 5. CALCULATE RAW FRAUD SCORE
    # ========================================================

    def calculate_raw_score(self, transaction):

        X = self.build_transaction_features(transaction)

        X_scaled = self.scaler.transform(X)

        # Use raw scores, not saturated sigmoid probabilities.
        score = float(
            self.model.decision_function(X_scaled)[0]
        )

        return score


    # ========================================================
    # 6. ASSIGN RISK LEVEL AND ACTION
    # ========================================================

    def score_transaction(self, transaction):

        score = self.calculate_raw_score(transaction)

        if score >= self.high_threshold:

            risk_level = "HIGH"
            action = "ALERT_AND_SIMULATED_HOLD"
            alert_required = True
            simulated_hold = True

        elif score >= self.medium_threshold:

            risk_level = "MEDIUM"
            action = "MANUAL_REVIEW"
            alert_required = False
            simulated_hold = False

        else:

            risk_level = "LOW"
            action = "MONITOR"
            alert_required = False
            simulated_hold = False

        return {
            "transaction_id": transaction.get(
                "transaction_id",
                "UNKNOWN"
            ),

            "transaction_type": transaction["type"],

            "amount": float(transaction["amount"]),

            "raw_decision_score": score,

            "risk_level": risk_level,

            "recommended_action": action,

            "alert_required": alert_required,

            "simulated_hold": simulated_hold,

            "score_type": "raw_decision_score",

            "prediction_scenario": (
                "post_transaction_monitoring"
            ),

            "note": (
                "Simulated monitoring decision only. "
                "No real banking transaction is blocked."
            ),
        }


# ============================================================
# 7. MODULE READY
# ============================================================

if __name__ == "__main__":

    engine = FraudRiskEngine()

    print("=" * 65)
    print("PAYSim FRAUD RISK ENGINE")
    print("=" * 65)

    print("Model loaded successfully.")
    print("Risk policy loaded successfully.")

    print("Medium threshold:", engine.medium_threshold)
    print("High threshold:", engine.high_threshold)

    print("Expected features:", len(EXPECTED_FEATURES))

    print("\nRisk Engine initialized successfully.")
