"""Lesson 4B: extract two Arabic text PDFs, preserving raw output.
Run: python archive/previous_lessons/phase1_pipeline/run.py extract
Requires: pip install pymupdf
"""
from pathlib import Path
import json
import re
import unicodedata
import pymupdf

from .paths import DATA_DIR

ROOT = DATA_DIR.parent
RAW = DATA_DIR / 'raw'
OUT = DATA_DIR / 'extracted'
BOOKS = ['nabulsi.pdf', 'ibn-Shahin.pdf']


def normalize_unicode(s: str) -> str:
    # Character compatibility normalization only, not linguistic rewriting.
    return unicodedata.normalize('NFKC', s)


def reverse_line_words(line: str) -> str:
    # Experimental correction for these PDFs: token order is reversed.
    # This cannot repair words split or joined incorrectly by the PDF font.
    tokens = line.split()
    return ' '.join(reversed(tokens)) if tokens else ''


def extract_one(filename: str) -> dict:
    pdf_path = RAW / filename
    if not pdf_path.exists():
        raise FileNotFoundError(f'Place the PDF here: {pdf_path}')
    OUT.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    raw_pages, candidates, page_stats = [], [], []
    with pymupdf.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            raw = page.get_text('text', sort=True)
            normalized = normalize_unicode(raw)
            candidate = '\n'.join(reverse_line_words(line) for line in normalized.splitlines())
            raw_pages.append(f'\n===== PDF PAGE {page_num} =====\n{raw}')
            candidates.append(f'\n===== PDF PAGE {page_num} =====\n{candidate}')
            page_stats.append({'pdf_page': page_num, 'characters': len(raw), 'empty': not raw.strip()})
    (OUT / f'{stem}_raw.txt').write_text(''.join(raw_pages), encoding='utf-8')
    (OUT / f'{stem}_candidate.txt').write_text(''.join(candidates), encoding='utf-8')
    return {'book': filename, 'pages': len(page_stats),
            'pages_without_text': [p['pdf_page'] for p in page_stats if p['empty']],
            'outputs': [f'{stem}_raw.txt', f'{stem}_candidate.txt'],
            'candidate_status': 'NEEDS HUMAN VALIDATION'}


if __name__ == '__main__':
    results = [extract_one(name) for name in BOOKS]
    (OUT / 'report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))
