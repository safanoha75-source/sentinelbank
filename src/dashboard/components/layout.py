from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc


# ============================================================
# 1. REUSABLE KPI CARD
# ============================================================

def create_kpi_card(
    title,
    value,
    description,
    icon,
    color,
    component_id,
):

    return html.Div(
        className=f"kpi-card kpi-{color}",
        children=[

            html.Div(
                icon,
                className="kpi-icon",
            ),

            html.Div(
                title,
                className="kpi-label",
            ),

            html.Div(
                value,
                id=component_id,
                className="kpi-value",
            ),

            html.Div(
                description,
                className="kpi-footnote",
            ),

        ],
    )


# ============================================================
# 2. REUSABLE SECTION CARD
# ============================================================

def create_section_card(
    title,
    subtitle,
    component,
    full_width=False,
):

    classes = "section-card"

    if full_width:
        classes += " section-card-full"

    return html.Section(
        className=classes,
        children=[

            html.Div(
                className="section-header",
                children=[

                    html.Div([
                        html.H3(
                            title,
                            className="section-title",
                        ),

                        html.P(
                            subtitle,
                            className="section-subtitle",
                        ),
                    ]),

                ],
            ),

            component,

        ],
    )


# ============================================================
# 3. GLOBAL FILTER COMPONENT
# ============================================================

def create_filter(
    label,
    component_id,
    options,
    default_value="ALL",
):

    return html.Div(
        className="filter-group",
        children=[

            html.Label(
                label,
                htmlFor=component_id,
                className="filter-label",
            ),

            dcc.Dropdown(
                id=component_id,
                options=options,
                value=default_value,
                clearable=False,
                searchable=False,
                className="filter-control",
            ),

        ],
    )


# ============================================================
# 4. TRANSACTION TABLE
# ============================================================

def create_transaction_table():

    return dash_table.DataTable(

        id="transaction-table",

        columns=[],

        data=[],

        page_action="native",
        page_size=12,

        sort_action="native",
        filter_action="none",

        row_selectable="single",
        selected_rows=[],

        style_table={
            "overflowX": "auto",
            "minWidth": "100%",
        },

        style_header={
            "backgroundColor": "#1d2b43",
            "color": "#9bb2d0",
            "fontWeight": "bold",
            "fontSize": "10px",
            "border": "1px solid #263650",
            "textAlign": "left",
        },

        style_cell={
            "backgroundColor": "#141f33",
            "color": "#eaf1fa",
            "border": "1px solid #263650",
            "padding": "12px 10px",
            "fontSize": "11px",
            "fontFamily": "Segoe UI, Arial",
            "textAlign": "left",
            "minWidth": "110px",
            "maxWidth": "220px",
            "whiteSpace": "normal",
            "height": "auto",
        },

        style_data_conditional=[

            {
                "if": {
                    "filter_query": '{RiskLevel} = "HIGH"',
                    "column_id": "RiskLevel",
                },
                "color": "#f16d79",
                "fontWeight": "bold",
            },

            {
                "if": {
                    "filter_query": '{RiskLevel} = "MEDIUM"',
                    "column_id": "RiskLevel",
                },
                "color": "#f5a742",
                "fontWeight": "bold",
            },

            {
                "if": {
                    "filter_query": '{RiskLevel} = "LOW"',
                    "column_id": "RiskLevel",
                },
                "color": "#39c98a",
                "fontWeight": "bold",
            },

        ],

        css=[
            {
                "selector": ".dash-spreadsheet-container",
                "rule": "background-color: #141f33;",
            },
        ],

    )


# ============================================================
# 5. ALERT TABLE
# ============================================================

