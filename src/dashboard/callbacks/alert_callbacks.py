from __future__ import annotations

import logging

from dash import Input, Output

from src.dashboard.queries import data_access as da
from src.dashboard.callbacks.transaction_callbacks import (
    build_table_records,
)


logger = logging.getLogger(__name__)


# ============================================================
# 1. ALERT TABLE CONFIGURATION
# ============================================================

ALERT_COLUMNS = [
    {"name": "Alert ID", "id": "AlertID"},
    {"name": "Alert Category", "id": "AlertType"},
    {"name": "Alert Status", "id": "AlertStatus"},
    {"name": "Alert Message", "id": "AlertMessage"},
    {"name": "Simulated Hold", "id": "SimulatedHold"},
    {"name": "Created At (UTC)", "id": "CreatedAtUtc"},
    {"name": "Resolved At (UTC)", "id": "ResolvedAtUtc"},
    {"name": "Source Row", "id": "SourceRowNumber"},
    {"name": "Step", "id": "Step"},
    {"name": "Transaction Type", "id": "TransactionType"},
    {"name": "Amount", "id": "Amount"},
    {"name": "Dataset Split", "id": "DatasetSplit"},
    {"name": "Raw Decision Score", "id": "RawDecisionScore"},
    {"name": "Risk Level", "id": "RiskLevel"},
    {"name": "Recommended Action", "id": "RecommendedAction"},
]


# ============================================================
# 2. ALERT CALLBACK REGISTRATION
# ============================================================

def register_alert_callbacks(app):
    """
    Register the Alert Center table callback.

    Filters:
        Dataset split
        Transaction type
        Alert status
        Alert category

    Refresh:
        Manual refresh button
        Automatic 30-second interval

    Output:
        Alert DataTable records, columns and selection state.
    """

    @app.callback(
        [
            Output("alert-table", "data"),
            Output("alert-table", "columns"),
            Output("alert-table", "selected_rows"),
        ],

        [
            Input("split-filter", "value"),
            Input("type-filter", "value"),
            Input("alert-status-filter", "value"),
            Input("alert-type-filter", "value"),
            Input("refresh-button", "n_clicks"),
            Input("refresh-interval", "n_intervals"),
        ],
    )
    def update_alert_table(
        dataset_split,
        transaction_type,
        alert_status,
        alert_type,
        manual_refresh,
        automatic_refresh,
    ):
        """
        Fetch filtered alert records from SQL Server.

        The query layer validates all filter values and
        uses parameterized SQL statements.
        """

        dataset_split = str(
            dataset_split or "ALL"
        ).upper()

        transaction_type = str(
            transaction_type or "ALL"
        ).upper()

        alert_status = str(
            alert_status or "ALL"
        ).upper()

        alert_type = str(
            alert_type or "ALL"
        ).upper()

        try:

            # ------------------------------------------------
            # A. RETRIEVE ALERTS FROM SQL SERVER
            # ------------------------------------------------

            dataframe = da.fetch_alerts(
                dataset_split=dataset_split,
                transaction_type=transaction_type,
                alert_status=alert_status,
                alert_type=alert_type,
                limit=100,
            )

            # ------------------------------------------------
            # B. VALIDATE QUERY RESULT
            # ------------------------------------------------

            if dataframe is None:
                raise TypeError(
                    "fetch_alerts() returned None."
                )

            # ------------------------------------------------
            # C. SERIALIZE DATABASE VALUES
            # ------------------------------------------------

            records = build_table_records(dataframe)

            # ------------------------------------------------
            # D. RETURN ALERT TABLE OUTPUTS
            # ------------------------------------------------

            return (
                records,
                ALERT_COLUMNS,
                [],
            )

        except Exception:

            logger.exception(
                "Alert Center query failed."
            )

            # Do not crash the complete dashboard.
            return (
                [],
                ALERT_COLUMNS,
                [],
            )
