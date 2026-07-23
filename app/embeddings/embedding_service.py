from sentence_transformers import SentenceTransformer

from app.config import settings
from app.config.logging import logger


class EmbeddingService:
    _model = None
    
    def __init__(self):
        if EmbeddingService._model is None:
            logger.info(f"[embeddings] loading model{settings.EMBEDDING_MODEL_NAME}")
            EmbeddingService._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        
        self.model = EmbeddingService._model
        
    def generate(self, text:str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * settings.EMBEDDINGS_DIMENSIONS
        
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    