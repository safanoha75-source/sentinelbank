from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ============================================================
# 1. PROFESSIONAL FINTECH COLOR SYSTEM
# ============================================================

COLORS = {
    "background": "rgba(0, 0, 0, 0)",
    "surface": "#111827",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
    "grid": "rgba(148, 163, 184, 0.14)",
    "cyan": "#22D3EE",
    "blue": "#60A5FA",
    "purple": "#A78BFA",
    "green": "#34D399",
    "amber": "#FBBF24",
    "red": "#F87171",
    "low": "#34D399",
    "medium": "#FBBF24",
    "high": "#F87171",
}


# ============================================================
# 2. DATA VALIDATION
# ============================================================

def _validate_columns(
    df: pd.DataFrame | None,
    required_columns: Iterable[str],
    chart_name: str,
) -> bool:
    """
    Validate the input DataFrame before building a chart.

    Returns False when the DataFrame is empty.
    Raises a clear error when required columns are missing.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return False

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{chart_name}: missing required columns: "
            f"{missing_columns}. "
            f"Received columns: {list(df.columns)}"
        )

    return True


def _numeric(
    df: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """
    Convert chart-related columns to numeric values safely.
    Invalid numeric values become zero for visualization.
    """

    result = df.copy()

    for column in columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        ).fillna(0)

    return result


# ============================================================
# 3. COMMON CHART DESIGN
# ============================================================

def _apply_chart_theme(
    fig: go.Figure,
    title: str,
    height: int = 370,
) -> go.Figure:
    """
    Apply the shared Midnight FinTech visual identity.
    """

    fig.update_layout(
        title={
            "text": title,
            "x": 0.02,
            "xanchor": "left",
            "font": {
                "size": 17,
                "color": COLORS["text"],
            },
        },
        template="plotly_dark",
        height=height,
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font={
            "family": "Segoe UI, Arial, sans-serif",
            "size": 12,
            "color": COLORS["muted"],
        },
        margin={
            "l": 55,
            "r": 55,
            "t": 65,
            "b": 55,
        },
        hoverlabel={
            "bgcolor": "#1E293B",
            "bordercolor": COLORS["cyan"],
            "font": {
                "color": "#F8FAFC",
                "family": "Segoe UI, Arial, sans-serif",
            },
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {
                "size": 10,
                "color": COLORS["text"],
            },
        },
        transition={
            "duration": 350,
            "easing": "cubic-in-out",
        },
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=COLORS["grid"],
        tickfont={"color": COLORS["muted"]},
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grid"],
        zeroline=False,
        linecolor=COLORS["grid"],
        tickfont={"color": COLORS["muted"]},
    )

    return fig


# ============================================================
# 4. EMPTY CHART STATE
# ============================================================

def empty_figure(
    message: str = "No data available for the selected filters.",
    title: str = "No Data",
) -> go.Figure:
    """
    Display a professional empty state instead of a broken chart.
    """

    fig = go.Figure()

    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={
            "size": 14,
            "color": COLORS["muted"],
        },
    )

    fig = _apply_chart_theme(fig, title)

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    return fig


# ============================================================
# 5. FRAUD BY TRANSACTION TYPE
# ============================================================

def create_type_figure(df: pd.DataFrame | None) -> go.Figure:
    """
    Compare actual fraud and model-predicted fraud by transaction type.

    Total transaction volume is displayed on a secondary Y-axis,
    because transaction volume and fraud counts have different scales.
    """

    required = [
        "TransactionType",
        "TotalTransactions",
        "ActualFraud",
        "PredictedFraud",
    ]

    if not _validate_columns(
        df,
        required,
        "Transaction Type Chart",
    ):
        return empty_figure(
            "No transaction-type data available.",
            "Fraud by Transaction Type",
        )

    data = _numeric(
        df,
        [
            "TotalTransactions",
            "ActualFraud",
            "PredictedFraud",
        ],
    )

    data["TransactionType"] = (
        data["TransactionType"]
        .fillna("UNKNOWN")
        .astype(str)
    )

    data = data.sort_values(
        "ActualFraud",
        ascending=True,
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=data["TransactionType"],
            y=data["ActualFraud"],
            name="Actual Fraud",
            marker={
                "color": COLORS["red"],
                "line": {"width": 0},
            },
            customdata=data[["TotalTransactions"]],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Actual Fraud: %{y:,.0f}<br>"
                "Total Transactions: %{customdata[0]:,.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Bar(
            x=data["TransactionType"],
            y=data["PredictedFraud"],
            name="Predicted Fraud",
            marker={
                "color": COLORS["cyan"],
                "line": {"width": 0},
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Predicted Fraud: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=data["TransactionType"],
            y=data["TotalTransactions"],
            name="Transaction Volume",
            mode="lines+markers",
            line={
                "color": COLORS["purple"],
                "width": 2.5,
            },
            marker={
                "size": 8,
                "symbol": "circle",
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Total Transactions: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        barmode="group",
        bargap=0.28,
        hovermode="x unified",
    )

    fig.update_yaxes(
        title_text="Fraud Cases",
        secondary_y=False,
    )

    fig.update_yaxes(
        title_text="Total Transactions",
        secondary_y=True,
        showgrid=False,
    )

    return _apply_chart_theme(
        fig,
        "Fraud by Transaction Type",
    )


# ============================================================
# 6. RISK DISTRIBUTION
# ============================================================

def create_risk_figure(df: pd.DataFrame | None) -> go.Figure:
    """
    Display LOW, MEDIUM and HIGH transaction-risk distribution.

    The donut represents transaction counts, not fraud probability.
    Additional details are available through the hover tooltip.
    """

    required = [
        "RiskLevel",
        "TotalTransactions",
        "ActualFraud",
        "PredictedFraud",
        "AverageAmount",
    ]

    if not _validate_columns(
        df,
        required,
        "Risk Distribution Chart",
    ):
        return empty_figure(
            "No risk-distribution data available.",
            "Risk Distribution",
        )

    data = df.copy()

    data["RiskLevel"] = (
        data["RiskLevel"]
        .fillna("UNKNOWN")
        .astype(str)
        .str.upper()
    )

    data = _numeric(
        data,
        [
            "TotalTransactions",
            "ActualFraud",
            "PredictedFraud",
            "AverageAmount",
        ],
    )

    risk_order = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
    }

    data["_order"] = (
        data["RiskLevel"]
        .map(risk_order)
        .fillna(99)
    )

    data = data.sort_values("_order")

    color_map = {
        "LOW": COLORS["low"],
        "MEDIUM": COLORS["medium"],
        "HIGH": COLORS["high"],
    }

    colors = [
        color_map.get(level, COLORS["blue"])
        for level in data["RiskLevel"]
    ]

    customdata = data[
        [
            "ActualFraud",
            "PredictedFraud",
            "AverageAmount",
        ]
    ].to_numpy()

    total_transactions = int(
        data["TotalTransactions"].sum()
    )

    fig = go.Figure(
        data=[
            go.Pie(
                labels=data["RiskLevel"],
                values=data["TotalTransactions"],
                hole=0.68,
                sort=False,
                direction="clockwise",
                marker={
                    "colors": colors,
                    "line": {
                        "color": "#111827",
                        "width": 3,
                    },
                },
                textinfo="label+percent",
                textposition="inside",
                insidetextorientation="horizontal",
                customdata=customdata,
                hovertemplate=(
                    "<b>Risk: %{label}</b><br>"
                    "Transactions: %{value:,.0f}<br>"
                    "Share: %{percent}<br>"
                    "Actual Fraud: %{customdata[0]:,.0f}<br>"
                    "Predicted Fraud: %{customdata[1]:,.0f}<br>"
                    "Average Amount: %{customdata[2]:,.2f}"
                    "<extra></extra>"
                ),
            )
        ]
    )

    fig.add_annotation(
        text=(
            f"<b>{total_transactions:,}</b>"
            "<br><span style='font-size:11px'>Transactions</span>"
        ),
        x=0.5,
        y=0.5,
        showarrow=False,
        font={
            "size": 21,
            "color": COLORS["text"],
        },
    )

    fig.update_layout(
        showlegend=True,
        legend={
            "orientation": "h",
            "y": -0.08,
            "x": 0.5,
            "xanchor": "center",
        },
        margin={
            "l": 20,
            "r": 20,
            "t": 65,
            "b": 60,
        },
    )

    return _apply_chart_theme(
        fig,
        "Transaction Risk Distribution",
    )


# ============================================================
# 7. FRAUD TREND OVER TIME
# ============================================================

def create_temporal_figure(df: pd.DataFrame | None) -> go.Figure:
    """
    Show actual fraud, predicted fraud and transaction volume by step.

    Fraud counts use the primary Y-axis.
    Transaction volume uses the secondary Y-axis.
    """

    required = [
        "Step",
        "TotalTransactions",
        "ActualFraud",
        "PredictedFraud",
    ]

    if not _validate_columns(
        df,
        required,
        "Temporal Trend Chart",
    ):
        return empty_figure(
            "No temporal data available.",
            "Fraud Trend Over Time",
        )

    data = _numeric(
        df,
        [
            "Step",
            "TotalTransactions",
            "ActualFraud",
            "PredictedFraud",
        ],
    )

    data = data.sort_values("Step")

    data["ActualFraudMovingAverage"] = (
        data["ActualFraud"]
        .rolling(
            window=7,
            min_periods=1,
        )
        .mean()
    )

    fig = make_subplots(
        specs=[[{"secondary_y": True}]]
    )

    fig.add_trace(
        go.Bar(
            x=data["Step"],
            y=data["TotalTransactions"],
            name="Transaction Volume",
            marker={
                "color": "rgba(96, 165, 250, 0.28)",
            },
            hovertemplate=(
                "Step: %{x:,.0f}<br>"
                "Transactions: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=data["Step"],
            y=data["ActualFraud"],
            name="Actual Fraud",
            mode="lines",
            line={
                "color": COLORS["red"],
                "width": 2,
            },
            hovertemplate=(
                "Step: %{x:,.0f}<br>"
                "Actual Fraud: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=data["Step"],
            y=data["PredictedFraud"],
            name="Predicted Fraud",
            mode="lines",
            line={
                "color": COLORS["cyan"],
                "width": 2,
                "dash": "dash",
            },
            hovertemplate=(
                "Step: %{x:,.0f}<br>"
                "Predicted Fraud: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=data["Step"],
            y=data["ActualFraudMovingAverage"],
            name="Actual Fraud · 7-Step Average",
            mode="lines",
            line={
                "color": COLORS["amber"],
                "width": 2.5,
            },
            hovertemplate=(
                "Step: %{x:,.0f}<br>"
                "7-Step Average: %{y:.2f}"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.update_layout(
        hovermode="x unified",
        bargap=0.05,
    )

    fig.update_xaxes(
        title_text="PaySim Time Step",
    )

    fig.update_yaxes(
        title_text="Fraud Cases",
        secondary_y=False,
    )

    fig.update_yaxes(
        title_text="Total Transactions",
        secondary_y=True,
        showgrid=False,
    )

    return _apply_chart_theme(
        fig,
        "Fraud Activity Over Time",
        height=410,
    )
