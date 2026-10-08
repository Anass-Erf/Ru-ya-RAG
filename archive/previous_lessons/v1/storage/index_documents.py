
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

LESSON_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = LESSON_ROOT / "data" / "documents.json"
STORAGE_PATH = LESSON_ROOT / "storage"

STORAGE_PATH.mkdir(exist_ok=True)

# Load documents
with open(DATA_PATH, "r", encoding="utf-8") as f:
    documents = json.load(f)

texts = [doc["text"] for doc in documents]

# Load embedding model
model = SentenceTransformer(MODEL_NAME)

# Encode corpus
vectors = model.encode(
    texts,
    normalize_embeddings=True,
    convert_to_numpy=True
)

# Store vectors
np.save(STORAGE_PATH / "vectors.npy", vectors)

# Store document metadata
with open(
    STORAGE_PATH / "documents.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        documents,
        f,
        ensure_ascii=False,
        indent=2
    )

# Save model identity
(STORAGE_PATH / "model.txt").write_text(
    MODEL_NAME,
    encoding="utf-8"
)

print("Indexing completed!")
print("Number of documents:", len(documents))
print("Vector matrix shape:", vectors.shape)
