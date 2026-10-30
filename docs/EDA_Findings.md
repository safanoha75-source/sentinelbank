# PaySim Fraud Detection Engine
## Exploratory Data Analysis (EDA) Findings

---

## 1. Project Objective

The objective is to develop an AI-based financial fraud detection engine
that analyzes financial transactions, estimates fraud probability,
assigns a risk level, and recommends an appropriate action.

The initial project uses the PaySim financial transaction dataset.

---

## 2. Dataset Selection

Primary dataset:

PS_20174392719_1491204439457_log.csv

Dataset size: 6,362,620 transactions
Number of columns: 11
Fraud transactions: 8,213
Normal transactions: 6,354,407
Fraud rate: approximately 0.1291%

Other available files:

- paysim.csv: 1,048,575 rows, 11 columns, 1,142 fraud cases.
- paysim_prepared.csv: 460,394 rows, 9 columns, 1,142 fraud cases.

Decision:
The full original dataset is selected as the primary data source.
The other two files are retained for comparison and are not modified.

---

## 3. Data Quality Findings

The full dataset was examined.

Findings:

- Total rows: 6,362,620
- Missing values: 0
- Invalid numeric values: 0
- Negative transaction amounts: 0
- Negative balances: 0
- Target values: 0 and 1

Numeric columns examined:

- step
- amount
- oldbalanceOrg
- newbalanceOrig
- oldbalanceDest
- newbalanceDest
- isFraud
- isFlaggedFraud

Decision:
No missing-value imputation is currently required.
The original dataset will remain unchanged.

---

## 4. Class Imbalance

Normal transactions: 6,354,407
Fraud transactions: 8,213
Fraud percentage: approximately 0.1291%

The dataset is severely imbalanced.

Important implication:
Accuracy alone is not sufficient for evaluating the fraud detection model.

Evaluation metrics will include:

- Precision
- Recall
- F1-score
- PR-AUC
- Confusion Matrix

Class imbalance strategies will be evaluated during model development.
Any resampling must be applied to training data only.

---

## 5. Transaction Type Analysis

| Transaction Type | Total | Fraud | Fraud Rate |
|---|---:|---:|---:|
| CASH_IN | 1,399,284 | 0 | 0.0000% |
| CASH_OUT | 2,237,500 | 4,116 | 0.1840% |
| DEBIT | 41,432 | 0 | 0.0000% |
| PAYMENT | 2,151,495 | 0 | 0.0000% |
| TRANSFER | 532,909 | 4,097 | 0.7688% |

Observation:
In this dataset, fraudulent transactions appear in TRANSFER and CASH_OUT.

TRANSFER has a higher fraud rate than CASH_OUT.

These observations describe the available dataset and must not be
treated as universal rules for all financial transactions.

---

## 6. Existing Fraud Flag Analysis

The dataset contains the column isFlaggedFraud.

Flagged transactions: 16
Actual fraud transactions: 8,213
Fraud cases flagged: 16

Observed recall of the existing flag:

16 / 8,213 = approximately 0.1948%

Observed precision of the existing flag:

16 / 16 = 100%

Interpretation:
The existing flag identifies very few of the actual fraud cases.

Decision:
isFlaggedFraud will be excluded from the initial machine learning
feature set and retained for separate analytical comparison.

This avoids giving the model an existing fraud-system decision
as an input feature.

---

## 7. Fraud vs Normal Financial Behavior

### H1 - Transaction Amount

TRANSFER:
- Normal average: 906,229.01
- Fraud average: 1,480,891.67

CASH_OUT:
- Normal average: 173,917.16
- Fraud average: 1,455,102.59

Hypothesis:
Fraudulent transactions may have different amount distributions
from normal transactions.

Planned experiment:
- Compare mean, median, and percentiles.
- Examine amount distributions.
- Evaluate amount and log-transformed amount as features.

Feature candidates:
- amount
- log_amount

The average alone is not sufficient to classify a transaction.

### H2 - Origin Balance Emptied

TRANSFER:
- Normal: 224,728 (42.50%)
- Fraud: 3,934 (96.02%)

