USE PaySimFraudDB;
GO

-- =====================================================
-- TABLE 1: TRANSACTIONS
-- Stores original PaySim transaction records.
-- =====================================================

IF OBJECT_ID('dbo.Transactions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Transactions
    (
        TransactionID BIGINT IDENTITY(1,1) NOT NULL,

        Step SMALLINT NOT NULL,

        TransactionType VARCHAR(20) NOT NULL,

        Amount DECIMAL(19,4) NOT NULL,

        NameOrig VARCHAR(32) NOT NULL,

        OldBalanceOrg DECIMAL(19,4) NOT NULL,

        NewBalanceOrig DECIMAL(19,4) NOT NULL,

        NameDest VARCHAR(32) NOT NULL,

        OldBalanceDest DECIMAL(19,4) NOT NULL,

        NewBalanceDest DECIMAL(19,4) NOT NULL,

        IsFraud BIT NOT NULL,

        IsFlaggedFraud BIT NOT NULL,

        LoadedAtUtc DATETIME2(0)
            NOT NULL DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_Transactions
            PRIMARY KEY CLUSTERED (TransactionID),

        CONSTRAINT CK_Transactions_Step
            CHECK (Step > 0),

        CONSTRAINT CK_Transactions_Amount
            CHECK (Amount >= 0),

        CONSTRAINT CK_Transactions_Type
            CHECK (
                TransactionType IN (
                    'CASH_IN',
                    'CASH_OUT',
                    'DEBIT',
                    'PAYMENT',
                    'TRANSFER'
                )
            ),

        CONSTRAINT CK_Transactions_Balances
            CHECK (
                OldBalanceOrg >= 0
                AND NewBalanceOrig >= 0
                AND OldBalanceDest >= 0
                AND NewBalanceDest >= 0
            )
    );
END;
GO


-- =====================================================
-- TABLE 2: FRAUD PREDICTIONS
-- Stores model predictions for transactions.
-- =====================================================

IF OBJECT_ID('dbo.FraudPredictions', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.FraudPredictions
    (
        PredictionID BIGINT IDENTITY(1,1) NOT NULL,

        TransactionID BIGINT NOT NULL,

        ModelName VARCHAR(100) NOT NULL,

        ModelVersion VARCHAR(50) NOT NULL,

        RawDecisionScore FLOAT NOT NULL,

        DecisionThreshold FLOAT NOT NULL,

        PredictedFraud BIT NOT NULL,

        RiskLevel VARCHAR(10) NOT NULL,

        RecommendedAction VARCHAR(50) NOT NULL,

        ScoreType VARCHAR(30)
            NOT NULL DEFAULT 'RAW_DECISION_SCORE',

        PredictionScenario VARCHAR(50)
            NOT NULL DEFAULT 'POST_TRANSACTION_MONITORING',

        ScoredAtUtc DATETIME2(0)
            NOT NULL DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_FraudPredictions
            PRIMARY KEY CLUSTERED (PredictionID),

        CONSTRAINT FK_Predictions_Transactions
            FOREIGN KEY (TransactionID)
            REFERENCES dbo.Transactions(TransactionID),

        CONSTRAINT UQ_Predictions_Transaction_Model
            UNIQUE (TransactionID, ModelName, ModelVersion),

        CONSTRAINT CK_Predictions_RiskLevel
            CHECK (
                RiskLevel IN ('LOW', 'MEDIUM', 'HIGH')
            ),

        CONSTRAINT CK_Predictions_Action
            CHECK (
                RecommendedAction IN (
                    'MONITOR',
                    'MANUAL_REVIEW',
                    'ALERT_AND_SIMULATED_HOLD'
                )
            )
    );
END;
GO


-- =====================================================
-- TABLE 3: FRAUD ALERTS
-- Stores high-risk alerts and manual review cases.
-- =====================================================

IF OBJECT_ID('dbo.FraudAlerts', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.FraudAlerts
    (
        AlertID BIGINT IDENTITY(1,1) NOT NULL,

        PredictionID BIGINT NOT NULL,

        TransactionID BIGINT NOT NULL,

        AlertType VARCHAR(30) NOT NULL,

        AlertStatus VARCHAR(20)
            NOT NULL DEFAULT 'OPEN',

        AlertMessage NVARCHAR(500) NOT NULL,

        SimulatedHold BIT
            NOT NULL DEFAULT 0,

        CreatedAtUtc DATETIME2(0)
            NOT NULL DEFAULT SYSUTCDATETIME(),

        ResolvedAtUtc DATETIME2(0) NULL,

        CONSTRAINT PK_FraudAlerts
            PRIMARY KEY CLUSTERED (AlertID),

        CONSTRAINT FK_Alerts_Predictions
            FOREIGN KEY (PredictionID)
            REFERENCES dbo.FraudPredictions(PredictionID),

        CONSTRAINT FK_Alerts_Transactions
            FOREIGN KEY (TransactionID)
            REFERENCES dbo.Transactions(TransactionID),

        CONSTRAINT UQ_Alerts_Prediction
            UNIQUE (PredictionID),

        CONSTRAINT CK_Alerts_Type
            CHECK (
                AlertType IN (
                    'HIGH_RISK',
                    'MANUAL_REVIEW'
                )
            ),

        CONSTRAINT CK_Alerts_Status
            CHECK (
                AlertStatus IN (
                    'OPEN',
                    'UNDER_REVIEW',
                    'RESOLVED',
                    'FALSE_POSITIVE'
                )
            )
    );
END;
GO


-- =====================================================
-- INDEXES
-- Improve dashboard filtering and reporting.
-- =====================================================

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Transactions_Step_Type'
      AND object_id = OBJECT_ID('dbo.Transactions')
)
BEGIN
    CREATE INDEX IX_Transactions_Step_Type
    ON dbo.Transactions(Step, TransactionType);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Transactions_IsFraud'
      AND object_id = OBJECT_ID('dbo.Transactions')
)
BEGIN
    CREATE INDEX IX_Transactions_IsFraud
    ON dbo.Transactions(IsFraud);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Predictions_RiskLevel'
      AND object_id = OBJECT_ID('dbo.FraudPredictions')
)
BEGIN
    CREATE INDEX IX_Predictions_RiskLevel
    ON dbo.FraudPredictions(RiskLevel, ScoredAtUtc);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Alerts_Status'
      AND object_id = OBJECT_ID('dbo.FraudAlerts')
)
BEGIN
    CREATE INDEX IX_Alerts_Status
    ON dbo.FraudAlerts(AlertStatus, CreatedAtUtc);
END;
GO

PRINT 'SUCCESS: PaySimFraudDB tables and indexes created.';
GO
