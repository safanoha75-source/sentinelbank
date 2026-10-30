from pathlib import Path

from dash import Dash
import dash_bootstrap_components as dbc

from src.dashboard.components.layout import build_layout

from src.dashboard.callbacks.dashboard_callbacks import (
    register_analytics_callbacks,
)

from src.dashboard.callbacks.transaction_callbacks import (
    register_transaction_callbacks,
)

from src.dashboard.callbacks.alert_callbacks import (
    register_alert_callbacks,
)


# Application paths
DASHBOARD_DIR = Path(__file__).resolve().parent
ASSETS_DIR = DASHBOARD_DIR / "assets"


# Create the Dash application
app = Dash(
    __name__,
    title="PaySim Fraud Intelligence Platform",
    update_title="Updating Fraud Intelligence Dashboard...",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    assets_folder=str(ASSETS_DIR),
    suppress_callback_exceptions=False,
)


# Build the user interface
app.layout = build_layout()


# Register all dashboard callback modules
register_analytics_callbacks(app)
register_transaction_callbacks(app)
register_alert_callbacks(app)


# WSGI server
server = app.server


# Run application
if __name__ == "__main__":

    print("=" * 65)
    print("PAYSIM FRAUD INTELLIGENCE PLATFORM")
    print("=" * 65)
    print("Application: READY")
    print(f"Assets directory: {ASSETS_DIR}")
    print(f"Registered callbacks: {len(app.callback_map)}")
    print("Database: SQL Server / PaySimFraudDB")
    print("Automatic refresh: 30 seconds")
    print("Monitoring: Historical post-transaction analysis")
    print("Banking actions: Simulation only")
    print("=" * 65)
    print("Dashboard URL: http://127.0.0.1:8050")
    print("=" * 65)

    app.run(
        host="127.0.0.1",
        port=8050,
        debug=False,
        use_reloader=False,
    )
