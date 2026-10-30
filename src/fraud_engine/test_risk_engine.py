from pathlib import Path
import sys
import json

import numpy as np
import pandas as pd

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent)
)

from risk_engine import FraudRiskEngine


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

SOURCE_PATH = (
    ROOT / "PS_20174392719_1491204439457_log.csv"
)

REPORT_PATH = (
    ROOT / "reports" / "risk_engine_smoke_test.json"
)

BATCH_SIZE = 200_000

SOURCE_COLUMNS = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
]

DTYPES = {
    "step": "int16",
    "type": "string",
    "amount": "float64",
    "oldbalanceOrg": "float64",
    "newbalanceOrig": "float64",
    "oldbalanceDest": "float64",
    "newbalanceDest": "float64",
}


# ============================================================
# 2. BUILD BATCH FEATURES
# ============================================================

def build_input_matrix(frame, categories):

    transaction_types = (
        frame["type"].astype(str).to_numpy()
    )

    unknown_types = (
        set(transaction_types) - set(categories)
    )

    if unknown_types:
        raise ValueError(
            f"Unknown transaction types: {unknown_types}"
        )

    amount = frame["amount"].to_numpy(
        dtype=np.float64
    )

    old_origin = frame["oldbalanceOrg"].to_numpy(
        dtype=np.float64
    )

    new_origin = frame["newbalanceOrig"].to_numpy(
        dtype=np.float64
    )

    old_destination = frame["oldbalanceDest"].to_numpy(
        dtype=np.float64
    )

    new_destination = frame["newbalanceDest"].to_numpy(
        dtype=np.float64
    )

    origin_error = (
        old_origin - amount - new_origin
    )

    destination_error = (
        old_destination + amount - new_destination
    )

    origin_error_log = (
        np.sign(origin_error)
        * np.log1p(np.abs(origin_error))
    )

    destination_error_log = (
        np.sign(destination_error)
        * np.log1p(np.abs(destination_error))
    )

    numeric_features = np.column_stack([
        np.log1p(amount),

        (
            (old_origin > 0)
            & (new_origin == 0)
        ).astype(np.float64),

        origin_error_log,
        destination_error_log,

        (np.abs(origin_error) > 0.01).astype(np.float64),

        (np.abs(destination_error) > 0.01).astype(np.float64),
    ])

    categorical_features = np.column_stack([
        (transaction_types == category).astype(np.float64)
        for category in categories
    ])

    X = np.column_stack([
        numeric_features,
        categorical_features,
    ])

    if not np.isfinite(X).all():
        raise ValueError("Invalid feature values detected.")

    return X


# ============================================================
# 3. INITIALIZE ENGINE
# ============================================================

if not SOURCE_PATH.exists():
    raise FileNotFoundError(SOURCE_PATH)

if REPORT_PATH.exists():
    raise FileExistsError(
        f"Report already exists: {REPORT_PATH}"
    )

engine = FraudRiskEngine()

categories = engine.transaction_types

candidates = {
    "LOW": None,
    "MEDIUM": None,
    "HIGH": None,
}

actions = {
    "LOW": "MONITOR",
    "MEDIUM": "MANUAL_REVIEW",
    "HIGH": "ALERT_AND_SIMULATED_HOLD",
}

print("=" * 70)
print("RISK ENGINE INTEGRATION TEST")
print("=" * 70)

print("Source: Original PaySim CSV")
print("Period: Validation only")
print("isFraud: NOT LOADED")
print("Test period: NOT USED")
print("Model retraining: NO")


# ============================================================
# 4. READ ORIGINAL TRANSACTIONS IN CHUNKS
# ============================================================

reader = pd.read_csv(
    SOURCE_PATH,
    usecols=SOURCE_COLUMNS,
    dtype=DTYPES,
    chunksize=BATCH_SIZE,
    encoding="utf-8-sig",
)

