// FILE: neo4j-setup.cypher
// This file sets up the graph schema by creating constraints on the nodes.

// Use the 'neo4j' database.
USE neo4j;

// Create uniqueness constraints for the core node types.
CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (l:AgentLog) REQUIRE l.id IS UNIQUE;

// FILE: neo4j-import.cypher
// This file contains a simplified example of how to import data from
// your SQL Server tables into Neo4j.

// Use the 'neo4j' database.
USE neo4j;

// Step 1: Import Agents
LOAD CSV WITH HEADERS FROM 'file:///agents.csv' AS row
MERGE (a:Agent {id: toInteger(row.AgentID)})
ON CREATE SET a.name = row.Name, a.role = row.Role;

// Step 2: Import Documents
LOAD CSV WITH HEADERS FROM 'file:///documents.csv' AS row
MERGE (d:Document {id: row.DocumentID})
ON CREATE SET d.title = row.Title, d.sourceUrl = row.SourceURL;

// Step 3: Import Chunks and link them to Documents
LOAD CSV WITH HEADERS FROM 'file:///chunks.csv' AS row
MERGE (c:Chunk {id: row.ChunkID})
ON CREATE SET c.text = row.Text
MERGE (d:Document {id: row.DocumentID})
MERGE (c)-[:CHUNK_OF]->(d);

// Step 4: Import AgentLogs and create relationships to Agents
LOAD CSV WITH HEADERS FROM 'file:///agent_logs.csv' AS row
MERGE (l:AgentLog {id: toInteger(row.LogID)})
ON CREATE SET l.queryContent = row.QueryContent, l.responseContent = row.ResponseContent
MERGE (a:Agent {id: toInteger(row.AgentID)})
MERGE (a)-[:EXECUTED]->(l);