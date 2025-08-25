import os

import pyodbc

try:
    server = os.getenv("SQLSERVER_LINUX_SERVER")
    database = os.getenv("SQLSERVER_LINUX_DATABASE")
    username = os.getenv("SQLSERVER_LINUX_USER")
    password = os.getenv("SQLSERVER_LINUX_PASSWORD")
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password}"
    )
    conn = pyodbc.connect(conn_str)
    print(
        "SQL Server (Linux) connection successful:",
        conn.getinfo(pyodbc.SQL_SERVER_NAME),
    )
except Exception as e:
    print("SQL Server (Linux) connection failed:", e)
