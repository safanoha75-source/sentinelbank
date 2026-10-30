from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from math import isfinite

import pandas as pd

from dash import Input, Output, State, html

from src.dashboard.queries import data_access as da


logger = logging.getLogger(__name__)


# ============================================================
# 1. TRANSACTION TABLE CONFIGURATION
# ============================================================

TRANSACTION_COLUMNS = [
    {"name": "Source Row", "id": "SourceRowNumber"},
    {"name": "Step", "id": "Step"},
    {"name": "Transaction Type", "id": "TransactionType"},
    {"name": "Amount", "id": "Amount"},
    {"name": "Sender ID", "id": "NameOrig"},
    {"name": "Receiver ID", "id": "NameDest"},
    {"name": "Dataset", "id": "DatasetSplit"},
    {"name": "Raw Decision Score", "id": "RawDecisionScore"},
    {"name": "Predicted Fraud", "id": "PredictedFraud"},
    {"name": "Risk Level", "id": "RiskLevel"},
    {"name": "Recommended Action", "id": "RecommendedAction"},
    {"name": "Alert Type", "id": "AlertType"},
    {"name": "Alert Status", "id": "AlertStatus"},
    {"name": "Simulated Hold", "id": "SimulatedHold"},
]


# ============================================================
# 2. SAFE VALUE CONVERSION
# ============================================================

def serialize_value(value):
    """
    Convert SQL Server and Pandas values into JSON-safe values
    that can be displayed by Dash DataTable.
    """

    if value is None:
        return None

    if isinstance(value, (bool,)):
        return "YES" if value else "NO"

    if isinstance(value, Decimal):
        number = float(value)

        if not isfinite(number):
            return None

        return round(number, 2)

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float):
        return value if isfinite(value) else None

    if isinstance(value, (str, int)):
        return value

    return str(value)


def build_table_records(dataframe: pd.DataFrame) -> list[dict]:
    """
    Convert the query DataFrame into Dash DataTable records.
    """

    if dataframe is None or dataframe.empty:
        return []

    return [
        {
            column: serialize_value(value)
            for column, value in record.items()
        }
        for record in dataframe.to_dict("records")
    ]


# ============================================================
# 3. TRANSACTION DISPLAY HELPERS
# ============================================================

def display_value(value, default="Not available"):
    """Return a readable text representation of a field."""

    if value is None:
        return default

    text = str(value).strip()

    if not text or text.lower() in {"nan", "none", "nat"}:
        return default

    return text


def detail_item(label: str, value, accent: str = "#E5E7EB"):
    """Create a reusable transaction detail field."""

    return html.Div(
        [
            html.Div(
                label.upper(),
                style={
                    "fontSize": "10px",
                    "fontWeight": "700",
                    "color": "#94A3B8",
                    "letterSpacing": "1px",
                    "marginBottom": "7px",
                },
            ),

            html.Div(
                display_value(value),
                style={
                    "fontSize": "13px",
                    "fontWeight": "600",
                    "color": accent,
                    "overflowWrap": "anywhere",
                },
            ),
        ],
        style={
            "backgroundColor": "#111D31",
            "border": "1px solid #263650",
            "borderRadius": "9px",
            "padding": "13px",
            "minWidth": "0",
        },
    )


# ============================================================
# 4. TRANSACTION DETAILS PANEL
# ============================================================

