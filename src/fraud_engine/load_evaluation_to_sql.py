from pathlib import Path
import json

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from db_connection import get_connection


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

SOURCE_PATH = ROOT / "PS_20174392719_1491204439457_log.csv"

MODEL_PATH = ROOT / "outputs" / "fraud_sgd_bundle.joblib"

POLICY_PATH = ROOT / "outputs" / "risk_policy.json"

TEST_REPORT_PATH = ROOT / "reports" / "fraud_sgd_test_metrics.json"

OUTPUT_REPORT = ROOT / "reports" / "sql_load_report.json"

CHUNK_SIZE = 100_000
SQL_INSERT_BATCH_SIZE = 5_000

MODEL_NAME = "SGDClassifier"
MODEL_VERSION = "sgd_logloss_raw_v1"

START_VALIDATION = 521
END_VALIDATION = 631

START_TEST = 632
END_TEST = 743

EXPECTED_COUNTS = {
    "VALIDATION": {
        "transactions": 191_147,
        "fraud": 1_180,
    },
    "TEST": {
        "transactions": 89_466,
        "fraud": 1_252,
    },
}

CSV_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]

CSV_DTYPES = {
    "step": "int16",
    "type": "string",
    "amount": "float64",
    "nameOrig": "string",
    "oldbalanceOrg": "float64",
    "newbalanceOrig": "float64",
    "nameDest": "string",
    "oldbalanceDest": "float64",
    "newbalanceDest": "float64",
    "isFraud": "int8",
    "isFlaggedFraud": "int8",
}


# ============================================================
# 2. BUILD FEATURES WITHOUT USING THE TARGET
# ============================================================

