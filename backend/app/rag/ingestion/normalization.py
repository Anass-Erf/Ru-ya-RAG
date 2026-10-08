"""Mechanical transformations only: no speculative Arabic word repair."""
import re
import unicodedata

ARABIC = re.compile(r'[\u0621-\u064a]')


def unicode_normalize(text: str) -> str:
    return unicodedata.normalize('NFKC', text)


def spaces(text: str) -> str:
    return ' '.join(text.split())


def search_normalize(text: str) -> str:
    text = unicode_normalize(text)
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text)
    text = re.sub('[أإآٱ]', 'ا', text).replace('ى', 'ي')
    return spaces(text)


def text_flags(text: str) -> list[str]:
    flags = []
    if '\ufffd' in text:
        flags.append('replacement_character')
    if re.search(r'[\ufb50-\ufdff\ufe70-\ufeff]', text):
        flags.append('presentation_forms_remain')
    if re.search(r'االله|اجمل|هبا|رهبم|أهنا|إهنا', text):
        flags.append('known_font_encoding_artifact')
    return flags