def build_transaction_details(transaction: dict):
    """
    Build the investigation panel for the selected transaction.

    Important:
    RawDecisionScore is a model decision margin,
    not a calibrated probability.
    """

    risk_level = display_value(
        transaction.get("RiskLevel"),
        "UNKNOWN",
    ).upper()

    risk_colors = {
        "LOW": "#34D399",
        "MEDIUM": "#FBBF24",
        "HIGH": "#F87171",
    }

    risk_color = risk_colors.get(
        risk_level,
        "#94A3B8",
    )

    amount = transaction.get("Amount")

    try:
        amount_display = f"{float(amount):,.2f}"
    except (TypeError, ValueError, OverflowError):
        amount_display = display_value(amount)

    score = transaction.get("RawDecisionScore")

    try:
        score_display = f"{float(score):,.4f}"
    except (TypeError, ValueError, OverflowError):
        score_display = display_value(score)

    return html.Div(
        [

            # ------------------------------------------------
            # HEADER
            # ------------------------------------------------

            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                "TRANSACTION INVESTIGATION",
                                style={
                                    "color": "#E5E7EB",
                                    "fontSize": "15px",
                                    "fontWeight": "800",
                                    "letterSpacing": "1px",
                                    "marginBottom": "6px",
                                },
                            ),

                            html.P(
                                (
                                    "Source row: "
                                    f"{display_value(transaction.get('SourceRowNumber'))}"
                                ),
                                style={
                                    "color": "#94A3B8",
                                    "fontSize": "11px",
                                    "margin": "0",
                                },
                            ),
                        ]
                    ),

                    html.Div(
                        risk_level,
                        style={
                            "backgroundColor": "#111D31",
                            "color": risk_color,
                            "border": f"1px solid {risk_color}",
                            "borderRadius": "20px",
                            "padding": "7px 16px",
                            "fontSize": "12px",
                            "fontWeight": "800",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": "15px",
                    "flexWrap": "wrap",
                    "marginBottom": "18px",
                },
            ),

            # ------------------------------------------------
            # TRANSACTION INFORMATION
            # ------------------------------------------------

            html.Div(
                [
                    detail_item(
                        "Transaction Type",
                        transaction.get("TransactionType"),
                    ),

                    detail_item(
                        "Transaction Amount",
                        amount_display,
                        "#22D3EE",
                    ),

                    detail_item(
                        "PaySim Time Step",
                        transaction.get("Step"),
                    ),

                    detail_item(
                        "Dataset Split",
                        transaction.get("DatasetSplit"),
                    ),

                    detail_item(
                        "Sender ID",
                        transaction.get("NameOrig"),
                    ),

                    detail_item(
                        "Receiver ID",
                        transaction.get("NameDest"),
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": (
                        "repeat(auto-fit, minmax(170px, 1fr))"
                    ),
                    "gap": "10px",
                    "marginBottom": "18px",
                },
            ),

            # ------------------------------------------------
            # MODEL DECISION
            # ------------------------------------------------

            html.H5(
                "MODEL DECISION",
                style={
                    "color": "#22D3EE",
                    "fontSize": "12px",
                    "fontWeight": "800",
                    "letterSpacing": "1px",
                    "marginBottom": "12px",
                },
            ),

            html.Div(
                [
                    detail_item(
                        "Predicted Fraud",
                        transaction.get("PredictedFraud"),
                    ),

                    detail_item(
                        "Raw Decision Score",
                        score_display,
                        "#A78BFA",
                    ),

                    detail_item(
                        "Recommended Action",
                        transaction.get("RecommendedAction"),
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": (
                        "repeat(auto-fit, minmax(170px, 1fr))"
                    ),
                    "gap": "10px",
                    "marginBottom": "18px",
                },
            ),

            html.P(
                (
                    "Interpretation: Raw Decision Score is the "
                    "classifier's raw decision margin, not a fraud "
                    "probability. Risk Level is assigned by the "
                    "project's experimental risk policy."
                ),
                style={
                    "color": "#94A3B8",
                    "fontSize": "11px",
                    "lineHeight": "1.7",
                    "marginBottom": "18px",
                },
            ),

            # ------------------------------------------------
            # ALERT AND SIMULATED ACTION
            # ------------------------------------------------

            html.H5(
                "ALERT AND SIMULATED ACTION",
                style={
                    "color": "#FBBF24",
                    "fontSize": "12px",
                    "fontWeight": "800",
                    "letterSpacing": "1px",
                    "marginBottom": "12px",
                },
            ),

            html.Div(
                [
                    detail_item(
                        "Alert Type",
                        transaction.get("AlertType"),
                    ),

                    detail_item(
                        "Alert Status",
                        transaction.get("AlertStatus"),
                    ),

                    detail_item(
                        "Simulated Hold",
                        transaction.get("SimulatedHold"),
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": (
                        "repeat(auto-fit, minmax(170px, 1fr))"
                    ),
                    "gap": "10px",
                },
            ),

            html.P(
                (
                    "This is a historical PaySim investigation view. "
                    "Any hold shown here is a simulated project decision, "
                    "not a real banking transaction action."
                ),
                style={
                    "color": "#94A3B8",
                    "fontSize": "10px",
                    "lineHeight": "1.7",
                    "marginTop": "17px",
                    "marginBottom": "0",
                },
            ),

        ],
        style={
            "backgroundColor": "#141F33",
            "border": "1px solid #263650",
            "borderRadius": "12px",
            "padding": "20px",
            "marginTop": "5px",
        },
    )


