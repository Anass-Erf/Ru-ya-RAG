"""Lesson 4D: review-only candidate heading detection from page-level JSONL.
Run from ruya-rag root: python archive/previous_lessons/phase1_pipeline/run.py structure
Never treats candidate headings as verified entry boundaries.
"""
import json
import re
from pathlib import Path

from .paths import DATA_DIR

ROOT = DATA_DIR.parent
SOURCE = DATA_DIR / 'processed' / 'pages.jsonl'
OUT = DATA_DIR / 'processed'

# These are deliberately broad heuristics, not final section parsers.
PATTERNS = {
    'nabulsi': [
        ('chapter', re.compile(r'^\s*باب\s+[\u0621-\u064a].{0,75}$')),
        ('possible_entry', re.compile(r'^\s*[-–—]?\s*[«"“]?[-–—]?\s*[\u0621-\u064a][\u0621-\u064a\s]{0,32}["”»]\s*[-–—]?\s*$')),
    ],
    'ibn-Shahin': [
        ('chapter', re.compile(r'^\s*الباب\s+(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|[\u0621-\u064a ]{1,40})\s*$')),
        ('section', re.compile(r'^\s*فصل\s*(?:في\s+.{1,80})?$')),
    ],
}

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f'Missing {SOURCE}; run clean_validate.py first')
    candidates = []
    page_count = {}
    for json_line in SOURCE.read_text(encoding='utf-8').splitlines():
        if not json_line.strip():
            continue
        page = json.loads(json_line)
        book = page['book_id']
        page_count[book] = page_count.get(book, 0) + 1
        for line_no, line in enumerate(page['cleaned_text'].splitlines(), 1):
            for kind, pattern in PATTERNS.get(book, []):
                if pattern.fullmatch(line.strip()):
                    candidates.append({
                        'book_id': book,
                        'pdf_page': page['pdf_page'],
                        'line_in_page': line_no,
                        'kind': kind,
                        'heading': line.strip(),
                        'validated': False,
                    })
                    break
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'structure_candidates.jsonl').open('w', encoding='utf-8') as stream:
        for record in candidates:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
    totals = {}
    for record in candidates:
        key = f"{record['book_id']}:{record['kind']}"
        totals[key] = totals.get(key, 0) + 1
    report = {
        'status': 'UNVALIDATED_HEURISTIC_CANDIDATES',
        'pages_inspected': page_count,
        'candidate_counts': totals,
        'examples': candidates[:12],
        'next_action': 'Compare candidate headings to original PDF pages before segmenting into entries.'
    }
    (OUT / 'structure_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='examples'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
