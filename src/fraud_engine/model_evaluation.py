from pathlib import Path
import sys
import json

import numpy as np
import joblib
import pyarrow.parquet as pq

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    confusion_matrix,
    accuracy_score,
)

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent)
)

from model_training import build_feature_matrix, INPUT_COLUMNS


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_ROOT / "outputs" / "paysim_features.parquet"

MODEL_PATH = PROJECT_ROOT / "outputs" / "fraud_sgd_bundle.joblib"

THRESHOLD_REPORT_PATH = (
    PROJECT_ROOT
    / "reports"
    / "sgd_margin_threshold_analysis.json"
)

OUTPUT_REPORT = (
    PROJECT_ROOT
    / "reports"
    / "fraud_sgd_test_metrics.json"
)

BATCH_SIZE = 200_000

TEST_START_STEP = 632
TEST_END_STEP = 743

EXPECTED_TEST_ROWS = 89_466
EXPECTED_TEST_FRAUD = 1_252


# ============================================================
# 2. CHECK REQUIRED FILES
# ============================================================

for path in [
    DATA_PATH,
    MODEL_PATH,
    THRESHOLD_REPORT_PATH,
]:
    if not path.exists():
        raise FileNotFoundError(path)

if OUTPUT_REPORT.exists():
    raise FileExistsError(
        f"Test report already exists: {OUTPUT_REPORT}"
    )


# ============================================================
# 3. LOAD MODEL AND VALIDATION THRESHOLD
# ============================================================

bundle = joblib.load(MODEL_PATH)

with THRESHOLD_REPORT_PATH.open(
    "r",
    encoding="utf-8"
) as file:
    threshold_report = json.load(file)

threshold = threshold_report[
    "threshold_candidates"
]["MAXIMUM_F1"]["threshold"]

if not np.isfinite(threshold):
    raise ValueError("Invalid decision threshold.")

model = bundle["model"]
scaler = bundle["scaler"]

parquet_file = pq.ParquetFile(DATA_PATH)


# ============================================================
# 4. TEST DATA COLLECTION
# ============================================================

test_targets = []
test_scores = []

total_rows = 0

print("=" * 70)
print("FINAL TEST EVALUATION")
print("=" * 70)

print("Model: SGDClassifier")
print("Evaluation period: Test only")
print("Steps:", TEST_START_STEP, "-", TEST_END_STEP)
print("Fixed threshold:", threshold)
print("Threshold source: Validation")
print("Model retraining: NO")
print("Threshold retuning: NO")


# ============================================================
# 5. GENERATE TEST SCORES
# ============================================================

for batch_number, batch in enumerate(
    parquet_file.iter_batches(
        columns=INPUT_COLUMNS,
        batch_size=BATCH_SIZE,
    ),
    start=1,
):

    frame = batch.to_pandas()

    steps = frame["step"].to_numpy()

    mask = (
        (steps >= TEST_START_STEP)
        & (steps <= TEST_END_STEP)
    )

    if not mask.any():
        continue

    test_frame = frame.loc[mask]

    X, y = build_feature_matrix(test_frame)

    X_scaled = scaler.transform(X)

    # Use raw scores because probability saturation was
    # observed during validation.
    scores = model.decision_function(X_scaled)

    if not np.isfinite(scores).all():
        raise ValueError("Non-finite test scores detected.")

    test_targets.append(y)
    test_scores.append(scores)

    total_rows += len(y)

    print(
        f"Batch {batch_number}: "
        f"Test rows collected: {total_rows:,}"
    )


# ============================================================
# 6. VALIDATE TEST DATA COUNTS
# ============================================================

if total_rows != EXPECTED_TEST_ROWS:
    raise ValueError(
        f"Unexpected test rows: {total_rows:,}"
    )

y_test = np.concatenate(test_targets)
scores_test = np.concatenate(test_scores)

fraud_count = int(y_test.sum())
normal_count = int(len(y_test) - fraud_count)

if fraud_count != EXPECTED_TEST_FRAUD:
    raise ValueError(
        f"Unexpected fraud count: {fraud_count:,}"
    )

print("\nTest data integrity verified.")


# ============================================================
# 7. APPLY THE FIXED VALIDATION THRESHOLD
# ============================================================

predictions = (
    scores_test >= threshold
).astype(np.int8)


# ============================================================
# 8. CALCULATE FINAL TEST METRICS
# ============================================================

precision = precision_score(
    y_test,
    predictions,
    zero_division=0,
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0,
)

f1 = f1_score(
    y_test,
    predictions,
    zero_division=0,
)

accuracy = accuracy_score(
    y_test,
    predictions,
)

average_precision = average_precision_score(
    y_test,
    scores_test,
)

tn, fp, fn, tp = confusion_matrix(
    y_test,
    predictions,
    labels=[0, 1],
).ravel()

fraud_prevalence = fraud_count / len(y_test)

precision_lift = (
    precision / fraud_prevalence
    if fraud_prevalence > 0 else None
)


# ============================================================
# 9. BUILD TEST REPORT
# ============================================================

metrics = {
    "model": "SGDClassifier",
    "evaluation_period": "FINAL_TEST",
    "prediction_scenario": "post_transaction_monitoring",

    "test_start_step": TEST_START_STEP,
    "test_end_step": TEST_END_STEP,

    "test_rows": int(total_rows),
    "test_normal": int(normal_count),
    "test_fraud": int(fraud_count),

    "fraud_prevalence": float(fraud_prevalence),

    "decision_threshold": float(threshold),
    "threshold_source": "validation_maximum_f1_raw_score",

    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "f1_score": float(f1),

    "average_precision_raw_scores": float(
        average_precision
    ),

    "precision_lift_over_prevalence": (
        float(precision_lift)
        if precision_lift is not None else None
    ),

    "confusion_matrix": {
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    },

    "predicted_fraud_transactions": int(
        predictions.sum()
    ),

    "model_retrained_on_test": False,
    "threshold_selected_using_test": False,
}


# ============================================================
# 10. SAVE REPORT
# ============================================================

with OUTPUT_REPORT.open(
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        metrics,
        file,
        indent=4,
    )


# ============================================================
# 11. DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST PERFORMANCE")
print("=" * 70)

print(f"Test transactions: {total_rows:,}")
print(f"Normal transactions: {normal_count:,}")
print(f"Fraud transactions: {fraud_count:,}")

print(f"\nDecision threshold: {threshold:.10f}")

print("\nCLASSIFICATION METRICS")

print(f"Accuracy: {accuracy:.6f}")
print(f"Precision: {precision:.6f}")
print(f"Recall: {recall:.6f}")
print(f"F1-score: {f1:.6f}")
print(f"Average Precision: {average_precision:.6f}")

print(f"\nFraud prevalence: {fraud_prevalence:.6%}")

print(
    "Precision lift over prevalence:",
    f"{precision_lift:.2f}x"
)

print("\nCONFUSION MATRIX")

print(f"True Negative: {tn:,}")
print(f"False Positive: {fp:,}")
print(f"False Negative: {fn:,}")
print(f"True Positive: {tp:,}")

print("\nTEST REPORT SAVED:")
print(OUTPUT_REPORT.resolve())

print("\nModel was not retrained.")
print("Threshold was not changed.")
print("Final test evaluation completed.")