def create_alert_table():

    return dash_table.DataTable(

        id="alert-table",

        columns=[],

        data=[],

        page_action="native",
        page_size=8,

        sort_action="native",

        row_selectable="single",
        selected_rows=[],

        style_table={
            "overflowX": "auto",
        },

        style_header={
            "backgroundColor": "#1d2b43",
            "color": "#9bb2d0",
            "fontWeight": "bold",
            "fontSize": "10px",
            "border": "1px solid #263650",
        },

        style_cell={
            "backgroundColor": "#141f33",
            "color": "#eaf1fa",
            "border": "1px solid #263650",
            "padding": "11px 9px",
            "fontSize": "10px",
            "fontFamily": "Segoe UI, Arial",
            "textAlign": "left",
            "minWidth": "105px",
            "maxWidth": "200px",
            "whiteSpace": "normal",
        },

    )


# ============================================================
# 6. MAIN DASHBOARD LAYOUT
# ============================================================

def build_layout():

    return html.Div(

        className="app-shell",

        children=[

            # ------------------------------------------------
            # AUTOMATIC REFRESH
            # ------------------------------------------------

            dcc.Interval(
                id="refresh-interval",
                interval=30 * 1000,
                n_intervals=0,
            ),

            # ------------------------------------------------
            # APPLICATION CONTENT
            # ------------------------------------------------

            html.Main(
                className="main-content",

                children=[

                    html.Div(
                        className="dashboard-container",

                        children=[

                            # =================================
                            # HEADER
                            # =================================

                            html.Header(
                                className="topbar",

                                children=[

                                    html.Div(
                                        className="brand-area",

                                        children=[

                                            html.Div(
                                                "F",
                                                className="brand-mark",
                                            ),

                                            html.Div([

                                                html.H1(
                                                    "FRAUD INTELLIGENCE",
                                                    className="brand-title",
                                                ),

                                                html.P(
                                                    "FINANCIAL RISK MONITORING PLATFORM",
                                                    className="brand-subtitle",
                                                ),

                                            ]),

                                        ],
                                    ),

                                    html.Div(
                                        className="topbar-meta",

                                        children=[

                                            html.Div(
                                                className="status-pill",

                                                children=[
                                                    html.Span(
                                                        className="status-dot"
                                                    ),

                                                    html.Span(
                                                        "MONITORING SYSTEM"
                                                    ),
                                                ],
                                            ),

                                            html.Div(
                                                id="db-status",
                                                children="CHECKING DATABASE...",
                                                className="last-updated",
                                            ),

                                        ],
                                    ),

                                ],
                            ),


                            # =================================
                            # PAGE TITLE
                            # =================================

                            html.Div(
                                className="page-heading",

                                children=[

                                    html.Div(
                                        "AI-POWERED FRAUD DETECTION",
                                        className="eyebrow",
                                    ),

                                    html.H2(
                                        "Executive Overview",
                                        className="page-title",
                                    ),

                                    html.P(
                                        "Monitor transaction patterns, "
                                        "fraud predictions, risk exposure "
                                        "and investigation alerts through "
                                        "an integrated analytical platform.",
                                        className="page-description",
                                    ),

                                    html.P(
                                        "Historical PaySim evaluation data "
                                        "| Post-transaction monitoring "
                                        "| Simulated banking actions only.",
                                        className="page-description",
                                    ),

                                ],
                            ),


                            # =================================
                            # GLOBAL FILTERS
                            # =================================

                            html.Div(
                                className="filter-panel",

                                children=[

                                    create_filter(
                                        "DATASET PERIOD",
                                        "split-filter",
                                        [
                                            {"label": "All Periods", "value": "ALL"},
                                            {"label": "Validation", "value": "VALIDATION"},
                                            {"label": "Final Test", "value": "TEST"},
                                        ],
                                    ),

                                    create_filter(
                                        "TRANSACTION TYPE",
                                        "type-filter",
                                        [
                                            {"label": "All Types", "value": "ALL"},
                                            {"label": "Transfer", "value": "TRANSFER"},
                                            {"label": "Cash Out", "value": "CASH_OUT"},
                                            {"label": "Cash In", "value": "CASH_IN"},
                                            {"label": "Payment", "value": "PAYMENT"},
                                            {"label": "Debit", "value": "DEBIT"},
                                        ],
                                    ),

                                    create_filter(
                                        "RISK LEVEL",
                                        "risk-filter",
                                        [
                                            {"label": "All Risk Levels", "value": "ALL"},
                                            {"label": "Low Risk", "value": "LOW"},
                                            {"label": "Medium Risk", "value": "MEDIUM"},
                                            {"label": "High Risk", "value": "HIGH"},
                                        ],
                                    ),

                                    html.Div(
                                        className="refresh-control",

                                        children=[

                                            dbc.Button(
                                                [
                                                    html.Span(
                                                        "↻ ",
                                                        style={
                                                            "fontSize": "16px"
                                                        },
                                                    ),

                                                    "REFRESH DATA",
                                                ],

                                                id="refresh-button",

                                                color="primary",
                                                outline=True,

                                                className="btn-refresh",

                                                n_clicks=0,
                                            ),

                                        ],
                                    ),

                                ],
                            ),


                            # =================================
                            # KPI SECTION
                            # =================================

                            html.Div(
                                "EXECUTIVE PERFORMANCE INDICATORS",
                                className="eyebrow",
                            ),

                            html.Div(
                                className="kpi-grid",

                                children=[

                                    create_kpi_card(
                                        "TOTAL TRANSACTIONS",
                                        "—",
                                        "Transactions in selected period",
                                        "▤",
                                        "blue",
                                        "kpi-total",
                                    ),

                                    create_kpi_card(
                                        "ACTUAL FRAUD",
                                        "—",
                                        "Historical verified fraud labels",
                                        "◈",
                                        "red",
                                        "kpi-fraud",
                                    ),

                                    create_kpi_card(
                                        "FRAUD PREVALENCE",
                                        "—",
                                        "Actual fraud / total transactions",
                                        "%",
                                        "orange",
                                        "kpi-fraud-rate",
                                    ),

                                    create_kpi_card(
                                        "HIGH RISK",
                                        "—",
                                        "Model-generated high-risk cases",
                                        "!",
                                        "red",
                                        "kpi-high",
                                    ),

                                    create_kpi_card(
                                        "MANUAL REVIEW",
                                        "—",
                                        "Transactions awaiting additional review",
                                        "⌕",
                                        "orange",
                                        "kpi-medium",
                                    ),

                                    create_kpi_card(
                                        "F1 SCORE",
                                        "—",
                                        "Precision and recall balance",
                                        "◎",
                                        "purple",
                                        "kpi-f1",
                                    ),

                                ],
                            ),


                            # =================================
                            # ERROR AND REFRESH STATUS
                            # =================================

                            html.Div(
                                id="dashboard-error",
                                children="",
                            ),

                            html.Div(
                                id="last-updated",
                                children="Waiting for initial data refresh...",
                                className="last-updated",
                                style={"marginBottom": "18px"},
                            ),


                            # =================================
                            # ANALYTICS SECTION
                            # =================================

                            html.Div(
                                "TRANSACTION AND RISK ANALYTICS",
                                className="eyebrow",
                            ),

                            html.Div(
                                className="section-grid",

                                children=[

                                    create_section_card(
                                        "Fraud by Transaction Type",

                                        "Actual fraud labels and model predictions "
                                        "across transaction categories.",

                                        dcc.Loading(
                                            dcc.Graph(
                                                id="type-chart",
                                                figure={},
                                                config={
                                                    "displayModeBar": False,
                                                    "responsive": True,
                                                },
                                                style={
                                                    "height": "340px"
                                                },
                                            )
                                        ),
                                    ),

                                    create_section_card(
                                        "Risk Distribution",

                                        "Distribution of LOW, MEDIUM "
                                        "and HIGH predicted risk.",

                                        dcc.Loading(
                                            dcc.Graph(
                                                id="risk-chart",
                                                figure={},
                                                config={
                                                    "displayModeBar": False,
                                                    "responsive": True,
                                                },
                                                style={
                                                    "height": "340px"
                                                },
                                            )
                                        ),
                                    ),

                                    create_section_card(
                                        "Temporal Fraud Monitoring",

                                        "Transaction volume, actual fraud "
                                        "and model-generated alerts by step.",

                                        dcc.Loading(
                                            dcc.Graph(
                                                id="temporal-chart",
                                                figure={},
                                                config={
                                                    "displayModeBar": False,
                                                    "responsive": True,
                                                },
                                                style={
                                                    "height": "370px"
                                                },
                                            )
                                        ),

                                        full_width=True,
                                    ),

                                ],
                            ),


                            # =================================
                            # ALERT CENTER
                            # =================================

                            html.Div(
                                "SECURITY OPERATIONS",
                                className="eyebrow",
                            ),

                            create_section_card(
                                "Fraud Alert Center",

                                "High-risk alerts and manual-review cases "
                                "from the selected dataset period.",

                                html.Div([

                                    html.Div(
                                        className="filter-panel",

                                        children=[

                                            create_filter(
                                                "ALERT STATUS",
                                                "alert-status-filter",
                                                [
                                                    {"label": "All Statuses", "value": "ALL"},
                                                    {"label": "Open", "value": "OPEN"},
                                                    {"label": "Under Review", "value": "UNDER_REVIEW"},
                                                    {"label": "Resolved", "value": "RESOLVED"},
                                                    {"label": "False Positive", "value": "FALSE_POSITIVE"},
                                                ],
                                            ),

                                            create_filter(
                                                "ALERT CATEGORY",
                                                "alert-type-filter",
                                                [
                                                    {"label": "All Alerts", "value": "ALL"},
                                                    {"label": "High Risk", "value": "HIGH_RISK"},
                                                    {"label": "Manual Review", "value": "MANUAL_REVIEW"},
                                                ],
                                            ),

                                        ],

                                        style={
                                            "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
                                            "padding": "12px 0",
                                            "border": "none",
                                            "boxShadow": "none",
                                        },
                                    ),

                                    dcc.Loading(
                                        create_alert_table()
                                    ),

                                ]),
                            ),


                            # =================================
                            # TRANSACTION EXPLORER
                            # =================================

                            html.Div(
                                style={"marginTop": "24px"},

                                children=[

                                    html.Div(
                                        "INVESTIGATION WORKSPACE",
                                        className="eyebrow",
                                    ),

                                    create_section_card(
                                        "Transaction Explorer",

                                        "Search, inspect and filter transactions "
                                        "with their risk decisions and alert status.",

                                        html.Div([

                                            dbc.Input(
                                                id="transaction-search",

                                                placeholder=(
                                                    "Search by source row number, "
                                                    "sender or receiver ID..."
                                                ),

                                                type="text",

                                                debounce=True,

                                                className="filter-control",

                                                style={
                                                    "marginBottom": "16px",
                                                    "backgroundColor": "#0e192b",
                                                    "color": "#edf3fc",
                                                    "borderColor": "#263650",
                                                },
                                            ),

                                            dcc.Loading(
                                                create_transaction_table()
                                            ),

                                            html.Div(
                                                id="transaction-details",

                                                className="section-card",

                                                style={
                                                    "marginTop": "18px",
                                                    "minHeight": "65px",
                                                },

                                                children=(
                                                    "Select a transaction "
                                                    "to inspect its details."
                                                ),
                                            ),

                                        ]),

                                        full_width=True,
                                    ),

                                ],
                            ),


                            # =================================
                            # FOOTER
                            # =================================

                            html.Footer(
                                className="dashboard-footer",

                                children=[

                                    html.Span(
                                        "PAYSIM FRAUD INTELLIGENCE PLATFORM"
                                    ),

                                    html.Span(
                                        "MODEL: SGDClassifier | RAW DECISION SCORE"
                                    ),

                                    html.Span(
                                        "SIMULATED MONITORING ENVIRONMENT"
                                    ),

                                ],
                            ),

                        ],
                    ),

                ],
            ),

        ],
    )