for batch_number, chunk in enumerate(reader, start=1):

    mask = (
        (chunk["step"] >= 521)
        & (chunk["step"] <= 631)
    )

    if not mask.any():
        continue

    validation = (
        chunk.loc[mask]
        .reset_index(drop=True)
    )

    X = build_input_matrix(
        validation,
        categories,
    )

    scores = engine.model.decision_function(
        engine.scaler.transform(X)
    )

    low_threshold = engine.medium_threshold
    high_threshold = engine.high_threshold

    risk_masks = {
        "LOW": scores < low_threshold,

        "MEDIUM": (
            (scores >= low_threshold)
            & (scores < high_threshold)
        ),

        "HIGH": scores >= high_threshold,
    }

    for risk_level, risk_mask in risk_masks.items():

        if candidates[risk_level] is not None:
            continue

        indexes = np.flatnonzero(risk_mask)

        if len(indexes) == 0:
            continue

        index = int(indexes[0])

        row = validation.iloc[index]

        candidates[risk_level] = {
            "transaction_id": (
                f"VALIDATION_{risk_level}_SAMPLE"
            ),

            "step": int(row["step"]),
            "type": str(row["type"]),
            "amount": float(row["amount"]),

            "oldbalanceOrg": float(
                row["oldbalanceOrg"]
            ),

            "newbalanceOrig": float(
                row["newbalanceOrig"]
            ),

            "oldbalanceDest": float(
                row["oldbalanceDest"]
            ),

            "newbalanceDest": float(
                row["newbalanceDest"]
            ),

            "_expected_score": float(scores[index]),
        }

    found = sum(
        value is not None
        for value in candidates.values()
    )

    print(
        f"Batch {batch_number}: "
        f"Risk-level samples found: {found}/3"
    )

    if found == 3:
        break


# ============================================================
# 5. VERIFY ALL THREE RISK LEVELS
# ============================================================

missing = [
    risk
    for risk, transaction in candidates.items()
    if transaction is None
]

if missing:
    raise ValueError(
        f"Could not find examples for: {missing}"
    )


# ============================================================
# 6. SEND TRANSACTIONS TO THE REAL RISK ENGINE
# ============================================================

results = []

print("\n" + "=" * 70)
print("RISK ENGINE DECISIONS")
print("=" * 70)

for expected_risk, transaction in candidates.items():

    expected_score = transaction.pop(
        "_expected_score"
    )

    result = engine.score_transaction(transaction)

    if result["risk_level"] != expected_risk:
        raise AssertionError(
            f"Expected {expected_risk}, "
            f"received {result['risk_level']}"
        )

    if result["recommended_action"] != actions[expected_risk]:
        raise AssertionError(
            f"Incorrect action for {expected_risk}"
        )

    if not np.isclose(
        result["raw_decision_score"],
        expected_score,
        rtol=1e-9,
        atol=1e-8,
    ):
        raise AssertionError(
            "Risk Engine score differs from batch score."
        )

    print(f"\nRisk level: {result['risk_level']}")
    print(f"Transaction type: {result['transaction_type']}")
    print(f"Amount: {result['amount']:,.2f}")
    print(
        "Raw Score:",
        f"{result['raw_decision_score']:.8f}"
    )
    print(f"Action: {result['recommended_action']}")
    print(f"Alert: {result['alert_required']}")
    print(f"Simulated Hold: {result['simulated_hold']}")

    results.append(result)


# ============================================================
# 7. SAVE TEST REPORT
# ============================================================

report = {
    "test_name": "Risk Engine Integration Test",

    "source": "Original PaySim CSV",

    "period": "Validation",

    "target_column_loaded": False,

    "test_period_used": False,

    "risk_thresholds": {
        "medium": engine.medium_threshold,
        "high": engine.high_threshold,
    },

    "results": results,

    "risk_levels_passed": [
        "LOW",
        "MEDIUM",
        "HIGH",
    ],

    "all_checks_passed": True,

    "real_banking_actions_executed": False,
}

with REPORT_PATH.open(
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        report,
        file,
        indent=4,
    )


print("\n" + "=" * 70)
print("RISK ENGINE INTEGRATION TEST PASSED")
print("=" * 70)

print("LOW: PASS")
print("MEDIUM: PASS")
print("HIGH: PASS")

print("\nSaved report:")
print(REPORT_PATH.resolve())

