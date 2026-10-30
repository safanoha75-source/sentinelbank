from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
)


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_ROOT / "outputs" / "paysim_features.parquet"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
REPORT_DIR = PROJECT_ROOT / "reports"

BUNDLE_PATH = OUTPUT_DIR / "fraud_sgd_bundle.joblib"
METRICS_PATH = REPORT_DIR / "fraud_sgd_validation_metrics.json"

BATCH_SIZE = 200_000

TRAIN_END = 520
VALIDATION_START = 521
VALIDATION_END = 631

TYPE_CATEGORIES = [
    "CASH_IN",
    "CASH_OUT",
    "DEBIT",
    "PAYMENT",
    "TRANSFER",
]

INPUT_COLUMNS = [
    "step",
    "type",
    "log_amount",
    "orig_balance_emptied",
    "orig_balance_error",
    "dest_balance_error",
    "orig_balance_mismatch",
    "dest_balance_mismatch",
    "isFraud",
]

FEATURE_NAMES = [
    "log_amount",
    "orig_balance_emptied",
    "orig_balance_error_signed_log",
    "dest_balance_error_signed_log",
    "orig_balance_mismatch",
    "dest_balance_mismatch",
] + [
    f"type_{category}"
    for category in TYPE_CATEGORIES
]


# ============================================================
# 2. FEATURE MATRIX BUILDER
# ============================================================

def build_feature_matrix(frame):

    transaction_types = frame["type"].astype(str).to_numpy()

    unknown_types = set(transaction_types) - set(TYPE_CATEGORIES)

    if unknown_types:
        raise ValueError(
            f"Unexpected transaction types: {unknown_types}"
        )

    origin_error = frame["orig_balance_error"].to_numpy(
        dtype=np.float64
    )

    destination_error = frame["dest_balance_error"].to_numpy(
        dtype=np.float64
    )

    # Signed logarithmic transformation preserves error direction.
    origin_error_log = (
        np.sign(origin_error)
        * np.log1p(np.abs(origin_error))
    )

    destination_error_log = (
        np.sign(destination_error)
        * np.log1p(np.abs(destination_error))
    )

    numeric_features = np.column_stack([
        frame["log_amount"].to_numpy(dtype=np.float64),
        frame["orig_balance_emptied"].to_numpy(dtype=np.float64),
        origin_error_log,
        destination_error_log,
        frame["orig_balance_mismatch"].to_numpy(dtype=np.float64),
        frame["dest_balance_mismatch"].to_numpy(dtype=np.float64),
    ])

    categorical_features = np.column_stack([
        (transaction_types == category).astype(np.float64)
        for category in TYPE_CATEGORIES
    ])

    X = np.column_stack([
        numeric_features,
        categorical_features,
    ])

    y = frame["isFraud"].to_numpy(dtype=np.int8)

    if not np.isfinite(X).all():
        raise ValueError("Non-finite model feature detected.")

    return X, y


# ============================================================
# 3. VALIDATE INPUT FILES
# ============================================================