def build_inference_matrix(frame, categories):
    """
    Build the same model input features used during training.

    isFraud is deliberately excluded from this function.
    """

    transaction_types = (
        frame["type"].astype(str).to_numpy()
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
# 3. CHUNKED SQL INSERT HELPER
# ============================================================

def insert_in_batches(cursor, sql, records):

    cursor.fast_executemany = True

    for start in range(
        0,
        len(records),
        SQL_INSERT_BATCH_SIZE
    ):
        batch = records[
            start:start + SQL_INSERT_BATCH_SIZE
        ]

        cursor.executemany(sql, batch)


# ============================================================
# 4. VERIFY PROJECT FILES
# ============================================================

def verify_files():

    required_files = [
        SOURCE_PATH,
        MODEL_PATH,
        POLICY_PATH,
        TEST_REPORT_PATH,
    ]

    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(path)

    if OUTPUT_REPORT.exists():
        raise FileExistsError(
            f"Report already exists: {OUTPUT_REPORT}"
        )


# ============================================================
# 5. LOAD MODEL AND RISK POLICY
# ============================================================

def load_model_and_policy():

    import joblib

    bundle = joblib.load(MODEL_PATH)

    with POLICY_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        policy = json.load(file)

    with TEST_REPORT_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        test_report = json.load(file)

    model = bundle["model"]
    scaler = bundle["scaler"]

    categories = bundle["transaction_types"]

    medium_threshold = float(
        policy["thresholds"]["medium"]
    )

    high_threshold = float(
        policy["thresholds"]["high"]
    )

    test_threshold = float(
        test_report["decision_threshold"]
    )

    if not np.isclose(
        high_threshold,
        test_threshold,
        rtol=1e-9,
        atol=1e-8,
    ):
        raise ValueError(
            "Risk policy threshold differs from final test threshold."
        )

    return (
        model,
        scaler,
        categories,
        medium_threshold,
        high_threshold,
    )


# ============================================================
# 6. DATABASE CONSISTENCY CHECK
# ============================================================

def verify_existing_database(cursor):

    cursor.execute("""
        SELECT COUNT_BIG(*)
        FROM dbo.Transactions AS t
        LEFT JOIN dbo.FraudPredictions AS p
            ON t.TransactionID = p.TransactionID
            AND p.ModelName = ?
            AND p.ModelVersion = ?
        WHERE p.PredictionID IS NULL;
    """, MODEL_NAME, MODEL_VERSION)

    missing_predictions = int(
        cursor.fetchone()[0]
    )

    if missing_predictions > 0:
        raise RuntimeError(
            "Existing transactions without matching predictions "
            f"were detected: {missing_predictions:,}. "
            "Review the database before continuing."
        )

    cursor.execute("""
        SELECT COUNT_BIG(*)
        FROM dbo.FraudPredictions AS p
        LEFT JOIN dbo.FraudAlerts AS a
            ON p.PredictionID = a.PredictionID
        WHERE
            (
                p.RiskLevel IN ('HIGH', 'MEDIUM')
                AND a.AlertID IS NULL
            )
            OR
            (
                p.RiskLevel = 'LOW'
                AND a.AlertID IS NOT NULL
            );
    """)

    inconsistent_alerts = int(
        cursor.fetchone()[0]
    )

    if inconsistent_alerts > 0:
        raise RuntimeError(
            "Existing prediction/alert records are inconsistent: "
            f"{inconsistent_alerts:,}."
        )


# ============================================================
# 7. SQL INSERT STATEMENTS
# ============================================================

TRANSACTION_INSERT = """
INSERT INTO dbo.Transactions
(
    SourceRowNumber,
    Step,
    TransactionType,
    Amount,
    NameOrig,
    OldBalanceOrg,
    NewBalanceOrig,
    NameDest,
    OldBalanceDest,
    NewBalanceDest,
    IsFraud,
    IsFlaggedFraud
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

PREDICTION_INSERT = """
INSERT INTO dbo.FraudPredictions
(
    TransactionID,
    ModelName,
    ModelVersion,
    RawDecisionScore,
    DecisionThreshold,
    PredictedFraud,
    RiskLevel,
    RecommendedAction,
    DatasetSplit
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

ALERT_INSERT = """
INSERT INTO dbo.FraudAlerts
(
    PredictionID,
    TransactionID,
    AlertType,
    AlertStatus,
    AlertMessage,
    SimulatedHold
)
VALUES (?, ?, ?, ?, ?, ?);
"""


# ============================================================
# 8. PROCESS ONE SOURCE CHUNK
# ============================================================

def process_chunk(
    connection,
    chunk,
    first_source_row,
    last_source_row,
    model,
    scaler,
    categories,
    medium_threshold,
    high_threshold,
):

    cursor = connection.cursor()

    try:

        # Select only validation and test rows.
        steps = chunk["step"].to_numpy()

        validation_mask = (
            (steps >= START_VALIDATION)
            & (steps <= END_VALIDATION)
        )

        test_mask = (
            (steps >= START_TEST)
            & (steps <= END_TEST)
        )

        selected_mask = validation_mask | test_mask

        if not selected_mask.any():
            return 0, 0, 0

        selected = chunk.loc[
            selected_mask
        ].copy()

        selected["SourceRowNumber"] = (
            chunk.loc[selected_mask, "SourceRowNumber"]
            .astype("int64")
        )

        selected["DatasetSplit"] = np.where(
            selected["step"] <= END_VALIDATION,
            "VALIDATION",
            "TEST",
        )

        # Skip source rows already loaded by a previous run.
        cursor.execute(
            """
            SELECT SourceRowNumber
            FROM dbo.Transactions
            WHERE SourceRowNumber BETWEEN ? AND ?;
            """,
            first_source_row,
            last_source_row,
        )

        existing_rows = {
            int(row[0])
            for row in cursor.fetchall()
        }

        selected = selected.loc[
            ~selected["SourceRowNumber"].isin(existing_rows)
        ].copy()

        if selected.empty:
            return 0, 0, 0

        # Build inference features WITHOUT isFraud.
        X = build_inference_matrix(
            selected,
            categories,
        )

        X_scaled = scaler.transform(X)

        raw_scores = model.decision_function(
            X_scaled
        )

        if not np.isfinite(raw_scores).all():
            raise ValueError("Invalid model scores detected.")

        risk_levels = np.where(
            raw_scores >= high_threshold,
            "HIGH",
            np.where(
                raw_scores >= medium_threshold,
                "MEDIUM",
                "LOW",
            ),
        )

        actions = np.select(
            [
                risk_levels == "HIGH",
                risk_levels == "MEDIUM",
            ],
            [
                "ALERT_AND_SIMULATED_HOLD",
                "MANUAL_REVIEW",
            ],
            default="MONITOR",
        )

        predicted_fraud = (
            risk_levels == "HIGH"
        ).astype(np.int8)

        # ----------------------------------------------------
        # INSERT TRANSACTIONS
        # ----------------------------------------------------

        transaction_columns = [
            "SourceRowNumber",
            "step",
            "type",
            "amount",
            "nameOrig",
            "oldbalanceOrg",
            "newbalanceOrig",
            "nameDest",
            "oldbalanceDest",
            "newbalanceDest",
            "isFraud",
            "isFlaggedFraud",
        ]

        transaction_records = []

        for row in selected[
            transaction_columns
        ].itertuples(index=False, name=None):

            transaction_records.append((
                int(row[0]),
                int(row[1]),
                str(row[2]),
                float(row[3]),
                str(row[4]),
                float(row[5]),
                float(row[6]),
                str(row[7]),
                float(row[8]),
                float(row[9]),
                int(row[10]),
                int(row[11]),
            ))

        insert_in_batches(
            cursor,
            TRANSACTION_INSERT,
            transaction_records,
        )

        # ----------------------------------------------------
        # GET DATABASE TRANSACTION IDENTIFIERS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT SourceRowNumber, TransactionID
            FROM dbo.Transactions
            WHERE SourceRowNumber BETWEEN ? AND ?;
            """,
            first_source_row,
            last_source_row,
        )

        transaction_id_map = {
            int(row.SourceRowNumber): int(row.TransactionID)
            for row in cursor.fetchall()
        }

        selected_source_rows = (
            selected["SourceRowNumber"].astype("int64").tolist()
        )

        if any(
            source_row not in transaction_id_map
            for source_row in selected_source_rows
        ):
            raise RuntimeError(
                "Could not map every source row to a SQL TransactionID."
            )

        transaction_ids = [
            transaction_id_map[source_row]
            for source_row in selected_source_rows
        ]

        # ----------------------------------------------------
        # INSERT PREDICTIONS
        # ----------------------------------------------------

        prediction_records = []

        splits = selected["DatasetSplit"].tolist()

        for index in range(len(selected)):

            prediction_records.append((
                transaction_ids[index],
                MODEL_NAME,
                MODEL_VERSION,
                float(raw_scores[index]),
                float(high_threshold),
                int(predicted_fraud[index]),
                str(risk_levels[index]),
                str(actions[index]),
                str(splits[index]),
            ))

        insert_in_batches(
            cursor,
            PREDICTION_INSERT,
            prediction_records,
        )

        # ----------------------------------------------------
        # RETRIEVE PREDICTION IDENTIFIERS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                t.SourceRowNumber,
                p.PredictionID,
                p.TransactionID,
                p.RiskLevel,
                p.RawDecisionScore
            FROM dbo.Transactions AS t
            INNER JOIN dbo.FraudPredictions AS p
                ON t.TransactionID = p.TransactionID
            WHERE
                t.SourceRowNumber BETWEEN ? AND ?
                AND p.ModelName = ?
                AND p.ModelVersion = ?;
            """,
            first_source_row,
            last_source_row,
            MODEL_NAME,
            MODEL_VERSION,
        )

        prediction_map = {
            int(row.SourceRowNumber): {
                "prediction_id": int(row.PredictionID),
                "transaction_id": int(row.TransactionID),
                "risk_level": row.RiskLevel,
                "score": float(row.RawDecisionScore),
            }
            for row in cursor.fetchall()
        }

        # ----------------------------------------------------
        # INSERT HIGH ALERTS AND MEDIUM REVIEWS
        # ----------------------------------------------------

        alert_records = []

        for index, source_row in enumerate(
            selected_source_rows
        ):

            risk = str(risk_levels[index])

            if risk == "LOW":
                continue

            prediction = prediction_map[source_row]

            if risk == "HIGH":
                alert_type = "HIGH_RISK"
                simulated_hold = 1
            else:
                alert_type = "MANUAL_REVIEW"
                simulated_hold = 0

            message = (
                f"{risk} risk detected. "
                f"Raw score: {raw_scores[index]:.8f}. "
                f"Action: {actions[index]}. "
                "Post-transaction monitoring only."
            )

            alert_records.append((
                prediction["prediction_id"],
                prediction["transaction_id"],
                alert_type,
                "OPEN",
                message,
                simulated_hold,
            ))

        if alert_records:
            insert_in_batches(
                cursor,
                ALERT_INSERT,
                alert_records,
            )

        # Commit transaction, predictions and alerts together.
        connection.commit()

        fraud_count = int(
            selected["isFraud"].sum()
        )

        return (
            len(selected),
            fraud_count,
            len(alert_records),
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()


# ============================================================
# 9. MAIN DATA LOADING PROCESS
# ============================================================

def main():

    verify_files()

    (
        model,
        scaler,
        categories,
        medium_threshold,
        high_threshold,
    ) = load_model_and_policy()

    print("=" * 75)
    print("PAYSIM VALIDATION AND TEST SQL LOADER")
    print("=" * 75)

    print("Database: PaySimFraudDB")
    print("Source:", SOURCE_PATH)
    print("Model:", MODEL_NAME)
    print("Model version:", MODEL_VERSION)
    print("Chunk size:", f"{CHUNK_SIZE:,}")

    print("\nMedium threshold:", medium_threshold)
    print("High threshold:", high_threshold)

    print("\nTraining period will NOT be loaded.")
    print("isFraud will NOT be used as a model feature.")

    connection = None

    rows_scanned = 0

    total_loaded = 0
    total_fraud = 0
    total_alerts = 0

    try:

        connection = get_connection()

        connection.autocommit = False

        check_cursor = connection.cursor()

        verify_existing_database(check_cursor)

        check_cursor.close()

        reader = pd.read_csv(
            SOURCE_PATH,
            usecols=CSV_COLUMNS,
            dtype=CSV_DTYPES,
            chunksize=CHUNK_SIZE,
            encoding="utf-8-sig",
        )

        for chunk_number, chunk in enumerate(
            reader,
            start=1,
        ):

            first_source_row = rows_scanned + 1

            rows_scanned += len(chunk)

            last_source_row = rows_scanned

            chunk["SourceRowNumber"] = np.arange(
                first_source_row,
                last_source_row + 1,
                dtype=np.int64,
            )

            loaded, fraud, alerts = process_chunk(
                connection,
                chunk,
                first_source_row,
                last_source_row,
                model,
                scaler,
                categories,
                medium_threshold,
                high_threshold,
            )

            total_loaded += loaded
            total_fraud += fraud
            total_alerts += alerts

            if chunk_number % 5 == 0 or loaded > 0:

                print(
                    f"CSV chunk {chunk_number}: "
                    f"source rows scanned={rows_scanned:,} | "
                    f"new transactions loaded={total_loaded:,} | "
                    f"new alerts/reviews={total_alerts:,}"
                )

        # ----------------------------------------------------
        # FINAL DATABASE SUMMARY
        # ----------------------------------------------------

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                p.DatasetSplit,
                COUNT_BIG(*) AS TotalPredictions,

                SUM(
                    CONVERT(BIGINT, t.IsFraud)
                ) AS ActualFraud,

                SUM(
                    CONVERT(BIGINT, p.PredictedFraud)
                ) AS PredictedFraud,

                SUM(
                    CASE WHEN p.RiskLevel = 'HIGH'
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                    END
                ) AS HighRisk,

                SUM(
                    CASE WHEN p.RiskLevel = 'MEDIUM'
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                    END
                ) AS MediumRisk

            FROM dbo.FraudPredictions AS p

            INNER JOIN dbo.Transactions AS t
                ON p.TransactionID = t.TransactionID

            WHERE
                p.ModelName = ?
                AND p.ModelVersion = ?

            GROUP BY p.DatasetSplit
            ORDER BY p.DatasetSplit;
        """, MODEL_NAME, MODEL_VERSION)

        database_summary = {}

        for row in cursor.fetchall():

            database_summary[row.DatasetSplit] = {
                "transactions": int(row.TotalPredictions),
                "actual_fraud": int(row.ActualFraud),
                "predicted_fraud": int(row.PredictedFraud),
                "high_risk": int(row.HighRisk),
                "medium_risk": int(row.MediumRisk),
            }

        expected_splits = set(EXPECTED_COUNTS)

        if set(database_summary) != expected_splits:
            raise RuntimeError(
                "Database split summary does not match expected splits."
            )

        for split, expected in EXPECTED_COUNTS.items():

            actual = database_summary[split]

            if actual["transactions"] != expected["transactions"]:
                raise RuntimeError(
                    f"{split} transaction count mismatch: "
                    f"{actual['transactions']:,}"
                )

            if actual["actual_fraud"] != expected["fraud"]:
                raise RuntimeError(
                    f"{split} fraud count mismatch: "
                    f"{actual['actual_fraud']:,}"
                )

        cursor.execute("""
            SELECT
                COUNT_BIG(*) AS AlertCount
            FROM dbo.FraudAlerts AS a
            INNER JOIN dbo.FraudPredictions AS p
                ON a.PredictionID = p.PredictionID
            WHERE
                p.ModelName = ?
                AND p.ModelVersion = ?;
        """, MODEL_NAME, MODEL_VERSION)

        alert_count = int(cursor.fetchone().AlertCount)

        cursor.close()

        connection.commit()

        report = {
            "database": "PaySimFraudDB",
            "model": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "source_rows_scanned": int(rows_scanned),
            "new_transactions_loaded_this_run": int(total_loaded),
            "new_fraud_cases_this_run": int(total_fraud),
            "new_alerts_and_reviews_this_run": int(total_alerts),
            "total_database_alerts": alert_count,
            "threshold_source": "validation",
            "training_period_loaded": False,
            "isFraud_used_as_model_feature": False,
            "real_banking_actions_executed": False,
            "database_summary": database_summary,
            "all_expected_counts_verified": True,
        }

        OUTPUT_REPORT.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with OUTPUT_REPORT.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                indent=4,
            )

        print("\n" + "=" * 75)
        print("SQL DATA LOADING COMPLETED")
        print("=" * 75)

        print("New transactions loaded:", f"{total_loaded:,}")
        print("New fraud cases:", f"{total_fraud:,}")
        print("New alerts/reviews:", f"{total_alerts:,}")

        print("\nDATABASE SUMMARY")

        for split, values in database_summary.items():

            print(f"\n{split}")
            print(
                "Transactions:",
                f"{values['transactions']:,}"
            )
            print(
                "Actual fraud:",
                f"{values['actual_fraud']:,}"
            )
            print(
                "Predicted fraud:",
                f"{values['predicted_fraud']:,}"
            )
            print(
                "High risk:",
                f"{values['high_risk']:,}"
            )
            print(
                "Medium risk:",
                f"{values['medium_risk']:,}"
            )

        print("\nTotal alert and review records:", f"{alert_count:,}")

        print("\nReport saved:")
        print(OUTPUT_REPORT.resolve())

        print("\nAll expected database counts verified.")

    except Exception:

        if connection is not None:
            connection.rollback()

        raise

    finally:

        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
