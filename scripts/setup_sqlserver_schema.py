import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import logging
import re

from dotenv import load_dotenv

from db_connectors import get_sql_server_connection

# Configure logging
logging.basicConfig(level=logging.INFO)


def ensure_table(conn, table_name, create_sql):
    async def inner():
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
                table_name,
            )
            exists = (await cursor.fetchone())[0] > 0
            if not exists:
                await cursor.execute(create_sql)
                await conn.commit()
                logging.info("Created table: %s", table_name)
            else:
                logging.info("Table already exists: %s", table_name)

    return asyncio.run(inner())


def main():
    load_dotenv()  # Load environment variables from .env file

    async def inner():
        conn = await get_sql_server_connection()
        if not conn:
            logging.error("Failed to get SQL Server connection. Exiting.")
            return

        # Execute each CREATE TABLE statement from migrations/sqlserver.sql
        # The GO statements are removed as pyodbc executes one statement at a time.

        create_statements = [
            """
        CREATE TABLE Agents
        (
            AgentID INT IDENTITY PRIMARY KEY,
            Name NVARCHAR(255) NOT NULL UNIQUE,
            Role NVARCHAR(100),
            Status NVARCHAR(50)
        )
        """,
            """
        CREATE TABLE Documents
        (
            DocumentID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
            Title NVARCHAR(MAX),
            SourceURL NVARCHAR(MAX),
            DocumentContent VARBINARY(MAX) NOT NULL,
            CreatedAt DATETIME DEFAULT GETDATE()
        )
        """,
            """
        CREATE TABLE Chunks
        (
            ChunkID UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
            DocumentID UNIQUEIDENTIFIER FOREIGN KEY REFERENCES Documents(DocumentID),
            Text NVARCHAR(MAX),
            Embedding VARBINARY(MAX), -- Using VARBINARY(MAX) as VECTOR type might not be universally supported by pyodbc
            ModelName NVARCHAR(100),
            ModelVersion NVARCHAR(50),
            CreatedAt DATETIME DEFAULT GETDATE()
        )
        """,
            """
        CREATE TABLE AgentLogs
        (
            LogID INT IDENTITY PRIMARY KEY,
            AgentID INT FOREIGN KEY REFERENCES Agents(AgentID),
            QueryContent NVARCHAR(MAX),
            ResponseContent NVARCHAR(MAX),
            ThoughtTree NVARCHAR(MAX),
            BDIState NVARCHAR(MAX),
            Evaluation NVARCHAR(MAX),
            RetrievedChunks NVARCHAR(MAX),
            CreatedAt DATETIME DEFAULT GETDATE()
        )
        """,
            """
        CREATE TABLE ChangeLog
        (
            ChangeID INT IDENTITY PRIMARY KEY,
            SourceTable NVARCHAR(50),
            SourceID NVARCHAR(100),
            ChangeType NVARCHAR(10),
            Payload NVARCHAR(MAX),
            CreatedAt DATETIME DEFAULT GETDATE()
        )
        """,
        ]

        async with conn.cursor() as cursor:
            for statement in create_statements:
                table_name = "UnknownTable"
                try:
                    table_name_match = re.search(
                        r"CREATE TABLE (\w+)", statement, re.IGNORECASE
                    )
                    if table_name_match:
                        table_name = table_name_match.group(1)

                    await cursor.execute(
                        f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}'"
                    )
                    exists = (await cursor.fetchone())[0] > 0
                    if not exists:
                        await cursor.execute(statement)
                        await conn.commit()
                        logging.info("Created table: %s", table_name)
                    else:
                        logging.info("Table already exists: %s", table_name)
                except Exception as e:
                    logging.error(
                        f"Error executing SQL statement for table {table_name}: {e}"
                    )
                    await conn.rollback()
                    raise

        await conn.close()
        logging.info("SQL Server schema setup complete.")

    asyncio.run(inner())


if __name__ == "__main__":
    main()
