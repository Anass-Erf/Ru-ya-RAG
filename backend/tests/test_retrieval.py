import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
from backend.app.rag.chunking.core import chunk_passage, exclusion_reason
from backend.app.rag.embeddings.minilm import MiniLM
from backend.app.rag.retrieval.index import read_corpus, SearchIndex, build_index
from backend.app.rag.retrieval.lexical import BM25, rrf, tokens
from backend.app.rag.evaluation.metrics import metrics

ROOT=Path(__file__).resolve().parents[2]


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoder=MiniLM()
        cls.passages,cls.rows,_=read_corpus(ROOT)
        cls.verified=[p for p in cls.passages if p.validation_status=='verified']
        cls.chunks=[c for p in cls.verified for c in chunk_passage(p,cls.encoder.tokenizer,cls.rows)]
        cls.temporary=tempfile.TemporaryDirectory()
        cls.path,_=build_index(ROOT,Path(cls.temporary.name),cls.encoder)
        cls.index=SearchIndex(cls.path,cls.encoder)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def test_policy_excludes_unreviewed_and_broken_records(self):
        p=self.verified[0]
        self.assertIsNone(exclusion_reason(p,'reviewed'))
        self.assertEqual(exclusion_reason(p.model_copy(update={'validation_status':'unreviewed','validated_text':None}),'reviewed'),'not_verified')
        self.assertTrue(exclusion_reason(p.model_copy(update={'review_flags':['replacement_character']}),'experimental'))
        self.assertEqual(exclusion_reason(p.model_copy(update={'book_id':'ibn-sirin'}),'experimental'),'OCR_PENDING')

    def test_short_entries_keep_source_and_stable_ids(self):
        chunks=chunk_passage(self.verified[0],self.encoder.tokenizer,self.rows)
        self.assertEqual(chunks,chunk_passage(self.verified[0],self.encoder.tokenizer,self.rows))
        self.assertEqual(len(chunks),1)
        self.assertEqual(chunks[0].text,self.verified[0].text)
        self.assertEqual(chunks[0].page_start,self.verified[0].page_start)
        self.assertEqual(chunks[0].parent_entry_id,self.verified[0].id)

    def test_long_cross_page_passage_is_not_truncated(self):
        # Override quality only inside this test to exercise a long actual source.
        # No such record is published as verified or admitted to the real corpus.
        source=max(self.passages,key=lambda p:len(p.text))
        p=source.model_copy(update={'validation_status':'verified','validated_text':source.text,'review_flags':[]})
        chunks=chunk_passage(p,self.encoder.tokenizer,self.rows)
        self.assertGreater(len(chunks),10)
        self.assertEqual(chunks[0].char_start,0)
        self.assertEqual(chunks[-1].char_end,len(p.text))
        self.assertEqual(chunks[-1].page_end,p.page_end)
        for i,c in enumerate(chunks):
            self.assertEqual(c.text,p.text[c.char_start:c.char_end])
            self.assertLessEqual(c.token_count,120)
            self.assertEqual(c.book_id,p.book_id)
            self.assertEqual(c.parent_entry_id,p.id)
            if i:self.assertLessEqual(c.char_start,chunks[i-1].char_end)

    def test_no_cross_book_combination(self):
        other = next(p for p in self.passages if p.book_id == 'ibn-Shahin' and exclusion_reason(p, 'experimental') is None)
        combined = self.chunks + chunk_passage(other, self.encoder.tokenizer, self.rows, policy='experimental')
        self.assertEqual({c.book_id for c in combined}, {'nabulsi', 'ibn-Shahin'})
        parents = {p.id:p for p in [*self.verified, other]}
        for c in combined:
            p = parents[c.parent_entry_id]
            self.assertEqual(c.book_id, p.book_id)
            self.assertEqual(c.source_sha256, p.source_sha256)
            self.assertEqual(c.symbol, p.symbol)

    def test_bad_provenance_and_chunk_settings_fail(self):
        with self.assertRaises(ValueError):chunk_passage(self.verified[0],self.encoder.tokenizer,self.rows,overlap_tokens=120)
        with self.assertRaises(ValueError):chunk_passage(self.verified[0].model_copy(update={'text':self.verified[0].text + ' إضافة غير أصلية'}),self.encoder.tokenizer,self.rows)
        with self.assertRaises(ValueError):build_index(ROOT,Path(self.temporary.name),self.encoder,max_tokens=1000)

    def test_arabic_lexical_normalization(self):
        self.assertEqual(tokens('إِبْرَاهِيم'),tokens('ابراهيم'))
        results=BM25(self.chunks).search('يعسوب')
        self.assertEqual(self.chunks[results[0][0]].symbol,'يعسوب')
        self.assertEqual(BM25(self.chunks).search('كلمةمعدومة'),[])

    def test_rrf_combines_ranks_not_score_scales(self):
        actual=rrf([[(0,10000),(1,1)],[(1,.9),(2,.8)]])
        self.assertEqual(actual[0][0],1)
        self.assertAlmostEqual(actual[0][1],1/62+1/61)

    def test_dense_index_vectors_and_real_retrieval(self):
        vectors=self.encoder.encode([c.text for c in self.chunks])
        self.assertEqual(vectors.shape,(len(self.chunks),384))
        self.assertTrue(np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5))
        hits=self.index.search('يعسوب',mode='hybrid',top_k=1)['hits']
        self.assertEqual(hits[0]['chunk']['symbol'],'يعسوب')
        self.assertIsNotNone(hits[0]['dense_cosine'])

    def test_filters_no_results_and_input_validation(self):
        for mode in ['bm25','dense','hybrid']:
            self.assertEqual(self.index.search('يعسوب',mode=mode,book_id='ibn-sirin')['hits'],[])
        with self.assertRaises(ValueError):self.index.search(' ')
        with self.assertRaises(ValueError):self.index.search('رؤيا',top_k=0)
        with self.assertRaises(ValueError):self.encoder.encode(['كلمة '*1000])

    def test_bm25_operates_without_embedder(self):
        index=SearchIndex(self.path)
        self.assertTrue(index.search('يعسوب',mode='bm25')['hits'])
        with self.assertRaises(ValueError):index.search('يعسوب',mode='dense')

    def test_model_revision_compatibility(self):
        class WrongModel:
            identity={**self.encoder.identity,'revision':'different'}
        with self.assertRaisesRegex(ValueError,'metadata mismatch'):SearchIndex(self.path,WrongModel())

    def test_index_tampering_detected_and_rebuild_reuses(self):
        self.assertEqual(build_index(ROOT,Path(self.temporary.name),self.encoder),(self.path,True))
        with tempfile.TemporaryDirectory() as folder:
            copied=Path(folder)/'index';shutil.copytree(self.path,copied)
            (copied/'chunks.jsonl').write_text('corrupt')
            with self.assertRaisesRegex(ValueError,'checksum'):SearchIndex(copied)

    def test_metrics_use_unique_passages_and_fixed_k(self):
        result=metrics(['a','a','b'],['b'],2)
        self.assertEqual(result,{'recall':1,'precision':.5,'reciprocal_rank':.5})
        self.assertEqual(metrics([],['b'],5),{'recall':0,'precision':0,'reciprocal_rank':0})
