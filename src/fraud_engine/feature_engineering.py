from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "PS_20174392719_1491204439457_log.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "outputs"

OUTPUT_PATH = OUTPUT_DIR / "paysim_features.parquet"

CHUNK_SIZE = 250_000

REQUIRED_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]

DTYPES = {
    "step": "int16",
    "type": "string",
    "amount": "float64",
    "nameOrig": "string",
    "oldbalanceOrg": "float64",
    "newbalanceOrig": "float64",
    "nameDest": "string",
    "oldbalanceDest": "float64",
    "newbalanceDest": "float64",
    "isFraud": "int8",
    "isFlaggedFraud": "int8",
}


# ============================================================
# 2. FEATURE ENGINEERING FUNCTION
# ============================================================

def create_features(chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Transform transaction data into fraud-monitoring features.

    The target isFraud is retained for supervised learning,
    but it must never be included in model input features.
    """

    # Transaction amount transformation
    log_amount = np.log1p(chunk["amount"])

    # Origin account balance behavior
    origin_balance_emptied = (
        (chunk["oldbalanceOrg"] > 0)
        & (chunk["newbalanceOrig"] == 0)
    ).astype("int8")

    # Expected versus observed origin balance
    origin_balance_error = (
        chunk["oldbalanceOrg"]
        - chunk["amount"]
        - chunk["newbalanceOrig"]
    )

    # Expected versus observed destination balance
    destination_balance_error = (
        chunk["oldbalanceDest"]
        + chunk["amount"]
        - chunk["newbalanceDest"]
    )

    # Balance discrepancy indicators
    origin_balance_mismatch = (
        origin_balance_error.abs() > 0.01
    ).astype("int8")

    destination_balance_mismatch = (
        destination_balance_error.abs() > 0.01
    ).astype("int8")

    # Construct the engineered dataset
    features = pd.DataFrame({
        "step": chunk["step"],
        "type": chunk["type"],
        "nameOrig": chunk["nameOrig"],
        "nameDest": chunk["nameDest"],
        "amount": chunk["amount"],
        "log_amount": log_amount,
        "orig_balance_emptied": origin_balance_emptied,
        "orig_balance_error": origin_balance_error,
        "dest_balance_error": destination_balance_error,
        "orig_balance_mismatch": origin_balance_mismatch,
        "dest_balance_mismatch": destination_balance_mismatch,
        "isFlaggedFraud": chunk["isFlaggedFraud"],
        "isFraud": chunk["isFraud"],
    })

    return features


# ============================================================
# 3. DATA VALIDATION
# ============================================================

def validate_dataset(data: pd.DataFrame) -> None:

    if data.empty:
        raise ValueError("An empty data chunk was detected.")

    if data["isFraud"].isna().any():
        raise ValueError("Missing values detected in isFraud.")

    if not data["isFraud"].isin([0, 1]).all():
        raise ValueError("Unexpected target values detected.")

    if (data["amount"] < 0).any():
        raise ValueError("Negative transaction amount detected.")

    balance_columns = [
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
    ]

    for column in balance_columns:
        if (data[column] < 0).any():
            raise ValueError(
                f"Negative values detected in {column}."
            )


# ============================================================
# 4. PROCESS THE FULL DATASET IN CHUNKS
# ============================================================

def main():

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Prevent accidental replacement of previous results
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_PATH}\n"
            "Rename or archive it before running again."
        )

    print("=" * 65)
    print("PAYSim FRAUD FEATURE ENGINEERING")
    print("=" * 65)

    print(f"Source: {DATA_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Chunk size: {CHUNK_SIZE:,}")

    writer = None

    total_rows = 0
    fraud_count = 0
    normal_count = 0

    transaction_types = {}

    try:

        reader = pd.read_csv(
            DATA_PATH,
            usecols=REQUIRED_COLUMNS,
            dtype=DTYPES,
            chunksize=CHUNK_SIZE,
            encoding="utf-8-sig",
        )

        for chunk_number, chunk in enumerate(reader, start=1):

            validate_dataset(chunk)

            engineered = create_features(chunk)

            table = pa.Table.from_pandas(
                engineered,
                preserve_index=False,
            )

            if writer is None:
                writer = pq.ParquetWriter(
                    OUTPUT_PATH,
                    table.schema,
                    compression="zstd",
                    use_dictionary=True,
                )

            writer.write_table(table)

            rows = len(chunk)

            total_rows += rows

            fraud_count += int(
                chunk["isFraud"].sum()
            )

            normal_count += int(
                (chunk["isFraud"] == 0).sum()
            )

            counts = chunk["type"].value_counts()

            for transaction_type, count in counts.items():
                transaction_types[transaction_type] = (
                    transaction_types.get(transaction_type, 0)
                    + int(count)
                )

            print(
                f"Chunk {chunk_number}: "
                f"{rows:,} rows processed | "
                f"Total: {total_rows:,}"
            )

        if writer is None:
            raise ValueError("No transaction rows were processed.")

        writer.close()
        writer = None

    except Exception:

        if writer is not None:
            writer.close()

        if OUTPUT_PATH.exists():
            OUTPUT_PATH.unlink()

        raise

    # ========================================================
    # 5. FINAL PROCESSING REPORT
    # ========================================================

    fraud_rate = (
        fraud_count / total_rows * 100
        if total_rows else 0
    )

    print("\n" + "=" * 65)
    print("FEATURE ENGINEERING COMPLETED")
    print("=" * 65)

    print(f"Total transactions: {total_rows:,}")
    print(f"Normal transactions: {normal_count:,}")
    print(f"Fraud transactions: {fraud_count:,}")
    print(f"Fraud rate: {fraud_rate:.4f}%")

    print("\nTransaction type distribution:")

    for transaction_type, count in sorted(
        transaction_types.items()
    ):
        print(f"{transaction_type}: {count:,}")

    print("\nOutput file:")
    print(OUTPUT_PATH)

    print(
        "Output size: "
        f"{OUTPUT_PATH.stat().st_size / (1024 ** 2):.2f} MB"
    )


if __name__ == "__main__":
    main()
