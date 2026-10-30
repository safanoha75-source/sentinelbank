from __future__ import annotations

from datetime import datetime
from math import isfinite

from dash import Input, Output

from src.dashboard.queries import data_access as da
from src.dashboard.components import charts


# ============================================================
# 1. DISPLAY FORMATTING HELPERS
# ============================================================

def format_count(value) -> str:
    """Format database counts with thousands separators."""

    try:
        return f"{int(value or 0):,}"
    except (TypeError, ValueError, OverflowError):
        return "0"


def format_percentage(value) -> str:
    """Convert a decimal ratio into a readable percentage."""

    try:
        number = float(value or 0)

        if not isfinite(number):
            return "—"

        return f"{number * 100:,.2f}%"

    except (TypeError, ValueError, OverflowError):
        return "—"


def get_current_timestamp() -> str:
    """Return the local timestamp for dashboard monitoring."""

    return datetime.now().astimezone().strftime(
        "%Y-%m-%d %I:%M:%S %p %Z"
    )


# ============================================================
# 2. ANALYTICS CALLBACK REGISTRATION
# ============================================================

def register_analytics_callbacks(app):
    """
    Register the main executive analytics callback.

    Inputs:
        - Dataset split
        - Transaction type
        - Risk level
        - Manual refresh button
        - Automatic refresh interval

    Outputs:
        - Six executive KPIs
        - Three interactive Plotly charts
        - Database connection status
        - Dashboard error message
        - Last refresh timestamp
    """

    @app.callback(
        [
            Output("kpi-total", "children"),
            Output("kpi-fraud", "children"),
            Output("kpi-fraud-rate", "children"),
            Output("kpi-high", "children"),
            Output("kpi-medium", "children"),
            Output("kpi-f1", "children"),

            Output("type-chart", "figure"),
            Output("risk-chart", "figure"),
            Output("temporal-chart", "figure"),

            Output("db-status", "children"),
            Output("dashboard-error", "children"),
            Output("last-updated", "children"),
        ],

        [
            Input("split-filter", "value"),
            Input("type-filter", "value"),
            Input("risk-filter", "value"),
            Input("refresh-button", "n_clicks"),
            Input("refresh-interval", "n_intervals"),
        ],
    )
    def update_dashboard_analytics(
        dataset_split,
        transaction_type,
        risk_level,
        manual_refresh,
        automatic_refresh,
    ):
        """
        Retrieve filtered SQL Server data and refresh
        all executive dashboard analytics.

        KPI metrics intentionally use dataset_split and
        transaction_type because fetch_kpis does not accept
        risk_level.
        """

        dataset_split = str(dataset_split or "ALL").upper()
        transaction_type = str(transaction_type or "ALL").upper()
        risk_level = str(risk_level or "ALL").upper()

        timestamp = get_current_timestamp()

        try:

            # ------------------------------------------------
            # A. EXECUTIVE KPI DATA
            # ------------------------------------------------

            metrics = da.fetch_kpis(
                dataset_split=dataset_split,
                transaction_type=transaction_type,
            )

            if not isinstance(metrics, dict):
                raise TypeError(
                    "fetch_kpis() must return a dictionary."
                )

            # ------------------------------------------------
            # B. TRANSACTION TYPE ANALYSIS
            # ------------------------------------------------

            type_data = da.fetch_type_analysis(
                dataset_split=dataset_split,
                risk_level=risk_level,
            )

            # ------------------------------------------------
            # C. RISK DISTRIBUTION
            # ------------------------------------------------

            risk_data = da.fetch_risk_distribution(
                dataset_split=dataset_split,
                transaction_type=transaction_type,
            )

            # ------------------------------------------------
            # D. TEMPORAL ANALYSIS
            # ------------------------------------------------

            temporal_data = da.fetch_temporal_trend(
                dataset_split=dataset_split,
                transaction_type=transaction_type,
            )

            # ------------------------------------------------
            # E. BUILD INTERACTIVE CHARTS
            # ------------------------------------------------

            type_figure = charts.create_type_figure(
                type_data
            )

            risk_figure = charts.create_risk_figure(
                risk_data
            )

            temporal_figure = charts.create_temporal_figure(
                temporal_data
            )

            # ------------------------------------------------
            # F. DATABASE CONNECTION HEALTH
            # ------------------------------------------------

            health = da.check_database_health()

            if health.get("connected", False):

                database_status = (
                    f"CONNECTED  |  "
                    f"{health.get('database') or 'SQL Server'}  |  "
                    f"{format_count(health.get('total_transactions'))} "
                    f"loaded transactions"
                )

                error_message = ""

            else:

                database_status = (
                    "DATABASE UNAVAILABLE  |  "
                    "No transaction records were returned."
                )

                error_message = (
                    "Database health check returned no transaction records."
                )

            # ------------------------------------------------
            # G. FORMAT KPI VALUES
            # ------------------------------------------------

            total_transactions = format_count(
                metrics.get("total_transactions")
            )

            actual_fraud = format_count(
                metrics.get("actual_fraud")
            )

            fraud_prevalence = format_percentage(
                metrics.get("fraud_rate")
            )

            high_risk = format_count(
                metrics.get("high_risk")
            )

            manual_review = format_count(
                metrics.get("medium_risk")
            )

            f1_score = format_percentage(
                metrics.get("f1_score")
            )

            last_updated = (
                f"Last successful analytics refresh: {timestamp}"
            )

            # ------------------------------------------------
            # H. RETURN ALL DASHBOARD OUTPUTS
            # ------------------------------------------------

            return (

                total_transactions,
                actual_fraud,
                fraud_prevalence,
                high_risk,
                manual_review,
                f1_score,

                type_figure,
                risk_figure,
                temporal_figure,

                database_status,
                error_message,
                last_updated,
            )

        except Exception as exc:

            # ------------------------------------------------
            # SAFE ERROR HANDLING
            # ------------------------------------------------

            error_message = (
                f"Dashboard refresh failed: "
                f"{type(exc).__name__}: {exc}"
            )

            database_status = (
                f"ANALYTICS ERROR  |  {type(exc).__name__}"
            )

            last_updated = (
                f"Last attempted refresh: {timestamp}"
            )

            # Return stable placeholders instead of
            # terminating the dashboard callback.

            return (

                "—",
                "—",
                "—",
                "—",
                "—",
                "—",

                charts.empty_figure(
                    "Analytics data could not be loaded.",
                    "Fraud by Transaction Type",
                ),

                charts.empty_figure(
                    "Analytics data could not be loaded.",
                    "Transaction Risk Distribution",
                ),

                charts.empty_figure(
                    "Analytics data could not be loaded.",
                    "Fraud Activity Over Time",
                ),

                database_status,
                error_message,
                last_updated,
            )
