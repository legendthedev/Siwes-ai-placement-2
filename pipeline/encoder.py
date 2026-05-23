"""
pipeline/encoder.py  —  Sentence-BERT semantic encoding
Converts a list of skills (or raw text) into a dense embedding vector.
Model: all-MiniLM-L6-v2  (384-dim, fast, strong semantic quality)
"""

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


class SBERTEncoder:
    """
    Wraps SentenceTransformer for SIWES placement.
    Encodes skill lists or raw strings into 384-dim float32 vectors.
    """

    def __init__(self, model_name: str = MODEL_NAME):
        print(f"[SBERT] Loading model '{model_name}' ...")
        self.model = SentenceTransformer(model_name)
        print("[SBERT] Model ready.")

    def encode_skills(self, skills: list[str]) -> np.ndarray:
        """
        Join the skills list into a single descriptive sentence and encode it.
        e.g. ["python", "django", "postgresql"] →
             "Skills: python, django, postgresql"
        """
        if not skills:
            # Return a zero vector of the correct dimension
            return np.zeros(self.model.get_sentence_embedding_dimension(), dtype=np.float32)

        text = "Skills: " + ", ".join(skills)
        return self._encode(text)

    def encode_text(self, text: str) -> np.ndarray:
        """Encode a raw text string directly."""
        return self._encode(text)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """Encode multiple texts at once (more efficient for large batches)."""
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    def _encode(self, text: str) -> np.ndarray:
        vec = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return vec.astype(np.float32)


# ── Module-level singleton ────────────────────
_encoder: SBERTEncoder | None = None

def get_encoder() -> SBERTEncoder:
    global _encoder
    if _encoder is None:
        _encoder = SBERTEncoder()
    return _encoder
