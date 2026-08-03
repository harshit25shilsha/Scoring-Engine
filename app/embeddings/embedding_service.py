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
    
    def generate_batch(self, texts: list[str])-> list[list[float]]:
        if not texts:
            return[]
        # Replace empty/blank entries with a placeholder so batch allignment stays correct;
        # zero-vector result gets substituted back in afterward.
        
        safe_texts = [t if t and t.strip() else " " for t in texts]
        
        vectors = self.model.encode(safe_texts, normalize_embeddings= True, batch_size=32)
        
        results =[]
        for original_text, vector in zip(texts, vectors):
            if not original_text or not original_text.strip():
                results.append([0.0] * settings.EMBEDDINGS_DIMENSIONS)
            else:
                results.append(vector.tolist())
        
        return results
    