# ============================================================
# 5. CALLBACK REGISTRATION
# ============================================================

def register_transaction_callbacks(app):
    """
    Register the Transaction Explorer and Details callbacks.
    """

    # --------------------------------------------------------
    # CALLBACK A: SEARCH AND FILTER TRANSACTIONS
    # --------------------------------------------------------

    @app.callback(
        [
            Output("transaction-table", "data"),
            Output("transaction-table", "columns"),
            Output("transaction-table", "selected_rows"),
        ],

        [
            Input("split-filter", "value"),
            Input("type-filter", "value"),
            Input("risk-filter", "value"),
            Input("transaction-search", "value"),
            Input("refresh-button", "n_clicks"),
            Input("refresh-interval", "n_intervals"),
        ],
    )
    def update_transaction_table(
        dataset_split,
        transaction_type,
        risk_level,
        search_text,
        manual_refresh,
        automatic_refresh,
    ):
        """
        Load a safely limited transaction result set.

        Each filter is passed to the parameterized SQL
        query in the data access layer.
        """

        dataset_split = str(dataset_split or "ALL").upper()
        transaction_type = str(transaction_type or "ALL").upper()
        risk_level = str(risk_level or "ALL").upper()
        search_text = str(search_text or "").strip()

        try:

            dataframe = da.fetch_transactions(
                dataset_split=dataset_split,
                transaction_type=transaction_type,
                risk_level=risk_level,
                search_text=search_text,
                limit=100,
            )

            if not isinstance(dataframe, pd.DataFrame):
                raise TypeError(
                    "fetch_transactions() must return a DataFrame."
                )

            records = build_table_records(dataframe)

            return (
                records,
                TRANSACTION_COLUMNS,
                [],
            )

        except Exception:
            logger.exception(
                "Transaction Explorer query failed."
            )

            return (
                [],
                TRANSACTION_COLUMNS,
                [],
            )

    # --------------------------------------------------------
    # CALLBACK B: INSPECT SELECTED TRANSACTION
    # --------------------------------------------------------

    @app.callback(
        Output("transaction-details", "children"),

        [
            Input("transaction-table", "selected_rows"),
        ],

        [
            State("transaction-table", "data"),
        ],
    )
    def show_transaction_details(selected_rows, table_data):
        """
        Display details for the currently selected row.
        """

        if not selected_rows or not table_data:
            return html.Div(
                "Select a transaction from the table to inspect "
                "its risk decision, model score and simulated alert.",
                style={
                    "color": "#94A3B8",
                    "fontSize": "12px",
                    "padding": "12px",
                },
            )

        selected_index = selected_rows[0]

        if not isinstance(selected_index, int):
            return html.Div(
                "Invalid transaction selection.",
                style={"color": "#F87171"},
            )

        if selected_index < 0 or selected_index >= len(table_data):
            return html.Div(
                "The selected transaction is no longer available. "
                "Refresh the table and select another row.",
                style={"color": "#FBBF24"},
            )

        transaction = table_data[selected_index]

        return build_transaction_details(transaction)
