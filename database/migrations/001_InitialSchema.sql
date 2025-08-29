-- HART-MCP Database Initial Schema
-- Migration: 001_InitialSchema
-- Created: $(date)

USE [master]
GO

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'HART_MCP')
BEGIN
    CREATE DATABASE [HART_MCP]
    COLLATE SQL_Latin1_General_CP1_CI_AS;
END
GO

USE [HART_MCP]
GO

-- Enable CLR integration
IF NOT EXISTS (SELECT * FROM sys.configurations WHERE name = 'clr enabled' AND value = 1)
BEGIN
    EXEC sp_configure 'clr enabled', 1;
    RECONFIGURE;
END
GO

-- Core application tables
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Documents')
BEGIN
    CREATE TABLE [Documents] (
        [Id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        [Title] NVARCHAR(255) NOT NULL,
        [Content] NVARCHAR(MAX) NOT NULL,
        [ContentType] NVARCHAR(100) NOT NULL DEFAULT 'text/plain',
        [Hash] NVARCHAR(64) NOT NULL,
        [Size] BIGINT NOT NULL DEFAULT 0,
        [CreatedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [UpdatedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [IsActive] BIT NOT NULL DEFAULT 1,
        [Metadata] NVARCHAR(MAX) NULL -- JSON metadata
    );
    
    CREATE INDEX IX_Documents_Hash ON [Documents] ([Hash]);
    CREATE INDEX IX_Documents_CreatedAt ON [Documents] ([CreatedAt]);
    CREATE INDEX IX_Documents_ContentType ON [Documents] ([ContentType]);
END
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Embeddings')
BEGIN
    CREATE TABLE [Embeddings] (
        [Id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        [DocumentId] UNIQUEIDENTIFIER NOT NULL,
        [VectorId] NVARCHAR(255) NOT NULL, -- Milvus collection ID
        [EmbeddingModel] NVARCHAR(100) NOT NULL DEFAULT 'text-embedding-ada-002',
        [ChunkIndex] INT NOT NULL DEFAULT 0,
        [ChunkText] NVARCHAR(MAX) NOT NULL,
        [CreatedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        FOREIGN KEY ([DocumentId]) REFERENCES [Documents]([Id]) ON DELETE CASCADE
    );
    
    CREATE INDEX IX_Embeddings_DocumentId ON [Embeddings] ([DocumentId]);
    CREATE INDEX IX_Embeddings_VectorId ON [Embeddings] ([VectorId]);
END
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'KnowledgeGraph')
BEGIN
    CREATE TABLE [KnowledgeGraph] (
        [Id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        [DocumentId] UNIQUEIDENTIFIER NOT NULL,
        [Neo4jNodeId] NVARCHAR(255) NOT NULL, -- Neo4j node ID
        [EntityType] NVARCHAR(100) NOT NULL,
        [EntityName] NVARCHAR(500) NOT NULL,
        [Properties] NVARCHAR(MAX) NULL, -- JSON properties
        [CreatedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        FOREIGN KEY ([DocumentId]) REFERENCES [Documents]([Id]) ON DELETE CASCADE
    );
    
    CREATE INDEX IX_KnowledgeGraph_DocumentId ON [KnowledgeGraph] ([DocumentId]);
    CREATE INDEX IX_KnowledgeGraph_EntityType ON [KnowledgeGraph] ([EntityType]);
    CREATE INDEX IX_KnowledgeGraph_Neo4jNodeId ON [KnowledgeGraph] ([Neo4jNodeId]);
END
GO

-- Audit and logging tables
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'AuditLogs')
BEGIN
    CREATE TABLE [AuditLogs] (
        [Id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        [UserId] NVARCHAR(255) NULL,
        [Action] NVARCHAR(100) NOT NULL,
        [EntityType] NVARCHAR(100) NOT NULL,
        [EntityId] NVARCHAR(255) NULL,
        [Changes] NVARCHAR(MAX) NULL, -- JSON of changes
        [Timestamp] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [IPAddress] NVARCHAR(45) NULL,
        [UserAgent] NVARCHAR(500) NULL
    );
    
    CREATE INDEX IX_AuditLogs_Timestamp ON [AuditLogs] ([Timestamp]);
    CREATE INDEX IX_AuditLogs_UserId ON [AuditLogs] ([UserId]);
    CREATE INDEX IX_AuditLogs_Action ON [AuditLogs] ([Action]);
END
GO

-- Configuration and system tables
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'SystemConfiguration')
BEGIN
    CREATE TABLE [SystemConfiguration] (
        [Key] NVARCHAR(255) PRIMARY KEY,
        [Value] NVARCHAR(MAX) NOT NULL,
        [Description] NVARCHAR(1000) NULL,
        [IsEncrypted] BIT NOT NULL DEFAULT 0,
        [UpdatedAt] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [UpdatedBy] NVARCHAR(255) NULL
    );
    
    -- Insert default configuration
    INSERT INTO [SystemConfiguration] ([Key], [Value], [Description])
    VALUES 
        ('SchemaVersion', '1.0.0', 'Current database schema version'),
        ('MaxDocumentSize', '52428800', 'Maximum document size in bytes (50MB)'),
        ('DefaultEmbeddingModel', 'text-embedding-ada-002', 'Default embedding model to use'),
        ('EnableAuditLogging', 'true', 'Enable audit logging for all operations');
END
GO

-- Create stored procedures for common operations
IF NOT EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_InsertDocument')
BEGIN
    EXEC('
    CREATE PROCEDURE [dbo].[sp_InsertDocument]
        @Title NVARCHAR(255),
        @Content NVARCHAR(MAX),
        @ContentType NVARCHAR(100) = ''text/plain'',
        @Hash NVARCHAR(64),
        @Size BIGINT,
        @Metadata NVARCHAR(MAX) = NULL,
        @DocumentId UNIQUEIDENTIFIER OUTPUT
    AS
    BEGIN
        SET NOCOUNT ON;
        
        SET @DocumentId = NEWID();
        
        INSERT INTO [Documents] ([Id], [Title], [Content], [ContentType], [Hash], [Size], [Metadata])
        VALUES (@DocumentId, @Title, @Content, @ContentType, @Hash, @Size, @Metadata);
        
        -- Log the action
        INSERT INTO [AuditLogs] ([Action], [EntityType], [EntityId])
        VALUES (''INSERT'', ''Document'', CAST(@DocumentId AS NVARCHAR(36)));
    END');
END
GO

-- Create function to check system health
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = 'fn_SystemHealthCheck' AND type = 'FN')
BEGIN
    EXEC('
    CREATE FUNCTION [dbo].[fn_SystemHealthCheck]()
    RETURNS TABLE
    AS
    RETURN
    (
        SELECT 
            ''Database'' AS Component,
            CASE 
                WHEN DB_ID() IS NOT NULL THEN ''Healthy''
                ELSE ''Unhealthy''
            END AS Status,
            GETUTCDATE() AS CheckedAt
        UNION ALL
        SELECT 
            ''Documents'',
            CASE 
                WHEN EXISTS (SELECT 1 FROM [Documents]) THEN ''Has Data''
                ELSE ''No Data''
            END,
            GETUTCDATE()
        UNION ALL
        SELECT 
            ''CLR Integration'',
            CASE 
                WHEN (SELECT value FROM sys.configurations WHERE name = ''clr enabled'') = 1 THEN ''Enabled''
                ELSE ''Disabled''
            END,
            GETUTCDATE()
    )');
END
GO

PRINT 'Initial schema migration completed successfully';
GO