-- HART-MCP Initial Database Schema Creation
-- This script creates the initial database schema for the enterprise HART-MCP system

-- Enable SQL CLR integration (required for quantum model functions)
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'clr enabled', 1;
RECONFIGURE;

-- Create main application schema
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'hart')
    EXEC('CREATE SCHEMA hart');
GO

-- Knowledge Store tables
CREATE TABLE hart.KnowledgeItems (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    DocumentId NVARCHAR(450) NOT NULL,
    Content NVARCHAR(MAX) NOT NULL,
    SourceType NVARCHAR(100) NOT NULL,
    SourceUri NVARCHAR(2000) NULL,
    Metadata NVARCHAR(MAX) NULL,
    VectorEmbedding VARBINARY(MAX) NULL,
    CreatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    Version INT NOT NULL DEFAULT 1,
    
    INDEX IX_KnowledgeItems_DocumentId NONCLUSTERED (DocumentId),
    INDEX IX_KnowledgeItems_SourceType NONCLUSTERED (SourceType),
    INDEX IX_KnowledgeItems_CreatedAt NONCLUSTERED (CreatedAt)
);

-- Document processing queue
CREATE TABLE hart.DocumentProcessingQueue (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    DocumentPath NVARCHAR(2000) NOT NULL,
    DocumentType NVARCHAR(100) NOT NULL,
    Status NVARCHAR(50) NOT NULL DEFAULT 'Pending',
    Priority INT NOT NULL DEFAULT 0,
    CreatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    ProcessedAt DATETIME2 NULL,
    ErrorMessage NVARCHAR(MAX) NULL,
    
    INDEX IX_DocumentProcessingQueue_Status_Priority NONCLUSTERED (Status, Priority),
    INDEX IX_DocumentProcessingQueue_CreatedAt NONCLUSTERED (CreatedAt)
);

-- User interaction logging
CREATE TABLE hart.UserInteractions (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    UserId NVARCHAR(256) NULL,
    SessionId NVARCHAR(256) NOT NULL,
    QueryText NVARCHAR(MAX) NOT NULL,
    ResponseText NVARCHAR(MAX) NULL,
    QueryType NVARCHAR(100) NOT NULL,
    ResponseTimeMs INT NULL,
    CreatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    INDEX IX_UserInteractions_UserId NONCLUSTERED (UserId),
    INDEX IX_UserInteractions_SessionId NONCLUSTERED (SessionId),
    INDEX IX_UserInteractions_CreatedAt NONCLUSTERED (CreatedAt)
);

-- System metrics and monitoring
CREATE TABLE hart.SystemMetrics (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    MetricName NVARCHAR(200) NOT NULL,
    MetricValue DECIMAL(18,4) NOT NULL,
    MetricUnit NVARCHAR(50) NULL,
    MetricTags NVARCHAR(MAX) NULL, -- JSON
    RecordedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    INDEX IX_SystemMetrics_MetricName_RecordedAt NONCLUSTERED (MetricName, RecordedAt),
    INDEX IX_SystemMetrics_RecordedAt NONCLUSTERED (RecordedAt)
);

-- Quantum model metadata (for SQL CLR integration)
CREATE TABLE hart.QuantumModels (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    ModelName NVARCHAR(200) NOT NULL UNIQUE,
    ModelPath NVARCHAR(2000) NOT NULL,
    ParameterCount BIGINT NOT NULL,
    ModelVersion NVARCHAR(100) NOT NULL,
    LoadedAt DATETIME2 NULL,
    LastUsedAt DATETIME2 NULL,
    IsActive BIT NOT NULL DEFAULT 0,
    Configuration NVARCHAR(MAX) NULL, -- JSON
    
    INDEX IX_QuantumModels_IsActive NONCLUSTERED (IsActive),
    INDEX IX_QuantumModels_LastUsedAt NONCLUSTERED (LastUsedAt)
);

