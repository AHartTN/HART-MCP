import pyodbc
import json

try:
    # Connection string for LocalDB
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=(localdb)\\mssqllocaldb;"
        "DATABASE=HART_MCP_Dev;"
        "Trusted_Connection=yes;"
    )
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        
        print("Checking HART-MCP Database Status...")
        
        # Check if tables exist and their row counts
        tables = ['Agents', 'Documents', 'DocumentChunks', 'AgentExecutions']
        results = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                count = cursor.fetchone()[0]
                results[table] = count
                print(f"{table}: {count} rows")
            except Exception as e:
                results[table] = f"Error: {e}"
                print(f"{table}: Error - {e}")
        
        # Get sample data from Agents table
        try:
            cursor.execute("SELECT TOP 5 Name, Type, Status FROM Agents")
            agents = []
            for row in cursor.fetchall():
                agents.append({
                    'Name': row[0],
                    'Type': row[1], 
                    'Status': row[2]
                })
            print(f"\nSample Agents:")
            for agent in agents:
                print(f"  - {agent['Name']} (Type: {agent['Type']}, Status: {agent['Status']})")
        except Exception as e:
            print(f"Error getting agents: {e}")
            
        # Get sample data from Documents table  
        try:
            cursor.execute("SELECT TOP 5 Title, Type, Status FROM Documents")
            docs = []
            for row in cursor.fetchall():
                docs.append({
                    'Title': row[0],
                    'Type': row[1],
                    'Status': row[2] 
                })
            print(f"\nSample Documents:")
            for doc in docs:
                print(f"  - {doc['Title']} (Type: {doc['Type']}, Status: {doc['Status']})")
        except Exception as e:
            print(f"Error getting documents: {e}")
        
        print(f"\nDatabase check completed!")
        print(f"Total records: {sum(v for v in results.values() if isinstance(v, int))}")
            
except Exception as e:
    print(f"Database connection failed: {e}")
    print("Make sure SQL Server LocalDB is running and the database exists.")