"""Small, inspectable Arabic query expansion; not a general Arabic stemmer."""
import re
from backend.app.rag.ingestion.normalization import search_normalize

ALIASES = {
    'اسافر': 'سفر', 'نسافر': 'سفر', 'يسافر': 'سفر', 'تسافر': 'سفر',
    'سافرت': 'سفر', 'سافرنا': 'سفر', 'سافر': 'سفر', 'مسافر': 'سفر',
    'امواج': 'موج', 'سفن': 'سفينة', 'بحار': 'بحر',
}
STOPWORDS = {'في', 'من', 'ان', 'انني', 'انه', 'رأيت', 'رايت', 'المنام', 'منام', 'كان', 'كانت', 'لكنني', 'وسط', 'الي', 'علي'}


def forms(word):
    # Strip only definite articles and common conjunction/article combinations.
    values = {word}
    for prefix in ('وال', 'فال', 'بال', 'كال', 'لل', 'ال'):
        if word.startswith(prefix) and len(word) - len(prefix) >= 2:
            values.add(word[len(prefix):])
    return values


def query_terms(text):
    words = re.findall(r'[\u0621-\u064a]+|[a-z0-9]+', search_normalize(text).lower())
    result = set()
    for word in words:
        for form in forms(word):
            if form not in STOPWORDS:
                result.add(form)
                if form in ALIASES:
                    result.add(ALIASES[form])
    return result


def symbol_matches(query, symbol):
    if not symbol:
        return False
    terms = query_terms(query)
    if search_normalize(symbol).strip() == 'موج الماء':
        return 'موج' in terms
    required = [next((v for v in forms(w) if v != w), w) for w in search_normalize(symbol).split()]
    return bool(required) and all(word in terms for word in required)
