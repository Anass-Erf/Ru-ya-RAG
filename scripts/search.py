"""Inspect real retrieval matches as JSON or a standalone Arabic HTML report."""
import argparse
import html
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from backend.app.rag.retrieval.index import SearchIndex
    from backend.app.rag.embeddings.minilm import MiniLM
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',required=True,type=Path)
    parser.add_argument('--query',required=True)
    parser.add_argument('--mode',choices=['bm25','dense','hybrid'],default='hybrid')
    parser.add_argument('--top-k',type=int,default=5)
    parser.add_argument('--book');parser.add_argument('--chapter')
    parser.add_argument('--html',type=Path)
    args=parser.parse_args()
    result=SearchIndex(args.index,MiniLM() if args.mode!='bm25' else None).search(args.query,mode=args.mode,top_k=args.top_k,book_id=args.book,chapter=args.chapter)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.html:
        cards=[]
        for hit in result['hits']:
            c=hit['chunk']; source=(ROOT/'data/raw'/c['source_file']).as_uri()+f"#page={c['page_start']}"
            cards.append(f'''<article><h2>{html.escape(c['symbol'] or c['section'] or c['chapter'] or '')}</h2>
<p>{html.escape(c['book_title'])} — {html.escape(c['author'])}</p>
<a href="{html.escape(source,quote=True)}">PDF {c['page_start']}–{c['page_end']}</a>
<p>status: {html.escape(c['validation_status'])} | rank score: {hit['score']:.6f} | BM25: {hit['bm25_score']} | cosine: {hit['dense_cosine']}</p>
<p>{html.escape(c['text'])}</p><details><summary>النص الخام وبيانات المصدر</summary><pre>{html.escape(c['raw_source_text'])}</pre><pre>{html.escape(json.dumps(c['source_ranges'],ensure_ascii=False,indent=2))}</pre></details></article>''')
        page=f'''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>فحص نتائج الاسترجاع</title>
<style>body{{background:#f6f3ec;color:#142c38;font:18px/1.8 system-ui;max-width:950px;margin:auto;padding:24px}}article{{background:white;padding:24px;margin:20px 0;border:1px solid #ccc;border-radius:12px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}p{{white-space:pre-wrap}}a{{color:#075b65}}</style>
<h1>فحص نتائج الاسترجاع</h1><p>{html.escape(args.query)}</p><p>corpus: {result['policy']} | mode: {result['mode']} | {result['latency_ms']:.2f} ms</p><p>درجات ترتيب وليست احتمالات ثقة. النصوص تفسيرات تاريخية وليست تنبؤات أو أحكامًا قطعية.</p>{''.join(cards) or '<p>لا توجد نتائج</p>'}</html>'''
        args.html.parent.mkdir(parents=True,exist_ok=True)
        args.html.write_text(page,encoding='utf-8')


if __name__=='__main__':main()
