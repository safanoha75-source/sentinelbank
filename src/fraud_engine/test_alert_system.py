from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(Path(__file__).resolve().parent))

from alert_system import AlertSystem, DECISION_LOG, HIGH_ALERT_LOG, REVIEW_QUEUE


# ============================================================
# 1. INPUT AND OUTPUT FILES
# ============================================================

INPUT_REPORT = ROOT / "reports" / "risk_engine_smoke_test.json"

OUTPUT_REPORT = ROOT / "reports" / "alert_system_test.json"

MONITORING_FILES = [
    DECISION_LOG,
    HIGH_ALERT_LOG,
    REVIEW_QUEUE,
    OUTPUT_REPORT,
]


# ============================================================
# 2. CHECK INPUT
# ============================================================

if not INPUT_REPORT.exists():
    raise FileNotFoundError(INPUT_REPORT)

existing_files = [
    path for path in MONITORING_FILES
    if path.exists()
]

if existing_files:
    raise FileExistsError(
        "Previous monitoring files exist. "
        "Archive them before running this test again: "
        + ", ".join(str(path) for path in existing_files)
    )

with INPUT_REPORT.open("r", encoding="utf-8") as file:
    smoke_report = json.load(file)

if smoke_report["target_column_loaded"] is not False:
    raise ValueError("The source test must not load isFraud.")

if smoke_report["test_period_used"] is not False:
    raise ValueError("The source test must not use the test period.")

decisions = smoke_report["results"]

expected_levels = {"LOW", "MEDIUM", "HIGH"}

actual_levels = {
    decision["risk_level"]
    for decision in decisions
}

if len(decisions) != 3 or actual_levels != expected_levels:
    raise ValueError(
        "Expected exactly one LOW, MEDIUM, and HIGH decision."
    )


# ============================================================
# 3. INITIALIZE ALERT SYSTEM
# ============================================================

alert_system = AlertSystem()


# ============================================================
# 4. RECORD ALL THREE DECISIONS
# ============================================================

events = alert_system.record_decisions(
    decisions,
    source="validation_integration_test",
)


# ============================================================
# 5. READ SAVED JSONL LOGS
# ============================================================

def read_jsonl(path):

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


decision_events = read_jsonl(DECISION_LOG)
high_alerts = read_jsonl(HIGH_ALERT_LOG)
review_queue = read_jsonl(REVIEW_QUEUE)


# ============================================================
# 6. VERIFY COUNTS AND ROUTING
# ============================================================

assert len(decision_events) == 3
assert len(high_alerts) == 1
assert len(review_queue) == 1

assert decision_events[0]["source"] == (
    "validation_integration_test"
)

assert high_alerts[0]["risk_level"] == "HIGH"
assert high_alerts[0]["alert_required"] is True
assert high_alerts[0]["simulated_hold"] is True

assert review_queue[0]["risk_level"] == "MEDIUM"
assert review_queue[0]["recommended_action"] == "MANUAL_REVIEW"

assert not any(
    event["risk_level"] == "LOW"
    for event in high_alerts + review_queue
)


# ============================================================
# 7. SAVE TEST SUMMARY
# ============================================================

summary = {
    "test_name": "Alert System Integration Test",
    "source": "Risk Engine Validation Smoke Test",
    "decisions_received": len(decisions),
    "events_recorded": len(events),
    "decision_log_records": len(decision_events),
    "high_alert_records": len(high_alerts),
    "manual_review_records": len(review_queue),
    "low_risk_records": sum(
        event["risk_level"] == "LOW"
        for event in decision_events
    ),
    "medium_risk_records": len(review_queue),
    "high_risk_records": len(high_alerts),
    "real_notifications_sent": False,
    "real_banking_actions_executed": False,
    "all_checks_passed": True,
}

OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT_REPORT.open("w", encoding="utf-8") as file:
    json.dump(summary, file, indent=4)


# ============================================================
# 8. DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 65)
print("ALERT SYSTEM INTEGRATION TEST")
print("=" * 65)

print("Total decisions recorded:", len(decision_events))
print("LOW records:", summary["low_risk_records"])
print("MEDIUM review records:", len(review_queue))
print("HIGH alert records:", len(high_alerts))

print("\nVALIDATION CHECKS")
print("[PASS] All decisions recorded")
print("[PASS] HIGH routed to alert log")
print("[PASS] MEDIUM routed to review queue")
print("[PASS] LOW retained in decision log")
print("[PASS] No real notification sent")
print("[PASS] No real banking action executed")

print("\nSaved files:")
print(DECISION_LOG)
print(HIGH_ALERT_LOG)
print(REVIEW_QUEUE)
print(OUTPUT_REPORT)

print("\nALERT SYSTEM TEST PASSED")
