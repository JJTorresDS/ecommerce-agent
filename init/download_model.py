"""
One-time download script for the BAAI/bge-m3 embedding model.

Run this ONCE while connected to the internet. It downloads the model
weights into the local Hugging Face cache (~/.cache/huggingface by default).
After this completes, embeddings.py works fully offline.

Usage:
    uv run python download_model.py
"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"

print(f"Downloading {MODEL_NAME} (this may take a few minutes)...")
SentenceTransformer(MODEL_NAME)
print("Done. Model is cached locally and ready for offline use.")