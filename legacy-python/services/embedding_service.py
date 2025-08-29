import asyncio
import logging
import traceback
from typing import List, Optional

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        try:
            self.embedding_model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            logging.info(
                "Embedding model 'sentence-transformers/all-MiniLM-L6-v2' loaded successfully."
            )
        except ImportError as e:
            logger.error(
                (
                    "Failed to import SentenceTransformer: %s\n%s",
                    e,
                    traceback.format_exc(),
                )
            )
            self.embedding_model = None
        except Exception as e:
            logger.error(
                "Failed to load embedding model: %s\n%s", e, traceback.format_exc()
            )
            self.embedding_model = None

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a given text."""
        if self.embedding_model:
            try:
                return (
                    await asyncio.to_thread(self.embedding_model.encode, text)
                ).tolist()
            except (RuntimeError, ValueError, TypeError) as e:
                logger.error(
                    (
                        "Failed to generate embedding: %s\n%s",
                        e,
                        traceback.format_exc(),
                    )
                )
                return None
        return None
