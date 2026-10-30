# Cloud deployment blueprint (not yet deployed)

## Important blocker
The local project uses Windows Authentication to a SQL Server Developer instance on the Windows workstation. A cloud Linux container cannot see `D:\` or use that workstation's integrated Windows login. Do not expose the workstation SQL Server publicly or hard-code credentials.

Choose one of these approaches before deployment:

### A. Keep SQL Server
1. Provision a reachable managed SQL Server / Azure SQL endpoint.
2. Restore/create the three tables and load the approved evaluation data.
3. Create a least-privilege database login for the web app.
4. Refactor `src/fraud_engine/db_connection.py` to read `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_DRIVER`, `DB_ENCRYPT`, and `DB_TRUST_SERVER_CERTIFICATE` from environment variables.
5. Use encrypted ODBC Driver 18 connection settings; do not commit credentials.
6. Restrict network access to trusted service egress / private networking where available.
7. Add the environment variables in the hosting dashboard as secrets.

### B. Move the dashboard data layer to a cloud database
A cloud-managed Postgres is another option, but this requires converting the current SQL Server T-SQL queries, schema and loader. It is not a drop-in change.

## Render service
- Service type: Web Service (Docker).
- Repository: connect the GitHub repository.
- Blueprint: `render.yaml`.
- Container: `Dockerfile.render`.
- App entry point: `src.dashboard.app:server`.
- Public URL: Render assigns an `onrender.com` URL after a successful deploy.

Free Render web services spin down after 15 minutes of inactivity and may take about one minute to spin up on the next request. Free service filesystems are ephemeral; do not store the database, credentials or durable uploads in the container filesystem.

## Required app code change
The existing local `db_connection.py` must be changed to build the pyodbc connection from environment variables, e.g. use `DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=...;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30`. Keep the current Windows Authentication path for local runs if desired, selected by environment. Verify this against the actual local file before replacing it.

## Deploy checklist
- [ ] GitHub repository contains source, SQL scripts, documentation, no secrets, no `.venv`, and no raw full CSV.
- [ ] Remote SQL database exists, is reachable and contains expected tables/data.
- [ ] Cloud connection uses secrets and encrypted TLS.
- [ ] `gunicorn` starts `src.dashboard.app:server`.
- [ ] `/` health check returns HTTP 200.
- [ ] Check first callback execution and logs for successful DB access.
- [ ] Test all filters and searches on the public URL.
- [ ] Document free-tier cold-start and data persistence limitations.

A deployment config file is a blueprint; it does not create a live service or URL by itself. A live link exists only after account authorization, repository connection, database setup and successful deploy.

## Dataset / model validity gate
Before presenting the cloud version as an operational fraud detector, run the planned ablation that removes all raw and engineered balance features. The PaySim Kaggle metadata warns that detected fraud transactions are cancelled and says not to use the balance columns for fraud detection. Preserve the current model as an experiment, but compare a balance-free model using the same chronological split and validation-only threshold selection.
