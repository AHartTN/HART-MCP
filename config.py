"""
Configuration file for database connections and other settings.
Environment variables are loaded from a .env file.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- SQL Server Configuration ---

# --- SQL Server Configuration ---
# Read all possible SQL Server variables from .env
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER")
SQL_SERVER_SERVER = os.getenv("SQL_SERVER_SERVER")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE")
SQL_SERVER_USERNAME = os.getenv("SQL_SERVER_USERNAME")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD")
SQL_SERVER_UID = os.getenv("SQL_SERVER_UID")
SQL_SERVER_PWD = os.getenv("SQL_SERVER_PWD")

# Prioritize UID/PWD for the connection, falling back to USERNAME/PASSWORD
SQL_SERVER_UID = os.getenv("SQL_SERVER_UID") or os.getenv("SQL_SERVER_USERNAME")
SQL_SERVER_PWD = os.getenv("SQL_SERVER_PWD") or os.getenv("SQL_SERVER_PASSWORD")

# Construct the connection string that db_connectors.py expects
# The driver in .env can have braces, so we strip them to avoid doubling them in the f-string.
SQL_SERVER_CONNECTION_STRING = (
    f"DRIVER={{{SQL_SERVER_DRIVER.strip('{}')}}};"
    f"SERVER={SQL_SERVER_SERVER};"
    f"DATABASE={SQL_SERVER_DATABASE};"
    f"UID={SQL_SERVER_UID};"
    f"PWD={SQL_SERVER_PWD};"
    "TrustServerCertificate=yes;"
)

# --- Milvus Configuration ---
# Read all possible Milvus variables from .env
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_USER = os.getenv("MILVUS_UID") or os.getenv("MILVUS_USER")
MILVUS_PASSWORD = os.getenv("MILVUS_PWD") or os.getenv("MILVUS_PASSWORD")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION")

# --- Neo4j Configuration ---
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# --- LLM Configuration ---
LLM_SOURCE = os.getenv("LLM_SOURCE", "gemini")

# Gemini Specific
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-pro")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))

# Claude Specific
CLAUDE_MODEL_NAME = os.getenv("CLAUDE_MODEL_NAME", "claude-3-opus-20240229")
CLAUDE_TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "2048"))

# Llama (Hugging Face Inference API) Specific
LLAMA_MODEL_NAME = os.getenv("LLAMA_MODEL_NAME", "meta-llama/Llama-2-7b-chat-hf") # Example model
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
LLAMA_TEMPERATURE = float(os.getenv("LLAMA_TEMPERATURE", "0.7"))
LLAMA_MAX_TOKENS = int(os.getenv("LLAMA_MAX_TOKENS", "2048"))

# Ollama Specific
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama2") # Default Ollama model
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))
