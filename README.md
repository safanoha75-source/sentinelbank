# SentinelBank
## PaySim Fraud Intelligence Module

A historical, post-transaction fraud analytics prototype using synthetic PaySim data. It combines a class-weighted `SGDClassifier(loss="log_loss")`, raw decision-margin thresholding, a three-tier risk policy, SQL Server persistence, and a Dash/Plotly investigation dashboard.

> **Scope:** Synthetic historical data only. This is not connected to a real bank and does not authorize, block, reverse, or hold real payments.

## Project highlights
- Source PaySim data: 6,362,620 rows, 11 columns, 8,213 fraud cases (~0.1291%).
- Chronological split: train 6,082,007; validation 191,147; test 89,466.
- Model: scikit-learn `SGDClassifier(loss="log_loss")`, `StandardScaler`, class weighting, incremental `partial_fit`.
- Probability saturation diagnostic: probability AP 0.2046 vs raw decision-margin AP 0.995086 on validation.
- High threshold selected on validation: 213.80866687194845. Medium threshold: 54.304175371966295 (P99 of normal validation raw margins).
- Final chronological test: Precision 1.0000, Recall 0.987220, F1 0.993569, Average Precision 0.989589; confusion matrix TN=88,214, FP=0, FN=16, TP=1,236.
- SQL Server evaluation store: 280,613 transactions, 280,613 predictions, 5,255 alerts; referential integrity checks passed.
- Dash: 4 callbacks, 23 layout IDs, three Plotly charts, transaction explorer, alert center, 30-second and manual refresh.

## Architecture
`PaySim CSV -> EDA / feature engineering -> scaled SGDClassifier -> raw decision margin -> validation thresholds -> LOW/MEDIUM/HIGH risk policy -> SQL Server -> Dash / Plotly`

## Run locally (Windows)
1. Create/activate the project virtual environment.
2. Install dashboard requirements (see `requirements-dashboard.txt`).
3. Configure SQL Server connection in `src/fraud_engine/db_connection.py` for your local environment. The project currently uses local Windows Authentication.
4. Ensure `PaySimFraudDB` and evaluation tables are loaded.
5. From the repository root: `python -m src.dashboard.app`
6. Open `http://127.0.0.1:8050`.

## Dashboard behavior
- Dataset split: ALL / VALIDATION / TEST.
- Transaction type: ALL / TRANSFER / CASH_OUT / CASH_IN / PAYMENT / DEBIT.
- Risk level: ALL / LOW / MEDIUM / HIGH. In this version, the risk filter affects type analysis and transaction explorer; the KPI query does not accept a risk-level parameter.
- Search: source row number, sender ID, receiver ID.
- Alerts: status and category filters.
- Manual and 30-second refresh.

## Important methodology notes
- **Dataset warning:** the PaySim Kaggle metadata warns that transactions detected as fraud are cancelled and advises against using the before/after balance fields for fraud detection. The current experiment includes balance-derived features, so a no-balance-feature ablation is required before treating the results as deployment evidence.
- `isFraud` is a target and is not included in model features. `nameOrig` and `nameDest` are kept for traceability/search, not predictive X. `isFlaggedFraud` was excluded from model inputs.
- Balance-after-transaction variables make the current workflow post-transaction monitoring. It is not a pre-authorization model.
- `decision_function` is a raw margin, **not a probability**. It is explicitly labeled Raw Decision Score.
- Thresholds were derived on validation and frozen for final test evaluation.
- Results on synthetic PaySim data are not a guarantee of real-world performance.

## Database tables
- `dbo.Transactions`: source transaction facts and evaluation label.
- `dbo.FraudPredictions`: model output, dataset split, score, risk tier, action.
- `dbo.FraudAlerts`: high-risk / manual-review alert records and status.

## Future modules (not part of the current fraud detector)
1. SQL Injection defensive lab: safe local demonstration of unsafe query construction vs parameterized queries and validation.
2. MITM integrity simulation: local-only message-tampering demonstration with HMAC/signature verification.
3. Cloud deployment: move to a secured remote SQL endpoint or a deliberate read-only demo data layer; use environment variables for secrets.

## Security and data handling
Never commit `.env`, database passwords, raw full dataset, model binaries unless permitted, `.venv`, or local logs. Use Git LFS or a controlled artifact store if model binaries must be shared.

## Citation / dataset note
PaySim is a synthetic financial transaction dataset. Cite the dataset source and original PaySim work required by your course or data provider in the final academic submission.
