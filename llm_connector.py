import os
import logging
from abc import ABC, abstractmethod
import google.generativeai as genai
import anthropic
from huggingface_hub import InferenceClient
import httpx # For Ollama

from config import (
    LLM_SOURCE,
    GEMINI_MODEL_NAME, GEMINI_TEMPERATURE, GEMINI_MAX_TOKENS,
    CLAUDE_MODEL_NAME, CLAUDE_TEMPERATURE, CLAUDE_MAX_TOKENS,
    LLAMA_MODEL_NAME, LLAMA_TEMPERATURE, LLAMA_MAX_TOKENS, HUGGINGFACE_API_TOKEN,
    OLLAMA_BASE_URL, OLLAMA_MODEL_NAME, OLLAMA_TEMPERATURE, OLLAMA_MAX_TOKENS
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    @abstractmethod
    async def invoke(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        pass

class GeminiClient(BaseLLMClient):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logging.info(f"Gemini model '{GEMINI_MODEL_NAME}' initialized.")

    async def invoke(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        temp = temperature if temperature is not None else GEMINI_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else GEMINI_MAX_TOKENS
        logging.info(f"Invoking Gemini with model '{GEMINI_MODEL_NAME}', temp={temp}, max_tokens={max_t}")
        response = await self.model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temp,
                max_output_tokens=max_t
            )
        )
        return response.text

class ClaudeClient(BaseLLMClient):
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        self.client = anthropic.Anthropic(api_key=api_key)
        logging.info(f"Claude client initialized for model '{CLAUDE_MODEL_NAME}'.")

    async def invoke(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        temp = temperature if temperature is not None else CLAUDE_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else CLAUDE_MAX_TOKENS
        logging.info(f"Invoking Claude with model '{CLAUDE_MODEL_NAME}', temp={temp}, max_tokens={max_t}")
        message = await self.client.messages.create(
            model=CLAUDE_MODEL_NAME,
            max_tokens=max_t,
            temperature=temp,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text

class HuggingFaceClient(BaseLLMClient):
    def __init__(self):
        if not HUGGINGFACE_API_TOKEN:
            raise ValueError("HUGGINGFACE_API_TOKEN environment variable not set for Llama.")
        self.client = InferenceClient(model=LLAMA_MODEL_NAME, token=HUGGINGFACE_API_TOKEN)
        logging.info(f"Hugging Face Inference Client initialized for model '{LLAMA_MODEL_NAME}'.")

    async def invoke(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        temp = temperature if temperature is not None else LLAMA_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else LLAMA_MAX_TOKENS
        logging.info(f"Invoking Llama (HF) with model '{LLAMA_MODEL_NAME}', temp={temp}, max_tokens={max_t}")
        response = self.client.text_generation(
            prompt,
            max_new_tokens=max_t,
            temperature=temp
        )
        return response

class OllamaClient(BaseLLMClient):
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model_name = OLLAMA_MODEL_NAME
        self.client = httpx.AsyncClient(base_url=self.base_url)
        logging.info(f"Ollama client initialized for model '{self.model_name}' at {self.base_url}.")

    async def invoke(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE
        max_t = max_tokens if max_tokens is not None else OLLAMA_MAX_TOKENS
        logging.info(f"Invoking Ollama with model '{self.model_name}', temp={temp}, max_tokens={max_t}")
        try:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "options": {
                        "temperature": temp,
                        "num_predict": max_t
                    }
                },
                timeout=None # Ollama can take a while for first run
            )
            response.raise_for_status()
            # Ollama streams responses, but for simplicity, we'll get the full response
            # For streaming, you'd iterate over response.iter_lines()
            return response.json()["response"]
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting {exc.request.url!r}: {exc}")
            raise
        except httpx.HTTPStatusError as exc:
            logging.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during Ollama invocation: {e}", exc_info=True)
            raise

class LLMClient:
    def __init__(self):
        self.llm_source = LLM_SOURCE
        self.client: BaseLLMClient = None
        logging.info(f"Initializing main LLMClient with source: {self.llm_source}")

        if self.llm_source == "gemini":
            self.client = GeminiClient()
        elif self.llm_source == "claude":
            self.client = ClaudeClient()
        elif self.llm_source == "llama":
            self.client = HuggingFaceClient()
        elif self.llm_source == "ollama":
            self.client = OllamaClient()
        else:
            raise ValueError(f"Unsupported LLM_SOURCE: {self.llm_source}")

    async def invoke(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        if self.client is None:
            logging.error("Internal LLM client not initialized.")
            return "Error: Internal LLM client not initialized."
        try:
            return await self.client.invoke(prompt, temperature, max_tokens)
        except Exception as e:
            logging.error(f"Error invoking LLM via main client ({self.llm_source}): {e}", exc_info=True)
            return f"Error invoking LLM: {e}"
