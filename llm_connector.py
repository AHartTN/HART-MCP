import os
import logging
from abc import ABC, abstractmethod
import google.generativeai as genai
import anthropic
from huggingface_hub import InferenceClient
import httpx  # For Ollama

from config import (
    LLM_SOURCE,
    GEMINI_MODEL_NAME,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_TOKENS,
    CLAUDE_MODEL_NAME,
    CLAUDE_TEMPERATURE,
    CLAUDE_MAX_TOKENS,
    LLAMA_MODEL_NAME,
    LLAMA_TEMPERATURE,
    LLAMA_MAX_TOKENS,
    HUGGINGFACE_API_TOKEN,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL_NAME,
    OLLAMA_TEMPERATURE,
    OLLAMA_MAX_TOKENS,
    LLM_FALLBACK_ENABLED,
    LLM_FALLBACK_ORDER,
    OLLAMA_MODELS,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def invoke(
        self, prompt: str, temperature: float = None, max_tokens: int = None
    ) -> str:
        pass


class GeminiClient(BaseLLMClient):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.api_key_missing = True
            logging.warning("GEMINI_API_KEY environment variable not set - client will fail gracefully")
            return
        self.api_key_missing = False
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logging.info(f"Gemini model '{GEMINI_MODEL_NAME}' initialized.")

    async def invoke(
        self, prompt: str, temperature: float = None, max_tokens: int = None
    ) -> str:
        if self.api_key_missing:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        temp = temperature if temperature is not None else GEMINI_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else GEMINI_MAX_TOKENS
        logging.info(
            f"Invoking Gemini with model '{GEMINI_MODEL_NAME}', temp={temp}, max_tokens={max_t}"
        )
        response = await self.model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temp, max_output_tokens=max_t
            ),
        )
        return response.text


class ClaudeClient(BaseLLMClient):
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            self.api_key_missing = True
            logging.warning("ANTHROPIC_API_KEY environment variable not set - client will fail gracefully")
            return
        self.api_key_missing = False
        self.client = anthropic.Anthropic(api_key=api_key)
        logging.info(f"Claude client initialized for model '{CLAUDE_MODEL_NAME}'.")

    async def invoke(
        self, prompt: str, temperature: float = None, max_tokens: int = None
    ) -> str:
        if self.api_key_missing:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        temp = temperature if temperature is not None else CLAUDE_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else CLAUDE_MAX_TOKENS
        logging.info(
            f"Invoking Claude with model '{CLAUDE_MODEL_NAME}', temp={temp}, max_tokens={max_t}"
        )
        message = await self.client.messages.create(
            model=CLAUDE_MODEL_NAME,
            max_tokens=max_t,
            temperature=temp,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class HuggingFaceClient(BaseLLMClient):
    def __init__(self):
        if not HUGGINGFACE_API_TOKEN:
            self.api_key_missing = True
            logging.warning("HUGGINGFACE_API_TOKEN environment variable not set - client will fail gracefully")
            return
        self.api_key_missing = False
        self.client = InferenceClient(
            model=LLAMA_MODEL_NAME, token=HUGGINGFACE_API_TOKEN
        )
        logging.info(
            f"Hugging Face Inference Client initialized for model '{LLAMA_MODEL_NAME}'."
        )

    async def invoke(
        self, prompt: str, temperature: float = None, max_tokens: int = None
    ) -> str:
        if self.api_key_missing:
            raise ValueError("HUGGINGFACE_API_TOKEN environment variable not set.")
        temp = temperature if temperature is not None else LLAMA_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else LLAMA_MAX_TOKENS
        logging.info(
            f"Invoking Llama (HF) with model '{LLAMA_MODEL_NAME}', temp={temp}, max_tokens={max_t}"
        )
        response = self.client.text_generation(
            prompt, max_new_tokens=max_t, temperature=temp
        )
        return response


class OllamaClient(BaseLLMClient):
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model_name = OLLAMA_MODEL_NAME
        self.client = httpx.AsyncClient(base_url=self.base_url)
        logging.info(
            f"Ollama client initialized for model '{self.model_name}' at {self.base_url}."
        )

    async def invoke(
        self, prompt: str, temperature: float = None, max_tokens: int = None
    ) -> str:
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else OLLAMA_MAX_TOKENS
        logging.info(
            f"Invoking Ollama with model '{self.model_name}', temp={temp}, max_tokens={max_t}"
        )
        try:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "options": {"temperature": temp, "num_predict": max_t},
                },
                timeout=None,  # Ollama can take a while for first run
            )
            response.raise_for_status()
            # Ollama streams responses, but for simplicity, we'll get the full response
            # For streaming, you'd iterate over response.iter_lines()
            return response.json()["response"]
        except httpx.RequestError as exc:
            logging.error(
                f"An error occurred while requesting {exc.request.url!r}: {exc}"
            )
            raise
        except httpx.HTTPStatusError as exc:
            logging.error(
                f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc}"
            )
            raise
        except Exception as e:
            logging.error(
                f"Unexpected error during Ollama invocation: {e}", exc_info=True
            )
            raise


