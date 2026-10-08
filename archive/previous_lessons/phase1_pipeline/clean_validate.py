"""Lesson 4C: conservative Arabic PDF candidate cleanup + quality review.
Run from the repo root: python archive/previous_lessons/phase1_pipeline/run.py clean
Requires only the Python standard library.
Inputs created by Lesson 4B: data/extracted/{nabulsi,ibn-Shahin}_candidate.txt
Outputs: data/processed/pages.jsonl and data/processed/quality_report.json
Do NOT embed outputs until representative pages have been checked against the PDFs.
"""
from pathlib import Path
import json
import re
import statistics
import unicodedata

from .paths import DATA_DIR

ROOT = DATA_DIR.parent
INPUT_DIR = DATA_DIR / 'extracted'
OUT_DIR = DATA_DIR / 'processed'
BOOKS = {'nabulsi': 'تعطير الأنام في تعبير المنام', 'ibn-Shahin': 'الإشارات في علم العبارات'}
MARKER = re.compile(r'^===== PDF PAGE (\d+) =====\s*$', re.M)
ARABIC = re.compile(r'[\u0621-\u064A]')
PRESENTATION = re.compile(r'[\uFB50-\uFDFF\uFE70-\uFEFF]')
# Only headers/footers observed in these edition-specific candidate texts.
NABULSI_FOOTER = re.compile(r'^تعطير الأنام في تفسير الأحلام-عبد الغني النابلسي\s+\d+\s*$')
SHAHIN_FOOTER = re.compile(r'^\s*\d+\s*$')

def load_pages(path):
    text = path.read_text(encoding='utf-8')
    matches = list(MARKER.finditer(text))
    if not matches:
        raise ValueError(f'No page markers in {path}')
    for i, match in enumerate(matches):
        until = matches[i+1].start() if i+1 < len(matches) else len(text)
        yield int(match.group(1)), text[match.end():until].strip('\n')

def clean_page(text, book_key):
    lines = []
    removed = []
    for line in unicodedata.normalize('NFKC', text).splitlines():
        line = re.sub(r'[ \t\u00a0]+', ' ', line).strip()
        if not line:
            if lines and lines[-1] != '':
                lines.append('')
            continue
        if book_key == 'nabulsi' and NABULSI_FOOTER.fullmatch(line):
            removed.append(line)
            continue
        # We intentionally do not remove Ibn Shahin numerical lines:
        # they could be real numbered content, not a page footer.
        lines.append(line)
    return '\n'.join(lines).strip(), removed

def flags_for(text):
    flags = []
    if PRESENTATION.search(text): flags.append('presentation_forms_remain')
    if re.search(r'االله|ابلسی|ابلسي|جوالسرا|ويلالتأ|هبا', text):
        flags.append('known_pdf_extraction_artifacts')
    if '\ufffd' in text: flags.append('replacement_character')
    if len(ARABIC.findall(text)) < 25: flags.append('very_little_arabic')
    return flags

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {'status': 'REVIEW_REQUIRED', 'books': {}}
    all_records = []
    for key, title in BOOKS.items():
        path = INPUT_DIR / f'{key}_candidate.txt'
        if not path.exists():
            raise FileNotFoundError(f'Missing {path}; run Lesson 4B first')
        records = []
        for page_num, raw in load_pages(path):
            cleaned, removed = clean_page(raw, key)
            flags = flags_for(cleaned)
            rec = {'id': f'{key}_page_{page_num:04d}', 'book_id': key,
                   'book': title, 'pdf_page': page_num,
                   'candidate_text': raw, 'cleaned_text': cleaned,
                   'removed_lines': removed, 'review_flags': flags,
                   'validated': False}
            records.append(rec)
        if len(set(r['pdf_page'] for r in records)) != len(records):
            raise ValueError(f'Duplicate pages in {key}')
        flagged = [r['pdf_page'] for r in records if r['review_flags']]
        report['books'][key] = {
            'pages': len(records), 'pages_with_flags': len(flagged),
            'sample_flagged_pages': flagged[:20],
            'empty_cleaned_pages': [r['pdf_page'] for r in records if not r['cleaned_text']][:20],
            'characters_cleaned': sum(len(r['cleaned_text']) for r in records),
            'removed_header_footer_lines': sum(len(r['removed_lines']) for r in records),
            'notes': 'Page-level candidate, not final interpretation chunks.'}
        all_records.extend(records)
    with (OUT_DIR / 'pages.jsonl').open('w', encoding='utf-8') as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    (OUT_DIR / 'quality_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    samples = []
    for key in BOOKS:
        pages = [r for r in all_records if r['book_id'] == key]
        for pos in sorted(set([0, len(pages)//2, len(pages)-1])):
            r = pages[pos]
            samples.append(f"BOOK: {key} | PDF PAGE: {r['pdf_page']} | FLAGS: {r['review_flags']}\n{r['cleaned_text'][:1100]}\n")
    (OUT_DIR / 'review_samples.txt').write_text('\n'+'\n---\n'.join(samples), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
