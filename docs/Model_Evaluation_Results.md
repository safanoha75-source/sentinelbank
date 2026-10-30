# PaySim Fraud Detection Engine
# Final Model Evaluation Report

## 1. Experiment

Model: SGDClassifier
Loss: log_loss
Prediction scenario: Post-Transaction Fraud Monitoring

Dataset: PaySim
Evaluation: Chronological holdout test

Training steps: 1-520
Validation steps: 521-631
Test steps: 632-743

## 2. Fixed Decision Threshold

Threshold: 213.80866687194845

Selection method:
Maximum F1-score using validation raw decision scores.

The threshold was selected using Validation only.
The model was not retrained on Test.
The threshold was not adjusted using Test.

## 3. Final Test Dataset

Total transactions: 89,466
Normal transactions: 88,214
Fraud transactions: 1,252

Fraud prevalence: 1.399414%

## 4. Final Test Metrics

| Metric | Result |
|---|---:|
| Accuracy | 0.999821 |
| Precision | 1.000000 |
| Recall | 0.987220 |
| F1-score | 0.993569 |
| Average Precision | 0.989589 |

Precision lift over fraud prevalence: 71.46x

## 5. Confusion Matrix

| | Predicted Normal | Predicted Fraud |
|---|---:|---:|
| Actual Normal | 88,214 | 0 |
| Actual Fraud | 16 | 1,236 |

True Negative: 88,214
False Positive: 0
False Negative: 16
True Positive: 1,236

## 6. Interpretation

The model detected 1,236 of the 1,252 fraudulent
transactions in the held-out test period.

Sixteen fraudulent transactions were missed.

No false-positive fraud alerts were observed at the
selected threshold on this test sample.

The results indicate strong discrimination on this
PaySim chronological holdout test.

These results do not guarantee equivalent performance
on real banking transactions or other datasets.

## 7. Important Methodological Limitations

1. PaySim is a simulated financial transaction dataset.
2. The current system is designed for post-transaction monitoring.
3. Post-transaction balance information is used in feature
   engineering and must not be treated as available before
   transaction execution.
4. Test metrics describe this particular held-out period.
5. Zero false positives in this sample do not guarantee
   zero false positives in future transactions.
6. Operational thresholds should be reviewed using
   additional data and business costs.

## 8. Model Artifacts

Model:
outputs/fraud_sgd_bundle.joblib

Validation report:
reports/fraud_sgd_validation_metrics.json

Threshold analysis:
reports/sgd_margin_threshold_analysis.json

Final test report:
reports/fraud_sgd_test_metrics.json

## 9. Next Development Phase

- Implement Risk Assessment Engine.
- Implement Decision and Alert Engine.
- Store prediction results in SQL Server.
- Build interactive Dash and Plotly dashboard.
- Test high-risk alert simulation.
- Prepare final technical documentation and presentation.

## 10. Experiment Status

Final chronological test evaluation completed.

The test dataset was not used for model training
or threshold selection.
