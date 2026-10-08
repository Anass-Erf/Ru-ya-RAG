
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

documents = [
    "رؤية الماء الصافي في المنام",
    "رؤية الأسد في المنام",
    "رؤية المطر الغزير في المنام",
    "رؤية السفر في طريق طويل",
    "رؤية البحر والأمواج في المنام",
]

query = "حلمت بمياه نقية"

# Approach 1: TF-IDF
tfidf = TfidfVectorizer()
tfidf_docs = tfidf.fit_transform(documents)
tfidf_query = tfidf.transform([query])

tfidf_scores = cosine_similarity(
    tfidf_query, tfidf_docs
)[0]

# Approach 2: Semantic Embeddings
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

doc_embeddings = model.encode(
    documents, normalize_embeddings=True
)
query_embedding = model.encode(
    [query], normalize_embeddings=True
)

semantic_scores = (
    query_embedding @ doc_embeddings.T
)[0]

# Comparison
for i, document in enumerate(documents):
    print(f"\n{document}")
    print(f"TF-IDF:   {tfidf_scores[i]:.3f}")
    print(f"Semantic: {semantic_scores[i]:.3f}")
