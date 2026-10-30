# Temporal Split Analysis

## 1. Objective

Evaluate a chronological train, validation, and test split
for the PaySim Fraud Detection Engine.

## 2. Split Boundaries

| Split | Start Step | End Step | Transactions | Fraud | Normal | Fraud Rate |
|---|---:|---:|---:|---:|---:|---:|
| Train | 1 | 520 | 6,082,007 | 5,781 | 6,076,226 | 0.0951% |
| Validation | 521 | 631 | 191,147 | 1,180 | 189,967 | 0.6173% |
| Test | 632 | 743 | 89,466 | 1,252 | 88,214 | 1.3994% |

## 3. Important Observation: Temporal Distribution Shift

The fraud rate increases across the three chronological periods:

- Train: 0.0951%
- Validation: 0.6173%
- Test: 1.3994%

The test fraud rate is approximately 14.7 times the training
fraud rate.

This indicates a substantial change in the observed fraud
prevalence over time.

## 4. Interpretation

This difference is not automatically a data error.

It may reflect a change in the simulated transaction patterns
or fraud prevalence over time.

The model must therefore be evaluated on later transactions,
rather than relying only on random splitting.

## 5. Modeling Decisions

- Preserve chronological separation.
- Fit preprocessing using training data only.
- Use validation data for model selection and threshold tuning.
- Keep test data untouched until final evaluation.
- Report Precision, Recall, F1-score, Average Precision,
  and the Confusion Matrix.
- Interpret Precision in the context of changing fraud prevalence.

## 6. Transaction Count Clarification

The 70%, 15%, and 15% proportions refer to time-step ranges,
not to the number of transaction rows.

Actual row proportions are approximately:

- Train: 95.6%
- Validation: 3.0%
- Test: 1.4%

## 7. Conclusion

The chronological split contains fraud cases in all three
periods and is retained for the initial future-period
monitoring experiment.

The observed temporal shift must be considered when evaluating
model performance and designing risk thresholds.

The split audit is stored in:

reports/time_split_audit.csv
