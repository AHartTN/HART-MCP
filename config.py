"""
Configuration file for database connections and other settings.
Environment variables are loaded from a .env file with validation.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration with validation."""
    host: str
    port: int
    user: str
    password: str
    database: str
    
    def __post_init__(self):
        if not all([self.host, self.user, self.password]):
            raise ValueError("Database configuration incomplete")
            
@dataclass 
class LLMConfig:
    """LLM configuration with validation."""
    model_name: str
    temperature: float
    max_tokens: int
    api_key: Optional[str] = None
    
    def __post_init__(self):
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if not (1 <= self.max_tokens <= 32768):
            raise ValueError("Max tokens must be between 1 and 32768")
            
def validate_config() -> Dict[str, Any]:
    """Validate all configuration settings on startup."""
    errors = []
    warnings = []
    
    # Required environment variables
    required_vars = {
        'SQL_SERVER_DRIVER': SQL_SERVER_DRIVER,
        'SQL_SERVER_SERVER': SQL_SERVER_SERVER,
        'SQL_SERVER_DATABASE': SQL_SERVER_DATABASE,
        'NEO4J_URI': NEO4J_URI,
        'MILVUS_HOST': MILVUS_HOST,
    }
    
    for var_name, var_value in required_vars.items():
        if not var_value:
            errors.append(f"Missing required environment variable: {var_name}")
    
    # Validate LLM configurations
    try:
        gemini_config = LLMConfig(
            model_name=GEMINI_MODEL_NAME,
            temperature=GEMINI_TEMPERATURE,
            max_tokens=GEMINI_MAX_TOKENS,
            api_key=os.getenv('GEMINI_API_KEY')
        )
    except ValueError as e:
        errors.append(f"Gemini configuration error: {e}")
        
    # Check API keys
    api_keys = {
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'HUGGINGFACE_API_TOKEN': HUGGINGFACE_API_TOKEN,
    }
    
    for key_name, key_value in api_keys.items():
        if not key_value:
            warnings.append(f"Missing API key: {key_name} (fallback may be limited)")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }

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
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash-exp")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))

# Claude Specific
CLAUDE_MODEL_NAME = os.getenv("CLAUDE_MODEL_NAME", "claude-3-opus-20240229")
CLAUDE_TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "2048"))

# Llama (Hugging Face Inference API) Specific
LLAMA_MODEL_NAME = os.getenv(
    "LLAMA_MODEL_NAME", "meta-llama/Llama-2-7b-chat-hf"
)  # Example model
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
LLAMA_TEMPERATURE = float(os.getenv("LLAMA_TEMPERATURE", "0.7"))
LLAMA_MAX_TOKENS = int(os.getenv("LLAMA_MAX_TOKENS", "2048"))

# Ollama Specific
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3:8b")  # Default Ollama model
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))

# LLM Fallback Configuration
LLM_FALLBACK_ENABLED = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"
LLM_FALLBACK_ORDER = os.getenv("LLM_FALLBACK_ORDER", "gemini,ollama,claude,llama").split(",")

# Additional Local Models Configuration
OLLAMA_MODELS = {
    # Llama 3 Series
    "llama3:8b": {"context_length": 8192, "description": "Llama 3 8B - Fast and efficient", "category": "general"},
    "llama3:70b": {"context_length": 8192, "description": "Llama 3 70B - High quality", "category": "general"},
    
    # Qwen 2.5 Series (General)
    "qwen2.5:7b": {"context_length": 32768, "description": "Qwen 2.5 7B - Large context", "category": "general"},
    "qwen2.5:14b": {"context_length": 32768, "description": "Qwen 2.5 14B - Balanced", "category": "general"},
    "qwen2.5:32b": {"context_length": 32768, "description": "Qwen 2.5 32B - High quality", "category": "general"},
    
    # Qwen Coder Series (Code-specialized)
    "qwen2.5-coder:1.5b": {"context_length": 32768, "description": "Qwen 2.5 Coder 1.5B - Fast coding", "category": "coding"},
    "qwen2.5-coder:7b": {"context_length": 32768, "description": "Qwen 2.5 Coder 7B - Balanced coding", "category": "coding"},
    "qwen2.5-coder:14b": {"context_length": 32768, "description": "Qwen 2.5 Coder 14B - Advanced coding", "category": "coding"},
    "qwen2.5-coder:32b": {"context_length": 32768, "description": "Qwen 2.5 Coder 32B - Expert coding", "category": "coding"},
    
    # Code-focused models
    "codellama:7b": {"context_length": 16384, "description": "Code Llama 7B - Code focused", "category": "coding"},
    "codellama:13b": {"context_length": 16384, "description": "Code Llama 13B - Better coding", "category": "coding"},
    "codellama:34b": {"context_length": 16384, "description": "Code Llama 34B - Expert coding", "category": "coding"},
    
    # Other popular models
    "mistral:7b": {"context_length": 8192, "description": "Mistral 7B - Fast inference", "category": "general"},
    "phi3:3.8b": {"context_length": 4096, "description": "Phi-3 3.8B - Compact model", "category": "general"},
    "gemma2:9b": {"context_length": 8192, "description": "Gemma 2 9B - Google's model", "category": "general"},
    "deepseek-coder:6.7b": {"context_length": 16384, "description": "DeepSeek Coder 6.7B - Code expert", "category": "coding"},
}

# Performance and production settings
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))  # 5 minutes
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))

# Feature flags
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
ENABLE_TRACING = os.getenv("ENABLE_TRACING", "false").lower() == "true"

# Redis configuration for caching
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "10"))

# Validate configuration on import
try:
    config_validation = validate_config()
    if not config_validation['valid']:
        logger.error(f"Configuration validation failed: {config_validation['errors']}")
        raise ValueError("Invalid configuration. Check environment variables.")

    if config_validation['warnings']:
        for warning in config_validation['warnings']:
            logger.warning(warning)
except NameError:
    # Handle case where validation function uses variables not yet defined
    pass
