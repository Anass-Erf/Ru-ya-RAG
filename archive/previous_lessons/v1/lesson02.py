
import numpy as np
from sentence_transformers import SentenceTransformer

# 1. Our corpus
# These are artificial examples, not religious quotations.
documents = [
    "رؤية الماء الصافي في المنام",
    "رؤية الأسد في المنام",
    "رؤية المطر الغزير في المنام",
    "رؤية السفر في طريق طويل",
    "رؤية البحر والأمواج في المنام",
]

# 2. Load pretrained model
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# 3. Encode all documents (indexing)
document_vectors = model.encode(
    documents,
    normalize_embeddings=True
)

print("Document vectors:", document_vectors.shape)

# 4. User query
query = "حلمت بمياه نقية"

# 5. Encode the query
query_vector = model.encode(
    [query],
    normalize_embeddings=True
)

print("Query vector:", query_vector.shape)

# 6. Calculate similarity
# Normalized vectors: dot product = cosine similarity
scores = query_vector @ document_vectors.T

# 7. Rank documents
ranking = np.argsort(scores[0])[::-1]

print("\nQuery:", query)

for index in ranking:
    print(f"\nSimilarity: {scores[0][index]:.4f}")
    print(f"Document: {documents[index]}")
