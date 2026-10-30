from pathlib import Path
from datetime import datetime, timezone
import json
import math
import uuid


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MONITORING_DIR = PROJECT_ROOT / "outputs" / "monitoring"

DECISION_LOG = MONITORING_DIR / "transaction_decisions.jsonl"

HIGH_ALERT_LOG = MONITORING_DIR / "high_risk_alerts.jsonl"

REVIEW_QUEUE = MONITORING_DIR / "manual_review_queue.jsonl"


# ============================================================
# 2. ALERT SYSTEM
# ============================================================

class AlertSystem:

    EXPECTED_DECISIONS = {
        "LOW": {
            "action": "MONITOR",
            "alert": False,
            "hold": False,
        },

        "MEDIUM": {
            "action": "MANUAL_REVIEW",
            "alert": False,
            "hold": False,
        },

        "HIGH": {
            "action": "ALERT_AND_SIMULATED_HOLD",
            "alert": True,
            "hold": True,
        },
    }

    def __init__(self):

        MONITORING_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        print("Alert System initialized.")
        print("Monitoring directory:", MONITORING_DIR)


    # ========================================================
    # 3. VALIDATE DECISION
    # ========================================================

    @staticmethod
    def validate_decision(decision):

        required_fields = [
            "transaction_id",
            "transaction_type",
            "amount",
            "raw_decision_score",
            "risk_level",
            "recommended_action",
            "alert_required",
            "simulated_hold",
        ]

        missing = [
            field
            for field in required_fields
            if field not in decision
        ]

        if missing:
            raise ValueError(
                f"Missing decision fields: {missing}"
            )

        if not isinstance(decision["risk_level"], str):
            raise TypeError("Risk level must be a string.")

        risk_level = decision["risk_level"]

        if risk_level not in AlertSystem.EXPECTED_DECISIONS:
            raise ValueError(
                f"Unsupported risk level: {risk_level}"
            )

        expected = AlertSystem.EXPECTED_DECISIONS[risk_level]

        if decision["recommended_action"] != expected["action"]:
            raise ValueError(
                "Decision action does not match risk level."
            )

        if decision["alert_required"] is not expected["alert"]:
            raise ValueError(
                "Alert flag does not match risk level."
            )

        if decision["simulated_hold"] is not expected["hold"]:
            raise ValueError(
                "Simulated hold flag does not match risk level."
            )

        amount = float(decision["amount"])
        score = float(decision["raw_decision_score"])

        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Invalid transaction amount.")

        if not math.isfinite(score):
            raise ValueError("Invalid raw decision score.")

        return True


    # ========================================================
    # 4. APPEND EVENT TO JSONL
    # ========================================================

    @staticmethod
    def append_event(file_path, event):

        with file_path.open(
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    event,
                    ensure_ascii=False,
                    allow_nan=False,
                )
            )

            file.write("\n")


    # ========================================================
    # 5. RECORD TRANSACTION DECISION
    # ========================================================

    def record_decision(
        self,
        decision,
        source="demo",
    ):

        self.validate_decision(decision)

        event = {
            "event_id": str(uuid.uuid4()),

            "timestamp_utc": (
                datetime.now(timezone.utc).isoformat()
            ),

            "source": source,

            "transaction_id": decision["transaction_id"],

            "transaction_type": decision["transaction_type"],

            "amount": float(decision["amount"]),

            "raw_decision_score": float(
                decision["raw_decision_score"]
            ),

            "score_type": "raw_decision_score",

            "risk_level": decision["risk_level"],

            "recommended_action": (
                decision["recommended_action"]
            ),

            "alert_required": bool(
                decision["alert_required"]
            ),

            "simulated_hold": bool(
                decision["simulated_hold"]
            ),

            "prediction_scenario": (
                "post_transaction_monitoring"
            ),

            "real_banking_action_executed": False,
        }

        # Every decision enters the audit log.
        self.append_event(
            DECISION_LOG,
            event,
        )

        # HIGH risk transactions create alert records.
        if event["risk_level"] == "HIGH":

            self.append_event(
                HIGH_ALERT_LOG,
                event,
            )

        # MEDIUM risk transactions enter the review queue.
        elif event["risk_level"] == "MEDIUM":

            self.append_event(
                REVIEW_QUEUE,
                event,
            )

        return event


    # ========================================================
    # 6. RECORD MULTIPLE DECISIONS
    # ========================================================

    def record_decisions(
        self,
        decisions,
        source="demo",
    ):

        events = []

        for decision in decisions:

            event = self.record_decision(
                decision,
                source=source,
            )

            events.append(event)

        return events


# ============================================================
# 7. MODULE CHECK
# ============================================================

if __name__ == "__main__":

    alert_system = AlertSystem()

    print("\nDecision log:", DECISION_LOG)
    print("High risk alerts:", HIGH_ALERT_LOG)
    print("Manual review queue:", REVIEW_QUEUE)

    print("\nAlert System is ready.")
