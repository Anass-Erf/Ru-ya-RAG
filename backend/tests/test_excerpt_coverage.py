import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from backend.app.rag.retrieval.index import read_corpus
from backend.app.rag.retrieval.query import symbol_matches, source_topics
from backend.app.rag.chunking.excerpts import reviewed_excerpts
from backend.app.core.config import Settings
from backend.app.main import create_app
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[2]
DREAM='رأيت في المنام أنني أسافر في سفينة وسط البحر، وكانت الأمواج عالية، لكنني وصلت إلى الشاطئ بسلام.'


class ExcerptCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.passages,cls.rows,cls.handoff=read_corpus(ROOT)

    @staticmethod
    def tokenizer(text,**kwargs):return {'input_ids':list(range(len(text.split())))}

    def test_explicit_arabic_forms_without_substring_false_matches(self):
        for symbol in ['سفر','سفينة','بحر','موج الماء']:
            self.assertTrue(symbol_matches(DREAM,symbol),symbol)
        self.assertTrue(symbol_matches('رأيت السفن','سفينة'))
        self.assertFalse(symbol_matches('سفرجل','سفر'))
        self.assertFalse(symbol_matches('سفرة','سفر'))
        self.assertFalse(symbol_matches('بحر','سفينة'))

    def test_section_topics_require_explicit_headings(self):
        self.assertEqual(source_topics(None, 'فصل في رؤيا السراب'), ['السراب'])
        self.assertEqual(source_topics(None, 'فصل في رؤيا الطل وهو الندى'), ['الطل', 'الندى'])
        self.assertEqual(source_topics(None, 'الباب الثالث'), [])
        self.assertEqual(source_topics(None, 'قال المؤلف في رؤيا السراب'), [])
        self.assertEqual(source_topics('سفينة', 'فصل في رؤيا البحر'), ['سفينة'])
        topics = source_topics(None, 'فصل في رؤيا القيح والصديد')
        self.assertFalse(any(symbol_matches('رأيت القيح', t) for t in topics))

    def test_exact_excerpts_do_not_promote_parent_passages(self):
        chunks=reviewed_excerpts(ROOT,self.passages,self.rows,self.tokenizer,self.handoff,120,'reviewed')
        self.assertEqual(len(chunks),6)
        lookup={p.id:p for p in self.passages}
        for c in chunks:
            parent=lookup[c.parent_entry_id]
            self.assertNotEqual(parent.validation_status,'verified')
            self.assertEqual(parent.text[c.char_start:c.char_end],c.text)
            self.assertIn('excerpt_source_review',c.review_flags)
            self.assertEqual(c.validation_status,'verified')
            self.assertNotIn('االله',c.text)

    def test_review_rejects_forged_quote_and_unchecked_page(self):
        original=json.loads((ROOT/self.handoff['excerpt_reviews']).read_text())
        for mutation in ['quote','page','offset']:
            data=json.loads(json.dumps(original))
            d=data['decisions'][0]
            if mutation=='quote':d['quote']='هذا اقتباس مختلق لا يوجد في النص الأصلي'
            if mutation=='page':d['checked_pdf_pages']=[1]
            if mutation=='offset':d['char_end']+=1
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'reviews.json';path.write_text(json.dumps(data))
                handoff={**self.handoff,'excerpt_reviews':'reviews.json','excerpt_reviews_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.assertRaises(ValueError):reviewed_excerpts(Path(folder),self.passages,self.rows,self.tokenizer,handoff,120,'reviewed')

    def test_user_dream_returns_scoped_sources_without_paid_generation(self):
        with TestClient(create_app(Settings(enable_generation=False))) as client:
            response=client.post('/api/interpret',json={'query':DREAM,'mode':'bm25','generate':False})
            self.assertEqual(response.status_code,200,response.text)
            result=response.json()
            self.assertEqual(set(result['matched_symbols']),{'سفر','سفينة','بحر','موج الماء'})
            self.assertEqual(len(result['sources']),6)
            self.assertTrue(all(s['review_scope']=='excerpt' for s in result['sources']))
            self.assertFalse(result['generation_available'])
            self.assertFalse(result['synthesis'])
            for source in result['sources']:
                parent=client.get('/api/passages/'+source['passage_id']).json()
                self.assertNotEqual(parent['validation_status'],'verified')
