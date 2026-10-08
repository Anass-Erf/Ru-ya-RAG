"""Book-specific boundary rules, with explicit rejected-candidate diagnostics."""
import hashlib
import re
from .models import Boundary, Page, SourceLine
from .normalization import spaces, search_normalize, unicode_normalize, ARABIC

LETTERS = ('الألف', 'الباء', 'التاء', 'الثاء', 'الجيم', 'الحاء', 'الخاء',
           'الدال', 'الذال', 'الراء', 'الزاي', 'السين', 'الشين', 'الصاد',
           'الضاد', 'الطاء', 'الظاء', 'العين', 'الغين', 'الفاء', 'القاف',
           'الكاف', 'اللام', 'الميم', 'النون', 'الهاء', 'الواو', 'الياء', 'الهمزة')
CHAPTERS = {'باب ' + letter for letter in LETTERS}
QUOTED = re.compile(r'^\s*(?P<prefix>[-–—]\s*)?[“"«]\s*(?P<label>[^“”"»]{1,90})[“”"»]\s*(?P<rest>.*)$')
SHAHIN_HEADING_COLOR = 868775


def chapter_from_line(text: str) -> str | None:
    text = spaces(unicode_normalize(text))
    text = re.sub(r'^[.\d٠-٩…\s–—-]+', '', text)
    text = re.sub(r'(?<=ا)\s+ء\b', 'ء', text)
    return text if text in CHAPTERS else None


def symbol_from_line(text: str) -> tuple[str | None, str]:
    match = QUOTED.match(text)
    if not match:
        return None, 'not_quoted_heading'
    label = match['label']
    if not (match['prefix'] or re.search('[-–—]', label) or re.match(r'^[-–—]', match['rest'])):
        return None, 'quotation_without_entry_marker'
    label = spaces(re.sub('[-–—]', ' ', label)).strip(' :؛،')
    compact = search_normalize(label).replace(' ', '')
    # Whitespace in PDF glyph runs must not turn continuation phrases into symbols.
    if (re.match(r'^(?:و|ف)?(?:كذلك)?(?:من|ان|اذا|لو)(?:را|اي|ري)', compact)
            or compact.startswith(('ومن', 'فمن', 'وقيل', 'خاتمة'))
            or label.startswith(('قال ', 'وقال '))
            or compact in {'قال', 'وقال', 'واعلم', 'مقدمة', 'الابواب', 'فصل', 'تابع'}):
        return None, 'continuation_or_editorial_label'
    if not 2 <= len(label) <= 65 or not ARABIC.search(label) or any(c.isdigit() for c in label):
        return None, 'malformed_label'
    return label, 'quoted_dash_entry'


def is_shahin_heading(line: SourceLine) -> bool:
    letters = [s for s in line.spans if ARABIC.search(unicode_normalize(s.text))]
    return bool(letters) and all(s.color == SHAHIN_HEADING_COLOR for s in letters)


def make_boundary(page: Page, line: SourceLine, kind: str, label: str,
                  chapter: str | None, section: str | None, symbol: str | None, rule: str) -> Boundary:
    key = f'{page.source_sha256}:{page.book_id}:{page.pdf_page}:{line.line_number}:{kind}'
    return Boundary(id=f'{page.book_id}_boundary_{hashlib.sha256(key.encode()).hexdigest()[:20]}',
                    book_id=page.book_id, pdf_page=page.pdf_page, line_number=line.line_number,
                    kind=kind, label=label, source_text=line.candidate_text,
                    chapter=chapter, section=section, symbol=symbol, rule=rule)


def detect_boundaries(pages: list[Page]) -> tuple[list[Boundary], list[dict]]:
    if len({p.book_id for p in pages}) != 1:
        raise ValueError('Parse exactly one book at a time')
    if [p.pdf_page for p in pages] != sorted({p.pdf_page for p in pages}):
        raise ValueError('Pages must be unique and ordered')
    boundaries, rejected = [], []
    chapter = section = None
    ended = False
    rows = [(p, line) for p in pages for line in p.lines if not line.excluded_reason]
    for index, (page, line) in enumerate(rows):
        if line.excluded_reason:
            continue
        text = line.candidate_text
        if page.book_id == 'nabulsi':
            normalized = spaces(re.sub('[“”"«»]', '', text)).lstrip('- ')
            if normalized in {'خاتمة المؤلف', 'خاتمة الكتاب'} or normalized.startswith(('خاتمة الكتاب ', 'وحيث انتهى بنا الغرض من الكتاب')):
                if not ended:
                    boundaries.append(make_boundary(page, line, 'end_matter', 'خاتمة المؤلف', chapter, None, None, 'explicit_author_transition'))
                ended = True
            if ended:
                continue
            found = chapter_from_line(text)
            if found:
                chapter = found
                boundaries.append(make_boundary(page, line, 'chapter', found, chapter, None, None, 'alphabetic_chapter_whitelist'))
                continue
            symbol, rule = symbol_from_line(text)
            if chapter and symbol:
                boundaries.append(make_boundary(page, line, 'entry', symbol, chapter, None, symbol, rule))
            elif QUOTED.match(text):
                rejected.append({'book_id': page.book_id, 'pdf_page': page.pdf_page,
                                 'line_number': line.line_number, 'text': text,
                                 'reason': rule if not symbol else 'before_first_chapter'})
        elif page.book_id == 'ibn-Shahin':
            colored = is_shahin_heading(line)
            chapter_match = re.fullmatch(r'الباب [\u0621-\u064a ]{2,55}', text)
            section_match = re.fullmatch(r'فصل(?: .{1,150})?', text)
            if colored and (chapter_match or section_match):
                # Include wrapped blue titles; retain exact source rows in page records.
                pieces = [text]
                for following_page, following in rows[index + 1:index + 7]:
                    if (following_page.pdf_page > page.pdf_page + 1 or following.excluded_reason or not is_shahin_heading(following)
                            or following.candidate_text.startswith(('الباب ', 'فصل'))):
                        break
                    pieces.append(following.candidate_text)
                label = ' '.join(pieces)
                if chapter_match:
                    chapter, section = label, None
                    boundaries.append(make_boundary(page, line, 'chapter', label, chapter, None, None, 'blue_chapter_heading'))
                elif chapter:
                    section = label
                    boundaries.append(make_boundary(page, line, 'section', label, chapter, section, None, 'blue_section_heading'))
                else:
                    rejected.append({'book_id': page.book_id, 'pdf_page': page.pdf_page,
                                     'line_number': line.line_number, 'text': text,
                                     'reason': 'introductory_section_before_first_chapter'})
            elif text.startswith(('الباب ', 'فصل')):
                rejected.append({'book_id': page.book_id, 'pdf_page': page.pdf_page,
                                 'line_number': line.line_number, 'text': text,
                                 'reason': 'body_reference_not_colored_heading'})
    return boundaries, rejected
