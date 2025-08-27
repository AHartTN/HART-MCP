import asyncio
import logging

from dotenv import load_dotenv

from utils import sql_connection_context

logging.basicConfig(level=logging.INFO)

CREATE_AGENTLOGS_TABLE = """
    CREATE TABLE AgentLogs (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        AgentId NVARCHAR(255),
        MissionId NVARCHAR(255),
        Timestamp DATETIME2,
        LogType NVARCHAR(255),
        LogData NVARCHAR(MAX)
    )
    """

NVARCHAR_MAX = "NVARCHAR(MAX)"

AGENTLOGS_COLUMNS = {
    "BDIState": NVARCHAR_MAX,
    "ThoughtTree": NVARCHAR_MAX,
    "Evaluation": NVARCHAR_MAX,
    "RetrievedChunks": NVARCHAR_MAX,
}


async def main():
    load_dotenv()
    async with sql_connection_context() as (conn, cursor):
        # Create AgentLogs table if not exists
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_NAME = 'AgentLogs'"
        )
        result = cursor.fetchone()
        exists = result and result[0] > 0
        if not exists:
            try:
                cursor.execute(CREATE_AGENTLOGS_TABLE)
                conn.commit()
                logging.info("Created table: AgentLogs")
            except Exception as e:
                logging.error("Error creating AgentLogs table: %s", e)
                conn.rollback()
                raise
        else:
            logging.info("Table already exists: AgentLogs")

        # Ensure AgentLogs columns exist
        for col, coltype in AGENTLOGS_COLUMNS.items():
            cursor.execute(
                f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                f"WHERE TABLE_NAME = 'AgentLogs' AND COLUMN_NAME = '{col}'"
            )
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(
                    f"ALTER TABLE AgentLogs ADD {col} {coltype} AS JSON NULL"
                )
                conn.commit()
                logging.info(
                    "Added column %s to AgentLogs with type %s AS JSON.",
                    col,
                    coltype,
                )

        logging.info("SQL Server schema setup complete.")


if __name__ == "__main__":
    asyncio.run(main())