CASH_OUT:
- Normal: 955,334 (42.78%)
- Fraud: 4,078 (99.08%)

Hypothesis:
An origin account becoming empty after a transaction may be
a useful indicator of suspicious financial behavior.

Candidate feature:
orig_balance_emptied

Proposed calculation:

(oldbalanceOrg > 0) AND (newbalanceOrig == 0)

This feature is an indicator, not proof of fraud.

### H3 - Origin Balance Mismatch

TRANSFER:
- Normal: 508,761 (96.21%)
- Fraud: 21 (0.51%)

CASH_OUT:
- Normal: 1,991,245 (89.16%)
- Fraud: 24 (0.58%)

Hypothesis:
Origin balance discrepancies may distinguish some transaction
patterns, but the observed mismatch rate is much higher in
normal transactions in this dataset.

Decision:
Do not assume that an origin balance mismatch means fraud.
Investigate and test this feature before relying on it.

### H4 - Destination Balance Mismatch

TRANSFER:
- Normal: 116,716 (22.07%)
- Fraud: 4,095 (99.95%)

CASH_OUT:
- Normal: 506,881 (22.70%)
- Fraud: 545 (13.24%)

Hypothesis:
Destination balance mismatch may be informative for TRANSFER
transactions, but its behavior differs between transaction types.

Decision:
Test this feature together with transaction type.
Do not use it as a universal fraud rule.

---

## 8. Candidate Feature Engineering

Initial candidate features:

| Feature | Description |
|---|---|
| amount | Transaction amount |
| log_amount | Log-transformed transaction amount |
| type | Transaction type |
| orig_balance_emptied | Whether the origin balance became zero |
| orig_balance_error | Difference between expected and observed origin balance |
| dest_balance_error | Difference between expected and observed destination balance |
| orig_balance_mismatch | Whether origin balances differ beyond tolerance |
| dest_balance_mismatch | Whether destination balances differ beyond tolerance |

Target column:

isFraud

The target must never be used as an input feature.

Identifier columns nameOrig and nameDest will not be
direct inputs to the initial model.

---

## 9. Data Leakage and Prediction Timing

Two different prediction scenarios must be considered.

### Pre-Transaction Detection

Uses information available before the transaction is executed.

Post-transaction balances must not be used if they are not
available at the prediction time.

### Post-Transaction Monitoring

Uses transaction and updated balance information to detect
suspicious activity after the transaction.

The project must clearly distinguish these scenarios.

isFlaggedFraud will not be used as an input feature in the
initial model.

The training and validation process must avoid data leakage.
Any resampling, scaling, and preprocessing must be fitted
using training data only.

---

## 10. Model Evaluation Strategy

The initial model experiments will compare suitable classifiers.

Evaluation will focus on:

- Precision
- Recall
- F1-score
- PR-AUC
- Confusion Matrix

The model will not be selected using Accuracy alone.

The final choice will depend on validation results and the
operational balance between missed fraud and false alerts.

---

## 11. Planned System Architecture

1. PaySim Data Source
2. Data Validation and Preprocessing
3. Feature Engineering
4. Fraud Detection Model
5. Fraud Probability
6. Risk Assessment Engine
7. Decision and Alert Engine
8. SQL Server Storage
9. Dash and Plotly Monitoring Dashboard

High-risk actions will initially be simulated and will not
execute real banking transactions.

---

## 12. Current Project Status

Completed:
- Dataset inventory
- Dataset selection analysis
- Data quality examination
- Class distribution analysis
- Transaction type analysis
- Existing fraud flag analysis
- Initial financial behavior hypotheses

Pending:
- Formal feature engineering implementation
- Train/validation/test split
- Machine learning experiments
- Model evaluation and selection
- Risk scoring and decision engine
- SQL Server integration
- Dashboard development
- Alert simulation
- Final documentation and presentation

---

## 13. Evidence and Reproducibility

All numeric findings in this document are based on the
PowerShell analysis outputs obtained during the current
project workflow.

The original PaySim dataset has not been modified.

Further experiments must record their methodology, results,
and limitations before conclusions are drawn.