def main():

    if not DATA_PATH.exists():
        raise FileNotFoundError(DATA_PATH)

    if BUNDLE_PATH.exists() or METRICS_PATH.exists():
        raise FileExistsError(
            "A previous model or metrics report already exists. "
            "Rename the existing files before running again."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    parquet_file = pq.ParquetFile(DATA_PATH)

    print("=" * 70)
    print("PAYSim BASELINE FRAUD MODEL")
    print("=" * 70)

    print("Input:", DATA_PATH)
    print("Training steps:", f"1 to {TRAIN_END}")
    print(
        "Validation steps:",
        f"{VALIDATION_START} to {VALIDATION_END}"
    )
    print("Model: SGDClassifier with log_loss")
    print("Features:", len(FEATURE_NAMES))


    # ========================================================
    # 4. FIRST PASS: FIT SCALER ON TRAINING DATA ONLY
    # ========================================================

    scaler = StandardScaler()

    training_counts = np.zeros(2, dtype=np.int64)
    scaler_rows = 0

    print("\nPHASE A: Fitting StandardScaler")
    print("Only training-period transactions are used.")

    for batch_number, batch in enumerate(
        parquet_file.iter_batches(
            columns=INPUT_COLUMNS,
            batch_size=BATCH_SIZE,
        ),
        start=1,
    ):

        frame = batch.to_pandas()

        mask = frame["step"].to_numpy() <= TRAIN_END

        if not mask.any():
            continue

        training_frame = frame.loc[mask]

        X, y = build_feature_matrix(training_frame)

        scaler.partial_fit(X)

        training_counts += np.bincount(
            y,
            minlength=2,
        )

        scaler_rows += len(y)

        print(
            f"Scaler batch {batch_number}: "
            f"{len(y):,} training rows"
        )

    if scaler_rows != 6_082_007:
        raise ValueError(
            f"Unexpected training rows: {scaler_rows:,}"
        )

    if training_counts[1] != 5_781:
        raise ValueError(
            f"Unexpected training fraud count: "
            f"{training_counts[1]:,}"
        )

    if (training_counts == 0).any():
        raise ValueError("A target class is missing from training.")

    print("\nTraining distribution:")
    print("Normal:", f"{training_counts[0]:,}")
    print("Fraud:", f"{training_counts[1]:,}")


    # ========================================================
    # 5. CLASS WEIGHTS
    # ========================================================

    total_training = int(training_counts.sum())

    class_weights = {
        0: total_training / (2 * training_counts[0]),
        1: total_training / (2 * training_counts[1]),
    }

    print("\nClass weights:")
    print(class_weights)


    # ========================================================
    # 6. CREATE SGD LOGISTIC MODEL
    # ========================================================

    model = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=0.00001,
        learning_rate="optimal",
        class_weight=class_weights,
        random_state=42,
        average=True,
    )


    # ========================================================
    # 7. SECOND PASS: TRAIN THE MODEL
    # ========================================================

    print("\nPHASE B: Model training")

    rng = np.random.default_rng(42)
    first_batch = True
    trained_rows = 0

    for batch_number, batch in enumerate(
        parquet_file.iter_batches(
            columns=INPUT_COLUMNS,
            batch_size=BATCH_SIZE,
        ),
        start=1,
    ):

        frame = batch.to_pandas()

        mask = frame["step"].to_numpy() <= TRAIN_END

        if not mask.any():
            continue

        training_frame = frame.loc[mask]

        X, y = build_feature_matrix(training_frame)

        X_scaled = scaler.transform(X)

        # Shuffle rows within each batch.
        order = rng.permutation(len(y))

        X_scaled = X_scaled[order]
        y = y[order]

        if first_batch:
            model.partial_fit(
                X_scaled,
                y,
                classes=np.array([0, 1], dtype=np.int8),
            )
            first_batch = False
        else:
            model.partial_fit(X_scaled, y)

        trained_rows += len(y)

        print(
            f"Training batch {batch_number}: "
            f"Total trained: {trained_rows:,}"
        )

    if trained_rows != 6_082_007:
        raise ValueError("Training row count does not match audit.")


    # ========================================================
    # 8. THIRD PASS: VALIDATION PREDICTIONS
    # ========================================================

    print("\nPHASE C: Validation")

    validation_targets = []
    validation_probabilities = []

    validation_rows = 0

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
            (steps >= VALIDATION_START)
            & (steps <= VALIDATION_END)
        )

        if not mask.any():
            continue

        validation_frame = frame.loc[mask]

        X, y = build_feature_matrix(validation_frame)

        X_scaled = scaler.transform(X)

        probabilities = model.predict_proba(X_scaled)[:, 1]

        validation_targets.append(y)
        validation_probabilities.append(probabilities)

        validation_rows += len(y)

        print(
            f"Validation batch {batch_number}: "
            f"Total evaluated: {validation_rows:,}"
        )

    y_validation = np.concatenate(validation_targets)
    probability_validation = np.concatenate(
        validation_probabilities
    )

    if validation_rows != 191_147:
        raise ValueError(
            f"Unexpected validation rows: {validation_rows:,}"
        )

    if int(y_validation.sum()) != 1_180:
        raise ValueError("Validation fraud count does not match audit.")


    # ========================================================
    # 9. THRESHOLD SELECTION USING VALIDATION ONLY
    # ========================================================

    precision_values, recall_values, thresholds = (
        precision_recall_curve(
            y_validation,
            probability_validation,
        )
    )

    f1_values = (
        2 * precision_values[:-1] * recall_values[:-1]
        / (
            precision_values[:-1]
            + recall_values[:-1]
            + 1e-12
        )
    )

    best_index = int(np.argmax(f1_values))

    selected_threshold = float(thresholds[best_index])


    # ========================================================
    # 10. VALIDATION METRICS
    # ========================================================

    predictions = (
        probability_validation >= selected_threshold
    ).astype(np.int8)

    precision = precision_score(
        y_validation,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_validation,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_validation,
        predictions,
        zero_division=0,
    )

    average_precision = average_precision_score(
        y_validation,
        probability_validation,
    )

    matrix = confusion_matrix(
        y_validation,
        predictions,
        labels=[0, 1],
    )

    tn, fp, fn, tp = matrix.ravel()


    # ========================================================
    # 11. SAVE MODEL BUNDLE
    # ========================================================

    bundle = {
        "model": model,
        "scaler": scaler,
        "feature_names": FEATURE_NAMES,
        "threshold": selected_threshold,
        "transaction_types": TYPE_CATEGORIES,
        "prediction_scenario": "post_transaction_monitoring",
        "train_end_step": TRAIN_END,
        "validation_start_step": VALIDATION_START,
        "validation_end_step": VALIDATION_END,
    }

    joblib.dump(
        bundle,
        BUNDLE_PATH,
        compress=3,
    )


    # ========================================================
    # 12. SAVE VALIDATION METRICS
    # ========================================================

    metrics = {
        "model": "SGDClassifier",
        "loss": "log_loss",
        "prediction_scenario": "post_transaction_monitoring",
        "training_rows": int(trained_rows),
        "training_normal": int(training_counts[0]),
        "training_fraud": int(training_counts[1]),
        "validation_rows": int(validation_rows),
        "validation_fraud": int(y_validation.sum()),
        "selected_threshold": selected_threshold,
        "threshold_selection_method": "maximum_validation_f1",
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "average_precision": float(average_precision),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "feature_names": FEATURE_NAMES,
        "test_data_used": False,
    }

    with METRICS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            indent=4,
        )


    # ========================================================
    # 13. FINAL REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("BASELINE MODEL TRAINING COMPLETED")
    print("=" * 70)

    print(f"Training rows: {trained_rows:,}")
    print(f"Validation rows: {validation_rows:,}")

    print(f"\nSelected threshold: {selected_threshold:.8f}")

    print("\nVALIDATION METRICS")
    print(f"Precision: {precision:.6f}")
    print(f"Recall: {recall:.6f}")
    print(f"F1-score: {f1:.6f}")
    print(f"Average Precision: {average_precision:.6f}")

    print("\nCONFUSION MATRIX")
    print(f"True Negative : {tn:,}")
    print(f"False Positive: {fp:,}")
    print(f"False Negative: {fn:,}")
    print(f"True Positive : {tp:,}")

    print("\nSaved model:")
    print(BUNDLE_PATH.resolve())

    print("\nSaved validation report:")
    print(METRICS_PATH.resolve())

    print("\nThe test dataset has NOT been used.")

    print("\nBaseline experiment completed successfully.")


if __name__ == "__main__":
    main()
