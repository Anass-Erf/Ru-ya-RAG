"""Reassemble same-baseline spans while preserving native span text and geometry.

These profiles are for the supplied single-column PDFs. All text remains candidate
text: embedded fonts and overlapping spans can still encode incorrect Arabic.
"""
from pathlib import Path
import re
import pymupdf

from .catalog import Book
from .models import Page, SourceLine, SourceSpan
from .normalization import unicode_normalize, spaces, text_flags, ARABIC

BASELINE_TOLERANCE = 1.5


def extract_page(page, book: Book, source_sha256: str) -> Page:
    original = page.get_text('text', sort=False)
    rows: list[tuple[float, list[SourceSpan]]] = []
    for block_index, block in enumerate(page.get_text('rawdict', flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES)['blocks']):
        for line_index, line in enumerate(block.get('lines', [])):
            for span_index, span in enumerate(line['spans']):
                span_text = ''.join(char['c'] for char in span['chars'])
                if not span_text.strip():
                    # Whitespace-only spans remain in original_text, not layout rows.
                    continue
                arabic_x = [c['origin'][0] for c in span['chars'] if ARABIC.search(unicode_normalize(c['c']))]
                suspect = any(b > a + 3 for a, b in zip(arabic_x, arabic_x[1:]))
                item = SourceSpan(block=block_index, line=line_index, span=span_index,
                                  bbox=span['bbox'], baseline=span['origin'][1],
                                  color=span['color'], text=span_text, glyph_order_suspect=suspect)
                row = next((r for r in rows if abs(r[0] - item.baseline) <= BASELINE_TOLERANCE), None)
                if row is None:
                    row = (item.baseline, [])
                    rows.append(row)
                row[1].append(item)
    lines = []
    for number, (_, spans) in enumerate(sorted(rows, key=lambda r: r[0]), 1):
        # Preserve PDF native span sequence, not reverse words or Arabic characters.
        raw = ''.join(s.text for s in spans)
        normalized = unicode_normalize(raw)
        fragments = []
        transformations = []
        for i, span in enumerate(spans):
            # A visible gap separates words; touching glyph fragments stay joined.
            if i and fragments[-1] and span.text:
                previous = spans[i - 1]
                gap = previous.bbox[0] - span.bbox[2]
                if gap >= 1.8 and fragments[-1][-1].isalnum() and span.text[0].isalnum():
                    fragments.append(' ')
                    transformations.append('geometry_word_space')
            fragments.append(span.text)
        candidate = spaces(unicode_normalize(''.join(fragments)))
        bbox = (min(s.bbox[0] for s in spans), min(s.bbox[1] for s in spans),
                max(s.bbox[2] for s in spans), max(s.bbox[3] for s in spans))
        flags = text_flags(candidate)
        if any(s.glyph_order_suspect for s in spans):
            flags.append('nonmonotonic_arabic_glyph_order')
        meaningful = [s for s in spans if len(ARABIC.findall(unicode_normalize(s.text))) >= 3]
        for left, right in zip(meaningful, meaningful[1:]):
            overlap = min(left.bbox[2], right.bbox[2]) - max(left.bbox[0], right.bbox[0])
            if overlap > 3:
                flags.append('overlapping_text_spans')
            if right.bbox[0] > left.bbox[2] + 3:
                flags.append('ambiguous_span_order')
        excluded = None
        if bbox[1] > page.rect.height * .88:
            if book.id == 'nabulsi' and re.fullmatch(r'تعطير الأنام في تفسير الأحلام-عبد الغني النابلسي\s*\d+', candidate):
                excluded = 'repeated_book_footer'
            elif re.fullmatch(r'[0-9٠-٩]+', candidate):
                excluded = 'page_number_footer'
            elif 'ISLAM' in candidate and 'ICBOOK' in candidate:
                excluded = 'publisher_footer'
        lines.append(SourceLine(line_number=number, bbox=bbox, raw_text=raw,
                                normalized_text=normalized, candidate_text=candidate,
                                spans=spans, transformations=sorted(set(transformations)), excluded_reason=excluded,
                                review_flags=sorted(set(flags))))
    body = '\n'.join(l.candidate_text for l in lines if not l.excluded_reason)
    flags = sorted({flag for l in lines if not l.excluded_reason for flag in l.review_flags})
    if not original.strip():
        flags.append('no_text_layer_on_page')
    elif len(ARABIC.findall(body)) < 25:
        flags.append('very_little_arabic')
    if source_sha256 != book.sha256:
        flags.append('unrecognized_source_edition')
    return Page(book_id=book.id, source_file=book.filename, source_sha256=source_sha256,
                pdf_page=page.number + 1, width=page.rect.width, height=page.rect.height,
                original_text=original, normalized_text=unicode_normalize(original),
                corrected_candidate_text=body, lines=lines, review_flags=flags,
                validation_status='needs_review' if flags else 'unreviewed')


def extract_book(path: Path, book: Book, checksum: str) -> list[Page]:
    with pymupdf.open(path) as document:
        return [extract_page(page, book, checksum) for page in document]
