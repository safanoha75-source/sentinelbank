from pathlib import Path
import sys

import pandas as pd


# ============================================================
# 1. PROJECT PATH AND DATABASE CONNECTION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

FRAUD_ENGINE_DIR = (
    PROJECT_ROOT / "src" / "fraud_engine"
)

sys.path.insert(0, str(FRAUD_ENGINE_DIR))

from db_connection import get_connection


# ============================================================
# 2. ALLOWED FILTER VALUES
# ============================================================

VALID_SPLITS = {
    "ALL",
    "VALIDATION",
    "TEST",
}

VALID_TYPES = {
    "ALL",
    "CASH_IN",
    "CASH_OUT",
    "DEBIT",
    "PAYMENT",
    "TRANSFER",
}

VALID_RISK_LEVELS = {
    "ALL",
    "LOW",
    "MEDIUM",
    "HIGH",
}

VALID_ALERT_STATUSES = {
    "ALL",
    "OPEN",
    "UNDER_REVIEW",
    "RESOLVED",
    "FALSE_POSITIVE",
}

VALID_ALERT_TYPES = {
    "ALL",
    "HIGH_RISK",
    "MANUAL_REVIEW",
}


# ============================================================
# 3. DATABASE QUERY EXECUTOR
# ============================================================

def execute_query(sql, params=None):
    """
    Execute a parameterized SQL query and return a DataFrame.

    The connection is closed after each query.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(sql, params or [])

        if cursor.description is None:
            return pd.DataFrame()

        columns = [
            column[0]
            for column in cursor.description
        ]

        rows = cursor.fetchall()

        return pd.DataFrame.from_records(
            rows,
            columns=columns,
        )

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# 4. FILTER VALIDATION
# ============================================================

def normalize_filters(
    dataset_split="ALL",
    transaction_type="ALL",
    risk_level="ALL",
):

    dataset_split = str(dataset_split).upper()
    transaction_type = str(transaction_type).upper()
    risk_level = str(risk_level).upper()

    if dataset_split not in VALID_SPLITS:
        raise ValueError(
            f"Invalid dataset split: {dataset_split}"
        )

    if transaction_type not in VALID_TYPES:
        raise ValueError(
            f"Invalid transaction type: {transaction_type}"
        )

    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            f"Invalid risk level: {risk_level}"
        )

    return dataset_split, transaction_type, risk_level


# ============================================================
# 5. SQL WHERE CLAUSE BUILDER
# ============================================================

def build_filters(
    dataset_split="ALL",
    transaction_type="ALL",
    risk_level="ALL",
):

    dataset_split, transaction_type, risk_level = (
        normalize_filters(
            dataset_split,
            transaction_type,
            risk_level,
        )
    )

    conditions = ["1 = 1"]
    params = []

    if dataset_split != "ALL":
        conditions.append("p.DatasetSplit = ?")
        params.append(dataset_split)

    if transaction_type != "ALL":
        conditions.append("t.TransactionType = ?")
        params.append(transaction_type)

    if risk_level != "ALL":
        conditions.append("p.RiskLevel = ?")
        params.append(risk_level)

    where_clause = " AND ".join(conditions)

    return where_clause, params


# ============================================================
# 6. EXECUTIVE KPI DATA
# ============================================================

def fetch_kpis(
    dataset_split="ALL",
    transaction_type="ALL",
):
    """
    Calculate classification and monitoring KPIs.

    Risk-level filtering is intentionally omitted here,
    because filtering to one predicted class can distort
    the interpretation of overall model performance.
    """

    where_clause, params = build_filters(
        dataset_split=dataset_split,
        transaction_type=transaction_type,
        risk_level="ALL",
    )

    sql = f"""
        SELECT
            COUNT_BIG(*) AS TotalTransactions,

            SUM(
                CONVERT(BIGINT, t.IsFraud)
            ) AS ActualFraud,

            SUM(
                CASE
                    WHEN p.PredictedFraud = 1
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS PredictedFraud,

            SUM(
                CASE
                    WHEN p.RiskLevel = 'HIGH'
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS HighRisk,

            SUM(
                CASE
                    WHEN p.RiskLevel = 'MEDIUM'
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS MediumRisk,

            SUM(
                CASE
                    WHEN t.IsFraud = 1
                     AND p.PredictedFraud = 1
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS TruePositive,

            SUM(
                CASE
                    WHEN t.IsFraud = 0
                     AND p.PredictedFraud = 1
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS FalsePositive,

            SUM(
                CASE
                    WHEN t.IsFraud = 1
                     AND p.PredictedFraud = 0
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS FalseNegative,

            SUM(
                CASE
                    WHEN t.IsFraud = 0
                     AND p.PredictedFraud = 0
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS TrueNegative

        FROM dbo.Transactions AS t

        INNER JOIN dbo.FraudPredictions AS p
            ON t.TransactionID = p.TransactionID

        WHERE
            {where_clause}
            AND p.ModelName = ?
            AND p.ModelVersion = ?;
    """

    params.extend([
        "SGDClassifier",
        "sgd_logloss_raw_v1",
    ])

    data = execute_query(sql, params)

    if data.empty:
        return {}

    row = data.iloc[0]

    total = int(row["TotalTransactions"] or 0)
    actual_fraud = int(row["ActualFraud"] or 0)
    predicted_fraud = int(row["PredictedFraud"] or 0)

    tp = int(row["TruePositive"] or 0)
    fp = int(row["FalsePositive"] or 0)
    fn = int(row["FalseNegative"] or 0)
    tn = int(row["TrueNegative"] or 0)

    precision = (
        tp / (tp + fp)
        if tp + fp else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    accuracy = (
        (tp + tn) / total
        if total else 0.0
    )

    return {
        "total_transactions": total,
        "actual_fraud": actual_fraud,
        "predicted_fraud": predicted_fraud,
        "high_risk": int(row["HighRisk"] or 0),
        "medium_risk": int(row["MediumRisk"] or 0),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "fraud_rate": (
            actual_fraud / total if total else 0.0
        ),
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "accuracy": accuracy,
    }


# ============================================================
# 7. FRAUD ANALYSIS BY TRANSACTION TYPE
# ============================================================

def fetch_type_analysis(
    dataset_split="ALL",
    risk_level="ALL",
):

    where_clause, params = build_filters(
        dataset_split=dataset_split,
        transaction_type="ALL",
        risk_level=risk_level,
    )

    sql = f"""
        SELECT
            t.TransactionType,

            COUNT_BIG(*) AS TotalTransactions,

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

        FROM dbo.Transactions AS t

        INNER JOIN dbo.FraudPredictions AS p
            ON t.TransactionID = p.TransactionID

        WHERE
            {where_clause}
            AND p.ModelName = ?
            AND p.ModelVersion = ?

        GROUP BY t.TransactionType
        ORDER BY TotalTransactions DESC;
    """

    params.extend([
        "SGDClassifier",
        "sgd_logloss_raw_v1",
    ])

    return execute_query(sql, params)


# ============================================================
# 8. RISK DISTRIBUTION
# ============================================================

def fetch_risk_distribution(
    dataset_split="ALL",
    transaction_type="ALL",
):

    where_clause, params = build_filters(
        dataset_split=dataset_split,
        transaction_type=transaction_type,
        risk_level="ALL",
    )

    sql = f"""
        SELECT
            p.RiskLevel,

            COUNT_BIG(*) AS TotalTransactions,

            SUM(
                CONVERT(BIGINT, t.IsFraud)
            ) AS ActualFraud,

            SUM(
                CONVERT(BIGINT, p.PredictedFraud)
            ) AS PredictedFraud,

            AVG(t.Amount) AS AverageAmount

        FROM dbo.Transactions AS t

        INNER JOIN dbo.FraudPredictions AS p
            ON t.TransactionID = p.TransactionID

        WHERE
            {where_clause}
            AND p.ModelName = ?
            AND p.ModelVersion = ?

        GROUP BY p.RiskLevel

        ORDER BY
            CASE p.RiskLevel
                WHEN 'LOW' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'HIGH' THEN 3
            END;
    """

    params.extend([
        "SGDClassifier",
        "sgd_logloss_raw_v1",
    ])

    return execute_query(sql, params)


# ============================================================
# 9. TEMPORAL TRANSACTION TREND
# ============================================================

def fetch_temporal_trend(
    dataset_split="ALL",
    transaction_type="ALL",
):

    where_clause, params = build_filters(
        dataset_split=dataset_split,
        transaction_type=transaction_type,
        risk_level="ALL",
    )

    sql = f"""
        SELECT
            t.Step,

            COUNT_BIG(*) AS TotalTransactions,

            SUM(
                CONVERT(BIGINT, t.IsFraud)
            ) AS ActualFraud,

            SUM(
                CONVERT(BIGINT, p.PredictedFraud)
            ) AS PredictedFraud,

            SUM(
                CASE
                    WHEN p.RiskLevel = 'HIGH'
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS HighRisk,

            SUM(
                CASE
                    WHEN p.RiskLevel = 'MEDIUM'
                    THEN CONVERT(BIGINT, 1)
                    ELSE CONVERT(BIGINT, 0)
                END
            ) AS MediumRisk

        FROM dbo.Transactions AS t

        INNER JOIN dbo.FraudPredictions AS p
            ON t.TransactionID = p.TransactionID

        WHERE
            {where_clause}
            AND p.ModelName = ?
            AND p.ModelVersion = ?

        GROUP BY t.Step
        ORDER BY t.Step;
    """

    params.extend([
        "SGDClassifier",
        "sgd_logloss_raw_v1",
    ])

    return execute_query(sql, params)


# ============================================================
# 10. TRANSACTION EXPLORER
# ============================================================

def fetch_transactions(
    dataset_split="ALL",
    transaction_type="ALL",
    risk_level="ALL",
    search_text="",
    limit=100,
):
    """
    Retrieve a limited and filterable transaction page.

    Search supports source row number and sender/receiver IDs.
    """

    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("Limit must be an integer from 1 to 500.")

    where_clause, params = build_filters(
        dataset_split,
        transaction_type,
        risk_level,
    )

    search_text = str(search_text or "").strip()

    if len(search_text) > 64:
        raise ValueError("Search text is too long.")

    if search_text:
        where_clause += """
            AND (
                t.NameOrig LIKE ?
                OR t.NameDest LIKE ?
                OR CONVERT(VARCHAR(30), t.SourceRowNumber) LIKE ?
            )
        """

        search_pattern = f"%{search_text}%"

        params.extend([
            search_pattern,
            search_pattern,
            search_pattern,
        ])

    sql = f"""
        SELECT TOP {limit}

            t.SourceRowNumber,
            t.Step,
            t.TransactionType,
            t.Amount,

            t.NameOrig,
            t.NameDest,

            p.DatasetSplit,
            p.RawDecisionScore,
            p.PredictedFraud,
            p.RiskLevel,
            p.RecommendedAction,

            a.AlertType,
            a.AlertStatus,
            a.SimulatedHold

        FROM dbo.Transactions AS t

        INNER JOIN dbo.FraudPredictions AS p
            ON t.TransactionID = p.TransactionID

        LEFT JOIN dbo.FraudAlerts AS a
            ON p.PredictionID = a.PredictionID

        WHERE
            {where_clause}
            AND p.ModelName = ?
            AND p.ModelVersion = ?

        ORDER BY
            t.Step DESC,
            t.SourceRowNumber DESC;
    """

    params.extend([
        "SGDClassifier",
        "sgd_logloss_raw_v1",
    ])

    return execute_query(sql, params)


# ============================================================
# 11. ALERT CENTER
# ============================================================

def fetch_alerts(
    dataset_split="ALL",
    transaction_type="ALL",
    alert_status="ALL",
    alert_type="ALL",
    limit=100,
):

    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("Limit must be an integer from 1 to 500.")

    dataset_split = str(dataset_split).upper()
    transaction_type = str(transaction_type).upper()
    alert_status = str(alert_status).upper()
    alert_type = str(alert_type).upper()

    if dataset_split not in VALID_SPLITS:
        raise ValueError("Invalid dataset split.")

    if transaction_type not in VALID_TYPES:
        raise ValueError("Invalid transaction type.")

    if alert_status not in VALID_ALERT_STATUSES:
        raise ValueError("Invalid alert status.")

    if alert_type not in VALID_ALERT_TYPES:
        raise ValueError("Invalid alert type.")

    conditions = ["1 = 1"]
    params = []

    if dataset_split != "ALL":
        conditions.append("p.DatasetSplit = ?")
        params.append(dataset_split)

    if transaction_type != "ALL":
        conditions.append("t.TransactionType = ?")
        params.append(transaction_type)

    if alert_status != "ALL":
        conditions.append("a.AlertStatus = ?")
        params.append(alert_status)

    if alert_type != "ALL":
        conditions.append("a.AlertType = ?")
        params.append(alert_type)

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT TOP {limit}

            a.AlertID,
            a.AlertType,
            a.AlertStatus,
            a.AlertMessage,
            a.SimulatedHold,
            a.CreatedAtUtc,
            a.ResolvedAtUtc,

            t.SourceRowNumber,
            t.Step,
            t.TransactionType,
            t.Amount,

            p.DatasetSplit,
            p.RawDecisionScore,
            p.RiskLevel,
            p.RecommendedAction

        FROM dbo.FraudAlerts AS a

        INNER JOIN dbo.FraudPredictions AS p
            ON a.PredictionID = p.PredictionID

        INNER JOIN dbo.Transactions AS t
            ON a.TransactionID = t.TransactionID

        WHERE
            {where_clause}
            AND p.ModelName = ?
            AND p.ModelVersion = ?

        ORDER BY
            a.CreatedAtUtc DESC,
            a.AlertID DESC;
    """

    params.extend([
        "SGDClassifier",
        "sgd_logloss_raw_v1",
    ])

    return execute_query(sql, params)


# ============================================================
# 12. CONNECTION HEALTH CHECK
# ============================================================

def check_database_health():

    sql = """
        SELECT
            DB_NAME() AS DatabaseName,
            COUNT_BIG(*) AS TotalTransactions
        FROM dbo.Transactions;
    """

    data = execute_query(sql)

    if data.empty:
        return {
            "connected": False,
            "database": None,
            "total_transactions": 0,
        }

    row = data.iloc[0]

    return {
        "connected": True,
        "database": row["DatabaseName"],
        "total_transactions": int(row["TotalTransactions"]),
    }


# ============================================================
# 13. QUICK MODULE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 65)
    print("PAYSim DASHBOARD DATA ACCESS TEST")
    print("=" * 65)

    print("\nDatabase health:")
    print(check_database_health())

    print("\nValidation KPIs:")
    print(fetch_kpis("VALIDATION"))

    print("\nTest KPIs:")
    print(fetch_kpis("TEST"))

    print("\nTransaction types:")
    print(fetch_type_analysis("TEST").to_string(index=False))

    print("\nRisk distribution:")
    print(fetch_risk_distribution("TEST").to_string(index=False))

    print("\nTemporal trend sample:")
    print(fetch_temporal_trend("TEST").head().to_string(index=False))

    print("\nRecent transactions:")
    print(fetch_transactions("TEST", limit=5).to_string(index=False))

    print("\nRecent alerts:")
    print(fetch_alerts("TEST", limit=5).to_string(index=False))

    print("\nAll data access checks completed.")