-- Audit logging
CREATE TABLE hart.AuditLog (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    EntityName NVARCHAR(200) NOT NULL,
    EntityId NVARCHAR(450) NULL,
    Action NVARCHAR(100) NOT NULL,
    UserId NVARCHAR(256) NULL,
    Changes NVARCHAR(MAX) NULL, -- JSON
    Timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    INDEX IX_AuditLog_EntityName_Timestamp NONCLUSTERED (EntityName, Timestamp),
    INDEX IX_AuditLog_UserId_Timestamp NONCLUSTERED (UserId, Timestamp)
);

-- Create stored procedures for common operations
GO
CREATE PROCEDURE hart.GetKnowledgeItems
    @DocumentId NVARCHAR(450) = NULL,
    @SourceType NVARCHAR(100) = NULL,
    @PageSize INT = 100,
    @PageNumber INT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @Offset INT = (@PageNumber - 1) * @PageSize;
    
    SELECT 
        Id,
        DocumentId,
        Content,
        SourceType,
        SourceUri,
        Metadata,
        CreatedAt,
        UpdatedAt,
        Version
    FROM hart.KnowledgeItems
    WHERE (@DocumentId IS NULL OR DocumentId = @DocumentId)
      AND (@SourceType IS NULL OR SourceType = @SourceType)
    ORDER BY UpdatedAt DESC
    OFFSET @Offset ROWS
    FETCH NEXT @PageSize ROWS ONLY;
END;

GO
CREATE PROCEDURE hart.LogUserInteraction
    @UserId NVARCHAR(256) = NULL,
    @SessionId NVARCHAR(256),
    @QueryText NVARCHAR(MAX),
    @ResponseText NVARCHAR(MAX) = NULL,
    @QueryType NVARCHAR(100),
    @ResponseTimeMs INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO hart.UserInteractions (
        UserId, SessionId, QueryText, ResponseText, 
        QueryType, ResponseTimeMs
    )
    VALUES (
        @UserId, @SessionId, @QueryText, @ResponseText,
        @QueryType, @ResponseTimeMs
    );
END;

GO
CREATE PROCEDURE hart.RecordSystemMetric
    @MetricName NVARCHAR(200),
    @MetricValue DECIMAL(18,4),
    @MetricUnit NVARCHAR(50) = NULL,
    @MetricTags NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO hart.SystemMetrics (
        MetricName, MetricValue, MetricUnit, MetricTags
    )
    VALUES (
        @MetricName, @MetricValue, @MetricUnit, @MetricTags
    );
END;

-- Create indexes for performance
CREATE INDEX IX_KnowledgeItems_UpdatedAt_Includes 
ON hart.KnowledgeItems (UpdatedAt) 
INCLUDE (Id, DocumentId, Content, SourceType);

CREATE INDEX IX_UserInteractions_CreatedAt_Includes 
ON hart.UserInteractions (CreatedAt) 
INCLUDE (UserId, SessionId, QueryType, ResponseTimeMs);

-- Create views for common queries
GO
CREATE VIEW hart.vw_RecentInteractions AS
SELECT 
    ui.Id,
    ui.UserId,
    ui.SessionId,
    ui.QueryText,
    ui.QueryType,
    ui.ResponseTimeMs,
    ui.CreatedAt
FROM hart.UserInteractions ui
WHERE ui.CreatedAt >= DATEADD(day, -30, GETUTCDATE());

GO
CREATE VIEW hart.vw_ActiveQuantumModels AS
SELECT 
    qm.Id,
    qm.ModelName,
    qm.ParameterCount,
    qm.ModelVersion,
    qm.LoadedAt,
    qm.LastUsedAt,
    qm.Configuration
FROM hart.QuantumModels qm
WHERE qm.IsActive = 1;

PRINT 'HART-MCP database schema created successfully.';
PRINT 'Remember to deploy SQL CLR assemblies for quantum model functionality.';
GO