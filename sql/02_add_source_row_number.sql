USE PaySimFraudDB;
GO

-- Add stable source row identifier to Transactions.
IF COL_LENGTH('dbo.Transactions', 'SourceRowNumber') IS NULL
BEGIN
    IF EXISTS (SELECT 1 FROM dbo.Transactions)
        THROW 50001, 'Transactions table must be empty before migration.', 1;

    ALTER TABLE dbo.Transactions
    ADD SourceRowNumber BIGINT NULL;
END;
GO

-- Make the source identifier mandatory.
IF EXISTS (
    SELECT 1
    FROM dbo.Transactions
    WHERE SourceRowNumber IS NULL
)
    THROW 50002, 'Null source row numbers detected.', 1;
GO

ALTER TABLE dbo.Transactions
ALTER COLUMN SourceRowNumber BIGINT NOT NULL;
GO

-- Guarantee one source row number per transaction.
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_Transactions_SourceRowNumber'
      AND object_id = OBJECT_ID('dbo.Transactions')
)
BEGIN
    CREATE UNIQUE INDEX UX_Transactions_SourceRowNumber
    ON dbo.Transactions(SourceRowNumber);
END;
GO

-- Record whether a prediction belongs to validation or test.
IF COL_LENGTH('dbo.FraudPredictions', 'DatasetSplit') IS NULL
BEGIN
    ALTER TABLE dbo.FraudPredictions
    ADD DatasetSplit VARCHAR(12) NULL;
END;
GO

IF EXISTS (
    SELECT 1
    FROM dbo.FraudPredictions
    WHERE DatasetSplit IS NULL
)
    THROW 50003, 'Null DatasetSplit values detected.', 1;
GO

ALTER TABLE dbo.FraudPredictions
ALTER COLUMN DatasetSplit VARCHAR(12) NOT NULL;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_Predictions_DatasetSplit'
)
BEGIN
    ALTER TABLE dbo.FraudPredictions
    ADD CONSTRAINT CK_Predictions_DatasetSplit
    CHECK (DatasetSplit IN ('VALIDATION', 'TEST'));
END;
GO

PRINT 'SUCCESS: SourceRowNumber and DatasetSplit are ready.';
GO
