USE [HART-MCP];
GO

-- Trigger for Agents table: AFTER INSERT
CREATE OR ALTER TRIGGER Agents_AfterInsert
ON Agents
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Agents',
        CAST(i.AgentID AS NVARCHAR(100)),
        'INSERT',
        (SELECT i.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

-- Trigger for Agents table: AFTER UPDATE
CREATE OR ALTER TRIGGER Agents_AfterUpdate
ON Agents
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Agents',
        CAST(i.AgentID AS NVARCHAR(100)),
        'UPDATE',
        (SELECT i.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

-- Trigger for Agents table: AFTER DELETE
CREATE OR ALTER TRIGGER Agents_AfterDelete
ON Agents
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Agents',
        CAST(d.AgentID AS NVARCHAR(100)),
        'DELETE',
        (SELECT d.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM deleted d;
END;
GO

-- Trigger for Documents table: AFTER INSERT
CREATE OR ALTER TRIGGER Documents_AfterInsert
ON Documents
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Documents',
        CAST(i.DocumentID AS NVARCHAR(100)),
        'INSERT',
        (SELECT i.DocumentID, i.Title, i.SourceURL, i.CreatedAt FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

-- Trigger for Documents table: AFTER UPDATE
CREATE OR ALTER TRIGGER Documents_AfterUpdate
ON Documents
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Documents',
        CAST(i.DocumentID AS NVARCHAR(100)),
        'UPDATE',
        (SELECT i.DocumentID, i.Title, i.SourceURL, i.CreatedAt FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

-- Trigger for Documents table: AFTER DELETE
CREATE OR ALTER TRIGGER Documents_AfterDelete
ON Documents
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Documents',
        CAST(d.DocumentID AS NVARCHAR(100)),
        'DELETE',
        (SELECT d.DocumentID, d.Title, d.SourceURL, d.CreatedAt FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM deleted d;
END;
GO

-- Trigger for Chunks table: AFTER INSERT
CREATE OR ALTER TRIGGER Chunks_AfterInsert
ON Chunks
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Chunks',
        CAST(i.ChunkID AS NVARCHAR(100)),
        'INSERT',
        (SELECT i.ChunkID, i.DocumentID, i.Text, i.ModelName, i.ModelVersion, i.CreatedAt FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

-- Trigger for Chunks table: AFTER UPDATE
CREATE OR ALTER TRIGGER Chunks_AfterUpdate
ON Chunks
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Chunks',
        CAST(i.ChunkID AS NVARCHAR(100)),
        'UPDATE',
        (SELECT i.ChunkID, i.DocumentID, i.Text, i.ModelName, i.ModelVersion, i.CreatedAt FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM inserted i;
END;
GO

-- Trigger for Chunks table: AFTER DELETE
CREATE OR ALTER TRIGGER Chunks_AfterDelete
ON Chunks
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO ChangeLog (SourceTable, SourceID, ChangeType, Payload)
    SELECT
        'Chunks',
        CAST(d.ChunkID AS NVARCHAR(100)),
        'DELETE',
        (SELECT d.ChunkID, d.DocumentID, d.Text, d.ModelName, d.ModelVersion, d.CreatedAt FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
    FROM deleted d;
END;
GO