class LLMClient:
    def __init__(self):
        self.llm_source = LLM_SOURCE
        self.primary_client: BaseLLMClient = None
        self.fallback_clients = {}
        self.failed_clients = set()  # Track temporarily failed clients
        
        logging.info(f"Initializing main LLMClient with source: {self.llm_source}")
        
        # Initialize primary client
        self.primary_client = self._create_client(self.llm_source)
        
        # Initialize fallback clients if enabled
        if LLM_FALLBACK_ENABLED:
            logging.info("Fallback enabled. Initializing fallback clients...")
            for source in LLM_FALLBACK_ORDER:
                if source != self.llm_source:
                    try:
                        client = self._create_client(source)
                        # Only add client if it was initialized properly (has no API key issues)
                        if not hasattr(client, 'api_key_missing') or not client.api_key_missing:
                            self.fallback_clients[source] = client
                            logging.info(f"Fallback client '{source}' initialized.")
                        else:
                            logging.info(f"Fallback client '{source}' skipped due to missing API key.")
                    except Exception as e:
                        logging.warning(f"Failed to initialize fallback client '{source}': {e}")

    def _create_client(self, source: str) -> BaseLLMClient:
        """Create a client for the given source."""
        if source == "gemini":
            return GeminiClient()
        elif source == "claude":
            return ClaudeClient()
        elif source == "llama":
            return HuggingFaceClient()
        elif source == "ollama":
            return OllamaClient()
        else:
            raise ValueError(f"Unsupported LLM source: {source}")

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error."""
        error_str = str(error).lower()
        rate_limit_indicators = [
            "rate limit",
            "quota",
            "429",
            "too many requests",
            "rate_limit_exceeded",
            "resource_exhausted",
        ]
        return any(indicator in error_str for indicator in rate_limit_indicators)

    def _is_api_key_error(self, error: Exception) -> bool:
        """Check if the error is an API key/authentication error."""
        error_str = str(error).lower()
        auth_indicators = [
            "api key",
            "unauthorized",
            "authentication",
            "401",
            "403",
            "invalid key",
        ]
        return any(indicator in error_str for indicator in auth_indicators)

    async def invoke(
        self, prompt: str, temperature: float = None, max_tokens: int = None
    ) -> str:
        """Invoke LLM with fallback support."""
        if self.primary_client is None:
            logging.error("Internal LLM client not initialized.")
            return "Error: Internal LLM client not initialized."

        # Try primary client first
        try:
            logging.info(f"Attempting primary client: {self.llm_source}")
            response = await self.primary_client.invoke(prompt, temperature, max_tokens)
            
            # Reset failed clients on successful call
            if self.llm_source in self.failed_clients:
                self.failed_clients.remove(self.llm_source)
                logging.info(f"Primary client {self.llm_source} recovered.")
                
            return response
            
        except Exception as primary_error:
            logging.error(f"Primary client ({self.llm_source}) failed: {primary_error}")
            
            # Check if we should try fallbacks
            if not LLM_FALLBACK_ENABLED:
                return f"Error invoking LLM: {primary_error}"
            
            # Mark primary as temporarily failed if it's a rate limit
            if self._is_rate_limit_error(primary_error):
                self.failed_clients.add(self.llm_source)
                logging.warning(f"Rate limit detected for {self.llm_source}, trying fallbacks...")
            elif self._is_api_key_error(primary_error):
                logging.warning(f"API key issue for {self.llm_source}, trying fallbacks...")
            else:
                logging.warning(f"Unknown error for {self.llm_source}, trying fallbacks...")

            # Try fallback clients
            for fallback_source in LLM_FALLBACK_ORDER:
                if fallback_source == self.llm_source:
                    continue  # Skip primary
                    
                if fallback_source in self.failed_clients:
                    logging.info(f"Skipping temporarily failed client: {fallback_source}")
                    continue
                    
                if fallback_source not in self.fallback_clients:
                    logging.warning(f"Fallback client {fallback_source} not available")
                    continue

                try:
                    logging.info(f"Trying fallback client: {fallback_source}")
                    response = await self.fallback_clients[fallback_source].invoke(
                        prompt, temperature, max_tokens
                    )
                    logging.info(f"✅ Fallback client {fallback_source} succeeded!")
                    
                    # Reset failed status for this client
                    if fallback_source in self.failed_clients:
                        self.failed_clients.remove(fallback_source)
                        
                    return response
                    
                except Exception as fallback_error:
                    logging.error(f"Fallback client {fallback_source} failed: {fallback_error}")
                    
                    # Mark fallback as failed if rate limit
                    if self._is_rate_limit_error(fallback_error):
                        self.failed_clients.add(fallback_source)

            # All clients failed
            logging.error("All LLM clients failed!")
            return f"Error: All LLM clients failed. Primary error: {primary_error}"

    def get_available_models(self) -> dict:
        """Get information about available models."""
        models = {}
        
        # Add configured models
        models["gemini"] = {"model": GEMINI_MODEL_NAME, "type": "cloud", "status": "gemini" not in self.failed_clients}
        models["claude"] = {"model": CLAUDE_MODEL_NAME, "type": "cloud", "status": "claude" not in self.failed_clients}
        models["llama"] = {"model": LLAMA_MODEL_NAME, "type": "cloud", "status": "llama" not in self.failed_clients}
        
        # Add Ollama models
        models["ollama"] = {
            "model": OLLAMA_MODEL_NAME,
            "type": "local",
            "status": "ollama" not in self.failed_clients,
            "available_models": OLLAMA_MODELS
        }
        
        return models

    def reset_failed_clients(self):
        """Reset the failed clients list (useful for recovery)."""
        self.failed_clients.clear()
        logging.info("Reset all failed client statuses.")
