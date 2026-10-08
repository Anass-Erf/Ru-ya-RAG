"""Conservative entry-start detection for the Al-Nabulsi PDF.
Run: python archive/previous_lessons/phase1_pipeline/run.py detect
Only produces REVIEW candidates. Does not generate chunks or alter input.
"""
import json
import re
from collections import Counter
from pathlib import Path

from .paths import DATA_DIR

ROOT = DATA_DIR.parent
SOURCE = DATA_DIR / 'processed' / 'pages.jsonl'
OUT = DATA_DIR / 'processed'

LETTER_NAMES = (
    'الألف', 'الباء', 'التاء', 'الثاء', 'الجيم', 'الحاء', 'الخاء',
    'الدال', 'الذال', 'الراء', 'الزاي', 'السين', 'الشين',
    'الصاد', 'الضاد', 'الطاء', 'الظاء', 'العين', 'الغين',
    'الفاء', 'القاف', 'الكاف', 'اللام', 'الميم', 'النون',
    'الهاء', 'الواو', 'الياء', 'الهمزة',
)
KNOWN_CHAPTERS = {'باب ' + name for name in LETTER_NAMES}
# Only headings explicitly enclosed in the PDF's distinctive quotation marks.
QUOTED = re.compile(r'^\s*(?P<prefix>[-–—]\s*)?[“"«]\s*(?P<label>.{1,65}?)\s*[“”"»]\s*(?P<rest>.*)$')
ARABIC = re.compile(r'[\u0621-\u064a]')
EXCLUDED = {
    'مقدمة', 'الأبواب', 'واعلم', 'من رأى', 'ومن رأى',
    'قال', 'وقال', 'قال بعضهم', 'وقال بعضهم', 'فصل',
    'خاتمة', 'خاتمة الكتاب', 'تابع', 'وقيل من رأى', 'الأبواب',
}

def normalize_spaces(text):
    return ' '.join(text.split())

def chapter_from_line(line):
    # Repair only known split chapter names, NOT body text.
    candidate = normalize_spaces(line)
    candidate = re.sub(r'(?<=ا)\s+ء\b', 'ء', candidate)
    return candidate if candidate in KNOWN_CHAPTERS else None

def candidate_from_line(line):
    match = QUOTED.match(line)
    if not match:
        return None
    inside = match.group('label')
    # Genuine entries use a dash before the quotation OR inside the label.
    # Bare quoted verses and quotations must not become entries.
    if not (match.group('prefix') or re.search(r'[-–—]', inside) or re.match(r'^\s*[-–—]', match.group('rest'))):
        return None
    # Dash may occur inside label (broken layout). Remove it only in label.
    symbol = normalize_spaces(re.sub(r'\s*[-–—]\s*', ' ', inside))
    symbol = symbol.strip(' -–—:؛،"“”')
    symbol = symbol.replace('االله', 'الله')
    if not (2 <= len(symbol) <= 45 and ARABIC.search(symbol)):
        return None
    if symbol in EXCLUDED or symbol.startswith(('ومن رأى', 'من رأى', 'و من رأى', 'وقيل', 'وقال', 'قال ', 'خاتمة')):
        return None
    if any(ch.isdigit() for ch in symbol):
        return None
    # Candidate must have a short heading label in quotes; no guarantee it is genuine.
    return symbol

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f'Missing {SOURCE}')
    results = []
    chapter = None
    pages = 0
    chapters_found = set()
    with SOURCE.open(encoding='utf-8') as f:
        for raw in f:
            page = json.loads(raw)
            if page.get('book_id') != 'nabulsi':
                continue
            pages += 1
            text = page.get('cleaned_text') or ''
            for line_no, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                found = chapter_from_line(stripped)
                if found:
                    chapter = found
                    chapters_found.add(found)
                    continue
                # Never count pre-chapter introduction as symbol entries.
                if chapter is None:
                    continue
                symbol = candidate_from_line(stripped)
                if symbol is None:
                    continue
                results.append({
                    'book_id': 'nabulsi',
                    'pdf_page': page['pdf_page'],
                    'line_in_page': line_no,
                    'chapter_candidate': chapter,
                    'symbol_candidate': symbol,
                    'source_line': stripped,
                    'validated': False,
                })
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'nabulsi_entry_candidates_v3.jsonl'
    with path.open('w', encoding='utf-8') as f:
        for rec in results:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    report = {
        'status': 'REVIEW_ONLY_UNVALIDATED',
        'pages_processed': pages,
        'distinct_chapters_detected': len(chapters_found),
        'entry_start_candidates': len(results),
        'chapter_distribution': dict(Counter(rec['chapter_candidate'] for rec in results)),
        'warning': 'Heuristic candidates, not approved chunks. Review false positives and missed entries.',
    }
    (OUT / 'nabulsi_entry_report_v3.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('\nFirst 15 candidates:')
    for rec in results[:15]:
        print(f"p.{rec['pdf_page']}: {rec['symbol_candidate']}")

if __name__ == '__main__':
    main()
