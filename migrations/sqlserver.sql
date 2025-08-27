-- FILE: tables.sql
-- This file contains the core schema for the agent system.
-- The Agents table is the central hub for our actors.
CREATE TABLE Agents
(
    AgentID INT IDENTITY PRIMARY KEY,
    Name NVARCHAR(255) NOT NULL UNIQUE,
    Role NVARCHAR(100),
    -- e.g., 'Data Analyst', 'Task Planner', 'Reflector'
    Status NVARCHAR(50)
);
GO
-- The Documents table stores metadata and the document binary.
CREATE TABLE Documents
(
    DocumentID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    Title NVARCHAR(MAX),
    SourceURL NVARCHAR(MAX),
    -- For Windows, use the FILESTREAM attribute for large files. For Linux,
    -- VARBINARY(MAX) is the correct approach as it stores data directly in the table.
    DocumentContent VARBINARY(MAX) FILESTREAM NULL,
    -- DocumentContent VARBINARY(MAX) NOT NULL,
    DocumentContent VARBINARY(MAX) FILESTREAM NULL,
    CreatedAt DATETIME DEFAULT GETDATE()
);
GO
-- The Chunks table holds the segmented text and their vectors.
CREATE TABLE Chunks
(
    ChunkID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    DocumentID UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Documents(DocumentID),
    Text NVARCHAR(MAX),
    -- The native VECTOR data type is used here, as it's a first-class citizen in SQL Server 2025.
    Embedding VECTOR(1536),
    ModelName NVARCHAR(100),
    ModelVersion NVARCHAR(50),
    CreatedAt DATETIME DEFAULT GETDATE()
);
GO
-- The AgentLogs table is the heart of the agentic workflow, storing JSON data.
CREATE TABLE AgentLogs
(
    LogID INT IDENTITY PRIMARY KEY,
    AgentID INT FOREIGN KEY REFERENCES Agents(AgentID),
    QueryContent NVARCHAR(MAX),
    ResponseContent NVARCHAR(MAX),
    -- JSON columns are used to store hierarchical data from the thought process.
    ThoughtTree NVARCHAR(MAX)
    AS JSON,
        BDIState NVARCHAR
    (MAX) AS JSON,
        Evaluation NVARCHAR
    (MAX) AS JSON,
        RetrievedChunks NVARCHAR
    (MAX) AS JSON,
        CreatedAt DATETIME DEFAULT GETDATE
    ()
    );
GO
    -- The ChangeLog table acts as a transactional outbox for CDC.
    -- Specialized systems (Milvus, Neo4j) will consume events from this table.
    CREATE TABLE ChangeLog
    (
        ChangeID INT IDENTITY PRIMARY KEY,
        SourceTable NVARCHAR(50),
        -- e.g., 'Agents', 'AgentLogs', 'Chunks'
        SourceID NVARCHAR(100),
        -- The unique ID of the changed record
        ChangeType NVARCHAR(10),
        -- e.g., 'INSERT', 'UPDATE', 'DELETE'
        Payload JSON,
        -- A JSON representation of the changed data
        CreatedAt DATETIME DEFAULT GETDATE()
    );
GO
    -- FILE: procedures.sql
    -- This file contains the stored procedure for the agentic process.
    -- Stored procedure to generate embeddings and log the agent's actions.
    CREATE
    OR ALTER PROCEDURE dbo.IngestAndProcessQuery
        @AgentName NVARCHAR(255),
        @QueryContent NVARCHAR(MAX)
    AS
    BEGIN
        SET NOCOUNT ON;
        DECLARE @AgentID INT;
        DECLARE @QueryVector VECTOR(1536);
        DECLARE @LogID INT;
        DECLARE @Payload JSON;
        -- Step 1: Find the agent and create a log entry.
        SELECT @AgentID = AgentID
        FROM Agents
        WHERE Name = @AgentName;
        INSERT INTO AgentLogs
            (AgentID, QueryContent)
        VALUES
            (@AgentID, @QueryContent);
        SET @LogID = SCOPE_IDENTITY();
        -- Step 2: Simulate AI_GENERATE_EMBEDDINGS.
        -- In a real scenario, this would call an external model via a registered endpoint.
        SET @QueryVector = (
        SELECT AI_GENERATE_EMBEDDINGS(
                @QueryContent
        USE MODEL
        MyOllamaModel
            )
    );
        -- Step 3: Perform a semantic search on the Chunks table.
        -- This shows native vector search using SQL Server's DiskANN index.
        SELECT TOP 10
            c.ChunkID,
            c.Text,
            c.DocumentID
        FROM Chunks c
        ORDER BY VECTOR_DISTANCE(@QueryVector, c.Embedding, 'COSINE') ASC;
        -- Step 4: Log the agent's action and a change event.
        -- This triggers the CDC pipeline for the external systems to consume.
        SELECT @Payload = (
        SELECT @AgentID AS AgentID,
                @LogID AS LogID,
                @QueryContent AS QueryContent
            FOR JSON PATH,
            WITHOUT_ARRAY_WRAPPER
    );
        INSERT INTO ChangeLog
            (SourceTable, SourceID, ChangeType, Payload)
        VALUES
            (
                'AgentLogs',
                CAST(@LogID AS NVARCHAR(100)),
                'INSERT',
                @Payload
    );
    END
GO
    -- FILE: sample-data.sql
    -- This file contains sample data to get you started with the schema.
    -- Insert a sample agent
    INSERT INTO Agents
        (Name, Role, Status)
    VALUES
        ('Analyst_Alpha', 'Data Analyst', 'active');
GO
    -- Insert a sample document and a chunk from it
    DECLARE @documentID UNIQUEIDENTIFIER = NEWID();
    INSERT INTO Documents
        (DocumentID, Title, SourceURL, DocumentContent)
    VALUES
        (
            @documentID,
            'SQL Server 2025 Features',
            'https://learn.microsoft.com',
            0x01
    );
GO
    -- Now, insert a chunk from the document with a dummy vector
    DECLARE @dummyVector VECTOR(1536);
    -- This is a placeholder for a real vector, which would be generated by an
    -- external model.
    SET @dummyVector = (
        SELECT AI_GENERATE_EMBEDDINGS(
                'SQL Server 2025 includes native vector support with DiskANN indexing.'
    USE MODEL
    MyOllamaModel
            )
    );
    INSERT INTO Chunks
        (
        DocumentID,
        Text,
        Embedding,
        ModelName,
        ModelVersion
        )
    VALUES
        (
            @documentID,
            'SQL Server 2025 includes native vector support with DiskANN indexing.',
            @dummyVector,
            'MyOllamaModel',
            '1.0'
    );
GO