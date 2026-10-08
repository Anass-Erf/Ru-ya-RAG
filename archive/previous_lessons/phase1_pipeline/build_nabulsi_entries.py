"""Build REVIEW-ONLY complete Al-Nabulsi entry candidates from detected starts.

Usage: python archive/previous_lessons/phase1_pipeline/run.py entries
Inputs: data/processed/pages.jsonl, nabulsi_entry_candidates_v3.jsonl
Outputs: data/processed/nabulsi_entries_review.jsonl, nabulsi_entries_report.json,
         nabulsi_entries_samples.txt
No embeddings or claims of validated interpretations.
"""
import json
import re
from collections import Counter
from pathlib import Path

from .paths import DATA_DIR

ROOT = DATA_DIR.parent
DIR = DATA_DIR / 'processed'
PAGES = DIR / 'pages.jsonl'
STARTS = DIR / 'nabulsi_entry_candidates_v3.jsonl'
ENTRIES = DIR / 'nabulsi_entries_review.jsonl'
REPORT = DIR / 'nabulsi_entries_report.json'
SAMPLES = DIR / 'nabulsi_entries_samples.txt'

LETTERS = ('الألف', 'الباء', 'التاء', 'الثاء', 'الجيم', 'الحاء', 'الخاء',
           'الدال', 'الذال', 'الراء', 'الزاي', 'السين', 'الشين',
           'الصاد', 'الضاد', 'الطاء', 'الظاء', 'العين', 'الغين',
           'الفاء', 'القاف', 'الكاف', 'اللام', 'الميم', 'النون',
           'الهاء', 'الواو', 'الياء', 'الهمزة')
CHAPTERS = {'باب ' + name for name in LETTERS}


def normalize_chapter(line):
    line = ' '.join(line.split())
    line = re.sub(r'(?<=ا)\s+ء\b', 'ء', line)
    return line if line in CHAPTERS else None


def read_jsonl(path):
    with path.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    for path in (PAGES, STARTS):
        if not path.exists():
            raise FileNotFoundError(f'Missing {path}. Run previous lessons first.')

    pages = [p for p in read_jsonl(PAGES) if p.get('book_id') == 'nabulsi']
    pages.sort(key=lambda p: p['pdf_page'])
    starts = list(read_jsonl(STARTS))
    positions = {}
    for record in starts:
        key = (record['pdf_page'], record['line_in_page'])
        if key in positions:
            raise ValueError(f'Duplicate entry start: {key}')
        positions[key] = record

    rows = []
    boundaries = []
    for p in pages:
        page_number = p['pdf_page']
        for line_no, line in enumerate((p.get('cleaned_text') or '').splitlines(), 1):
            key = (page_number, line_no)
            chapter = normalize_chapter(line.strip())
            if chapter:
                boundaries.append((len(rows), 'chapter', chapter))
                continue
            rows.append({'page': page_number, 'line': line_no, 'text': line})
            if key in positions:
                boundaries.append((len(rows) - 1, 'entry', positions[key]))

    # Sanity-check every candidate was mapped to the exact source line.
    found = {(row['page'], row['line']) for row in rows}
    missing = sorted(set(positions) - found)
    if missing:
        raise ValueError(f'{len(missing)} candidate starts not present in pages.jsonl: {missing[:5]}')

    boundaries.sort(key=lambda b: b[0])
    entries = []
    dropped_empty = 0
    for index, (start_ix, kind, source) in enumerate(boundaries):
        if kind != 'entry':
            continue
        end_ix = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(rows)
        block = rows[start_ix:end_ix]
        text = '\n'.join(r['text'].strip() for r in block if r['text'].strip()).strip()
        if not text:
            dropped_empty += 1
            continue
        p_first, p_last = block[0]['page'], block[-1]['page']
        flags = []
        if p_last - p_first + 1 > 3:
            flags.append('long_page_span_review')
        if len(text) > 9000:
            flags.append('long_text_review')
        if len(text) < 80:
            flags.append('short_text_review')
        entries.append({
            'id': f'nabulsi_entry_{len(entries) + 1:05d}',
            'book_id': 'nabulsi',
            'chapter_candidate': source['chapter_candidate'],
            'symbol_candidate': source['symbol_candidate'],
            'pdf_page_start': p_first,
            'pdf_page_end': p_last,
            'source_line_start': block[0]['line'],
            'source_line_end': block[-1]['line'],
            'text': text,
            'char_count': len(text),
            'review_flags': flags,
            'validated': False,
        })

    with ENTRIES.open('w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    flag_counts = Counter(flag for e in entries for flag in e['review_flags'])
    report = {
        'status': 'REVIEW_ONLY_NOT_READY_FOR_EMBEDDINGS',
        'pages_input': len(pages),
        'entry_starts_input': len(starts),
        'entries_built': len(entries),
        'dropped_empty': dropped_empty,
        'pages_without_guaranteed_entry_coverage': True,
        'flag_counts': dict(flag_counts),
        'chapter_distribution': dict(Counter(e['chapter_candidate'] for e in entries)),
        'notes': [
            'Each entry runs from its candidate start to the next entry or chapter heading.',
            'Missed starts can merge several real symbols; false starts can split an entry.',
            'Keep this output out of the vector index until reviewed.',
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    picks = entries[:3] + [e for e in entries if e['review_flags']][:4] + entries[-3:]
    with SAMPLES.open('w', encoding='utf-8') as f:
        for e in picks:
            f.write(f"\n{'=' * 70}\n{e['id']} | {e['chapter_candidate']} | {e['symbol_candidate']} | PDF pp. {e['pdf_page_start']}-{e['pdf_page_end']} | {e['review_flags']}\n")
            f.write(e['text'][:1400] + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('\nSample entries:')
    for e in entries[:5]:
        print(f"{e['id']} | {e['symbol_candidate']} | pages {e['pdf_page_start']}-{e['pdf_page_end']} | {e['char_count']} chars")


if __name__ == '__main__':
    main()
