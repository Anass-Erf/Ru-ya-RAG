"""Source-grounded regression tests; fixture coordinates refer to PDF pages."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf
from pydantic import ValidationError
from backend.app.rag.ingestion.catalog import BOOKS
from backend.app.rag.ingestion.extraction import extract_page
from backend.app.rag.ingestion.models import Page, Passage
from backend.app.rag.ingestion.normalization import search_normalize, unicode_normalize
from backend.app.rag.ingestion.parsers import chapter_from_line, symbol_from_line, detect_boundaries
from backend.app.rag.ingestion.pipeline import run_ingestion, verify_run
from backend.app.rag.ingestion.reconstruction import reconstruct
from backend.app.rag.ingestion.review import Decision, apply_decisions

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / 'fixtures/source_pages.jsonl'


class IngestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = [Page.model_validate_json(line) for line in FIXTURES.read_text().splitlines()]
        cls.by_key = {(p.book_id, p.pdf_page): p for p in cls.pages}

    def get_pages(self, book, *numbers):
        return [self.by_key[(book, n)] for n in numbers]

    def test_normalization_keeps_display_and_search_separate(self):
        self.assertEqual(unicode_normalize('ﺑﺎﺏ'), 'باب')
        self.assertEqual(search_normalize('إِبْرَاهِيم ـ أَحْمَد على'), 'ابراهيم احمد علي')
        self.assertEqual(unicode_normalize('على'), 'على')

    def test_native_extraction_fidelity_and_no_word_reversal(self):
        for book_id, number in [('nabulsi', 1357), ('ibn-Shahin', 304), ('ibn-Shahin', 20)]:
            book = BOOKS[book_id]
            with pymupdf.open(ROOT / 'data/raw' / book.filename) as document:
                record = extract_page(document[number - 1], book, book.sha256)
                self.assertEqual(record.original_text, document[number - 1].get_text('text', sort=False))
                self.assertEqual(record.model_dump(), self.by_key[(book_id, number)].model_dump())
                for line in record.lines:
                    self.assertEqual(line.raw_text, ''.join(s.text for s in line.spans))
        self.assertIn('باب الواو', self.by_key[('nabulsi', 1357)].corrected_candidate_text)
        self.assertNotIn('ببا الواو', self.by_key[('nabulsi', 1357)].corrected_candidate_text)

    def test_glyph_order_artifact_is_flagged_not_silently_rewritten(self):
        line = self.by_key[('ibn-Shahin', 304)].lines[2]
        self.assertIn('nonmonotonic_arabic_glyph_order', line.review_flags)
        self.assertIn('وأما المداد', line.candidate_text)
        self.assertIsNone(self.by_key[('ibn-Shahin', 304)].validated_text)

    def test_geometric_spaces_repair_split_heading_without_splitting_fragments(self):
        page = self.by_key[('ibn-Shahin', 20)]
        self.assertEqual(page.lines[9].candidate_text, 'الباب السادس')
        self.assertIn('geometry_word_space', page.lines[9].transformations)
        later = self.by_key[('ibn-Shahin', 304)]
        self.assertIn('الباب الثامن والخمسون', later.corrected_candidate_text)

    def test_chapter_whitelist_and_actual_decorated_heading(self):
        self.assertIsNone(chapter_from_line('باب السلطان فإنه يشهد'))
        self.assertEqual(chapter_from_line('باب البا ء'), 'باب الباء')
        boundaries, _ = detect_boundaries(self.get_pages('nabulsi', 1057, 1357))
        self.assertEqual([b.label for b in boundaries if b.kind == 'chapter'], ['باب الكاف', 'باب الواو'])

    def test_prose_is_not_an_entry(self):
        lines = self.by_key[('nabulsi', 9)].lines
        for prefix in ['باختلاف', 'الخير']:
            line = next(l.candidate_text for l in lines if l.candidate_text.startswith(prefix))
            self.assertIsNone(symbol_from_line(line)[0])

    def test_continuations_do_not_recreate_18325_candidate_failure(self):
        pages = self.get_pages('nabulsi', 193, 194, 195, 196, 197, 198)
        boundaries, rejected = detect_boundaries(pages)
        self.assertFalse([b for b in boundaries if b.kind == 'entry' and b.pdf_page == 195])
        self.assertFalse([b for b in boundaries if b.symbol and 'رأى' in b.symbol])
        self.assertGreater(sum(r['reason'] == 'continuation_or_editorial_label' for r in rejected), 20)
        # Also protect a real noun from an over-broad "قال" prefix exclusion.
        self.assertEqual(symbol_from_line('- “ قالب“ هو في المنام')[0], 'قالب')
        for text in ['“ وم- ن رأى“ أنه يبني', '“ ومن- رأ ى“ أنه يملك', '“ وكذلك- إن رأى“ كأنه شرب']:
            self.assertIsNone(symbol_from_line(text)[0])

    def test_unmarked_quotation_is_not_a_symbol(self):
        pages = self.get_pages('nabulsi', 9, 10, 11)
        _, rejected = detect_boundaries(pages)
        quotations = [r for r in rejected if r['reason'] == 'quotation_without_entry_marker']
        self.assertTrue(quotations)
        self.assertTrue(all(symbol_from_line(r['text'])[0] is None for r in quotations))

    def test_both_heading_styles_after_page_460(self):
        pages = self.get_pages('nabulsi', 452, 459, 460, 461, 462)
        boundaries, _ = detect_boundaries(pages)
        detected = {(b.pdf_page, b.symbol) for b in boundaries if b.kind == 'entry'}
        self.assertTrue({(460, 'ذراع'), (460, 'ذبح'), (462, 'ذل')} <= detected)
        self.assertNotIn((462, 'ومن رأى'), detected)

    def test_ibn_shahin_color_blocks_prose_chapters(self):
        boundaries, rejected = detect_boundaries(self.get_pages('ibn-Shahin', 4, 7, 8, 20, 58))
        self.assertTrue(any(b.label.startswith('الباب السادس') for b in boundaries))
        self.assertFalse(any(b.kind == 'chapter' and b.pdf_page == 58 for b in boundaries))
        self.assertTrue(any(r['pdf_page'] == 58 and r['reason'] == 'body_reference_not_colored_heading' for r in rejected))
        self.assertTrue(any(b.kind == 'section' and b.pdf_page == 7 for b in boundaries))

    def test_cross_page_chapter_title(self):
        boundaries, _ = detect_boundaries(self.get_pages('ibn-Shahin', 54, 55))
        chapter = next(b for b in boundaries if b.kind == 'chapter')
        self.assertIn('الباب الثاني عشر', chapter.label)
        self.assertIn('في رؤيا', chapter.label)

    def test_reconstruction_is_cross_page_and_loss_accounted(self):
        pages = self.get_pages('nabulsi', 9, 10, 11)
        boundaries, _ = detect_boundaries(pages)
        passages, excluded = reconstruct(pages, boundaries, BOOKS['nabulsi'])
        first = passages[0]
        self.assertEqual((first.page_start, first.page_end), (9, 11))
        self.assertIn('باختلاف', first.text)
        self.assertIn('الخير', first.text)
        self.assertGreater(len(first.text), 3000)
        self.assertEqual(first.text_sha256, __import__('hashlib').sha256(first.text.encode()).hexdigest())
        self.assertEqual(first.source_file, 'nabulsi.pdf')
        source = {(p.pdf_page, l.line_number): l for p in pages for l in p.lines}
        for passage in passages:
            lines = [source[(r.pdf_page, n)] for r in passage.source_ranges for n in range(r.line_start, r.line_end + 1)]
            self.assertEqual(passage.text, '\n'.join(l.candidate_text for l in lines))
            self.assertEqual(passage.raw_text, '\n'.join(l.raw_text for l in lines))
        covered = sum(r.line_end-r.line_start+1 for p in passages for r in p.source_ranges)
        self.assertEqual(covered+len(excluded), sum(len(p.lines) for p in pages))

    def test_conclusion_is_not_appended_to_last_symbol(self):
        pages = self.get_pages('nabulsi', 1405, 1406)
        # The chapter is already underway; reuse its actual heading as context only.
        from backend.app.rag.ingestion.parsers import make_boundary
        symbols = []
        for l in pages[0].lines:
            symbol, rule = symbol_from_line(l.candidate_text)
            if symbol:
                symbols.append(make_boundary(pages[0], l, 'entry', symbol, 'باب الياء', None, symbol, rule))
        detected, _ = detect_boundaries(pages)
        end = next(b for b in detected if b.kind == 'end_matter')
        passages, excluded = reconstruct(pages, symbols + [end], BOOKS['nabulsi'])
        self.assertTrue(passages)
        self.assertTrue(all(p.page_end == 1405 for p in passages))
        self.assertFalse(any('وحيث انتهى' in p.text for p in passages))
        self.assertTrue(any(r['pdf_page'] == 1406 for r in excluded))

    def test_stable_ids_and_short_entries_preserved(self):
        pages = self.get_pages('ibn-Shahin', 7, 8)
        boundaries, _ = detect_boundaries(pages)
        first, _ = reconstruct(pages, boundaries, BOOKS['ibn-Shahin'])
        repeated, _ = reconstruct(pages, boundaries, BOOKS['ibn-Shahin'])
        self.assertEqual(first, repeated)
        self.assertTrue(first)
        self.assertTrue(all(p.text.strip() != p.chapter for p in first))
        later, _ = reconstruct(pages, boundaries[1:], BOOKS['ibn-Shahin'])
        expected = {p.boundary_id: p.id for p in first}
        self.assertTrue(all(expected[p.boundary_id] == p.id for p in later))

    def test_short_symbol_is_preserved(self):
        from backend.app.rag.ingestion.parsers import make_boundary
        pages = self.get_pages('nabulsi', 462, 463)
        boundaries = []
        for p in pages:
            for line in p.lines:
                label, rule = symbol_from_line(line.candidate_text)
                if label:
                    boundaries.append(make_boundary(p, line, 'entry', label, 'باب الذال', None, label, rule))
        passages, _ = reconstruct(pages, boundaries, BOOKS['nabulsi'])
        short = next(p for p in passages if p.symbol == 'ذم لأرباب المدح')
        self.assertLess(len(short.text), 130)
        self.assertIn('نبيه عليه الصلاة والسلام', short.text)

    def test_reject_mixed_books_stale_boundaries_and_missing_pages(self):
        pages = self.get_pages('nabulsi', 9, 10, 11)
        boundaries, _ = detect_boundaries(pages)
        with self.assertRaises(ValueError):
            reconstruct(pages + self.get_pages('ibn-Shahin', 4), boundaries, BOOKS['nabulsi'])
        with self.assertRaises(ValueError):
            reconstruct([pages[0], pages[2]], boundaries, BOOKS['nabulsi'])
        corrupted = boundaries[0].model_copy(update={'source_text': 'different text'})
        with self.assertRaisesRegex(ValueError, 'source text'):
            reconstruct(pages, [corrupted, *boundaries[1:]], BOOKS['nabulsi'])
        foreign = boundaries[0].model_copy(update={'book_id': 'ibn-Shahin'})
        with self.assertRaisesRegex(ValueError, 'book/position'):
            reconstruct(pages, [foreign], BOOKS['nabulsi'])

    def test_status_and_review_require_actual_evidence(self):
        pages = self.get_pages('nabulsi', 9, 10, 11)
        boundaries, _ = detect_boundaries(pages)
        passages, _ = reconstruct(pages, boundaries, BOOKS['nabulsi'])
        p = passages[0]
        self.assertNotEqual(p.validation_status, 'verified')
        self.assertIsNone(p.validated_text)
        invalid = p.model_dump(); invalid['validation_status'] = 'verified'
        with self.assertRaises(ValidationError):
            Passage.model_validate(invalid)
        decision = Decision(passage_id=p.id, source_sha256=p.source_sha256, text_sha256=p.text_sha256,
                            status='verified', reviewer='test-only', method='assisted_pdf_comparison',
                            reviewed_at='2026-10-08T12:00:00Z', scope='full_passage_and_boundaries',
                            checked_pdf_pages=[9], evidence='Synthetic review decision for validation test only.')
        with self.assertRaisesRegex(ValueError, 'every PDF page'):
            apply_decisions(passages, [decision])
        stale = decision.model_copy(update={'text_sha256': 'stale'})
        with self.assertRaisesRegex(ValueError, 'Stale review'):
            apply_decisions(passages, [stale])

    def test_immutable_runs_reuse_and_detect_tampering(self):
        # Temporary tiny sources plus mocked extraction exercise orchestration without changing PDFs.
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            (data/'raw').mkdir()
            (data/'raw/nabulsi.pdf').write_bytes(b'test-profile-mismatch')
            with patch('backend.app.rag.ingestion.pipeline.extract_book', return_value=self.get_pages('nabulsi', 9)):
                output, reused = run_ingestion(data, data/'runs', ['nabulsi'])
                self.assertFalse(reused)
                report = json.loads((output/'report.json').read_text())
                self.assertEqual(report['books']['nabulsi']['status'], 'SOURCE_PROFILE_MISMATCH')
                self.assertEqual((output/'passages.jsonl').read_text(), '')
                self.assertEqual(run_ingestion(data, data/'runs', ['nabulsi']), (output, True))
                (output/'passages.jsonl').write_text('tampered')
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    verify_run(output)

    def test_scanned_book_is_excluded_even_if_text_appears(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            (data/'raw').mkdir()
            (data/'raw/ibn-sirine.pdf').write_bytes(b'scanned-test')
            page = self.by_key[('nabulsi', 9)].model_copy(update={'book_id': 'ibn-sirin'})
            with patch('backend.app.rag.ingestion.pipeline.extract_book', return_value=[page]):
                output, _ = run_ingestion(data, data/'runs', ['ibn-sirin'])
                report = json.loads((output/'report.json').read_text())
                self.assertEqual(report['books']['ibn-sirin']['status'], 'OCR_PENDING')
                self.assertEqual((output/'passages.jsonl').read_text(), '')


if __name__ == '__main__':
    unittest.main()
