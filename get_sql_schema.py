import pyodbc
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- SQL Server Configuration from config.py logic ---
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER")
SQL_SERVER_SERVER = os.getenv("SQL_SERVER_SERVER")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE")
SQL_SERVER_UID = os.getenv("SQL_SERVER_UID") or os.getenv("SQL_SERVER_USERNAME")
SQL_SERVER_PWD = os.getenv("SQL_SERVER_PWD") or os.getenv("SQL_SERVER_PASSWORD")

SQL_SERVER_CONNECTION_STRING = (
    f"DRIVER={{{SQL_SERVER_DRIVER.strip('{}')}}};"
    f"SERVER={SQL_SERVER_SERVER};"
    f"DATABASE={SQL_SERVER_DATABASE};"
    f"UID={SQL_SERVER_UID};"
    f"PWD={SQL_SERVER_PWD};"
    "TrustServerCertificate=yes;"
)


def get_schema():
    schema_info = {}
    try:
        with pyodbc.connect(SQL_SERVER_CONNECTION_STRING) as cnxn:
            cursor = cnxn.cursor()

            # Get table names
            cursor.execute(
                "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
            )
            tables = cursor.fetchall()

            for table_schema, table_name in tables:
                schema_info[f"{table_schema}.{table_name}"] = []
                # Get column details for each table
                cursor.execute(
                    f"SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{table_schema}' AND TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION"
                )
                columns = cursor.fetchall()
                for col_name, data_type, max_length, is_nullable in columns:
                    schema_info[f"{table_schema}.{table_name}"].append(
                        {
                            "column_name": col_name,
                            "data_type": data_type,
                            "character_maximum_length": max_length,
                            "is_nullable": is_nullable,
                        }
                    )
    except Exception as e:
        schema_info = {
            "error": str(e),
            "connection_string": SQL_SERVER_CONNECTION_STRING,
        }
    return schema_info


if __name__ == "__main__":
    schema = get_schema()
    print(json.dumps(schema, indent=2))
