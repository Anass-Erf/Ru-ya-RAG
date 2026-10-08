
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Our initial corpus (educational examples, not sourced interpretations)
documents = [
    "رؤية الماء الصافي في المنام",
    "رؤية الأسد في المنام",
    "رؤية المطر الغزير في المنام",
    "رؤية السفر في طريق طويل",
    "رؤية البحر والأمواج في المنام",
]

# 2. Arabic normalization
def normalize_arabic(text):
    # Remove Arabic diacritics and tatweel
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)

    # Normalize Alef variants
    text = re.sub(r"[أإآ]", "ا", text)

    # Normalize Alef Maksura
    text = text.replace("ى", "ي")

    return text.strip()

# 3. Transform documents into TF-IDF vectors
vectorizer = TfidfVectorizer(
    preprocessor=normalize_arabic
)

document_vectors = vectorizer.fit_transform(documents)

# 4. User query
#query = "رأيت الماء الصافي في المنام"
query = "حلمت بشرب مياه نقية"
query_vector = vectorizer.transform([query])

# 5. Compute cosine similarities
scores = cosine_similarity(
    query_vector,
    document_vectors
)[0]

# 6. Rank and display results
ranking = scores.argsort()[::-1]

for index in ranking:
    print(f"Score: {scores[index]:.3f}")
    print(f"Document: {documents[index]}")
    print("---")
