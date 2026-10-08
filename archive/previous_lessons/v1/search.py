
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

STORAGE_PATH = Path(__file__).resolve().parent / "storage"

# Load saved vectors
vectors = np.load(STORAGE_PATH / "vectors.npy")

# Load saved documents
with open(
    STORAGE_PATH / "documents.json",
    "r",
    encoding="utf-8"
) as f:
    documents = json.load(f)

# Load the same model used during indexing
model_name = (
    STORAGE_PATH / "model.txt"
).read_text(encoding="utf-8").strip()

model = SentenceTransformer(model_name)

assert len(documents) == len(vectors), (
    "Document/vector count mismatch. Rebuild the index."
)

def search(query: str, top_k: int = 3):
    if not query.strip():
        return []

    # Encode the query
    query_vector = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    # Cosine similarity via dot product
    scores = (query_vector @ vectors.T)[0]

    # Select the best matches
    ranking = np.argsort(scores)[::-1]
    ranking = ranking[:max(0, min(top_k, len(documents)))]

    results = []

    for index in ranking:
        doc = documents[int(index)]

        results.append({
            "id": doc["id"],
            "text": doc["text"],
            "topic": doc["topic"],
            "source": doc["source"],
            "score": float(scores[index])
        })

    return results


if __name__ == "__main__":
    query = input("اكتب رؤياك: ")

    results = search(query, top_k=3)

    for rank, result in enumerate(results, start=1):
        print(f"\nResult #{rank}")
        print("Text:", result["text"])
        print("Score:", round(result["score"], 4))
        print("Source:", result["source"])
