'use client';
import { useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { api, type Book, type SearchResult, type Stats } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Empty, ErrorNotice, HitCard, Loading, Notice, PageIntro, useResource } from '@/components/shared';
import { number } from '@/lib/utils';
export default function SearchPage() {
  const books = useResource<Book[]>('/api/books');
  const stats = useResource<Stats>('/api/stats');
  const [query,setQuery] = useState(''); const [book,setBook] = useState(''); const [chapter,setChapter] = useState('');
  const [mode,setMode] = useState('hybrid'); const [experimental,setExperimental] = useState(false);
  const [result,setResult] = useState<SearchResult | null>(null); const [error,setError] = useState<Error | null>(null); const [busy,setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); controller.current?.abort(); const current = new AbortController(); controller.current = current;
    setBusy(true);setError(null);setResult(null);
    try { setResult(await api<SearchResult>('/api/search',{method:'POST',signal:current.signal,body:JSON.stringify({query,book_id:book || null,chapter:chapter.trim() || null,mode,policy:experimental ? 'experimental' : 'reviewed',top_k:10})})); }
    catch(e) { if(!current.signal.aborted)setError(e as Error); } finally { if(!current.signal.aborted)setBusy(false); }
  }
  return <><PageIntro eyebrow="عد إلى النص" title="البحث في المصادر" description="ابحث عن رمز أو عبارة، وقارن النص المسترجع بصفحته الأصلية. تُعرض النصوص المراجعة افتراضيا."/>
    <form onSubmit={submit} className="panel" aria-busy={busy}><label htmlFor="search-query">رمز أو كلمات البحث</label><div className="search-form"><input id="search-query" required minLength={2} maxLength={2000} value={query} onChange={e=>setQuery(e.target.value)} placeholder="ابحث عن رمز، مثل: يعسوب"/><Button disabled={busy || query.trim().length<2} type="submit"><Search/> {busy?'جارٍ البحث…':'بحث في المصادر'}</Button></div>
      <div className="filter-grid"><div><label htmlFor="book">الكتاب</label><select id="book" value={book} onChange={e=>setBook(e.target.value)}><option value="">كل الكتب المتاحة</option>{books.data?.map(b=><option key={b.id} value={b.id} disabled={b.status==='OCR_PENDING'}>{b.title}{b.status==='OCR_PENDING'?' — ينتظر OCR':''}</option>)}</select></div><div><label htmlFor="chapter">الفصل أو الباب (مطابقة العنوان كاملا)</label><input id="chapter" value={chapter} maxLength={500} onChange={e=>setChapter(e.target.value)} placeholder="انسخ عنوان الباب من نتيجة بحث"/></div><div><label htmlFor="search-mode">طريقة البحث</label><select id="search-mode" value={mode} onChange={e=>setMode(e.target.value)}><option value="hybrid">هجين</option><option value="bm25">كلمات · BM25</option><option value="dense">معنى · Dense</option></select></div></div>
      {stats.data?.experimental_search_enabled && <label className="check-label mt-5"><input type="checkbox" checked={experimental} onChange={e=>setExperimental(e.target.checked)}/>تضمين المجموعة التجريبية غير المراجعة — للاستكشاف فقط</label>}
      <p className="form-note">البحث بالكلمات حساس لصيغة الكلمة. جرّب «يعسوب» دون «الـ»، أو استخدم البحث الهجين. لا تُرسل هذه الصفحة نصك إلى مزود توليد.</p>
    </form>
    {books.error && <ErrorNotice error={books.error} retry={books.reload}/>}
    {experimental && <Notice>هذه مجموعة تجريبية تتضمن نصوصا غير مراجعة. لا تُعامل النتائج بوصفها شواهد موثقة، ولا تُستخدم للتوليد.</Notice>}
    <div className="results" aria-live="polite">{busy && <Loading label="جارٍ البحث في النصوص…"/>}{error && <ErrorNotice error={error}/>}
      {result ? <><div className="section-title"><h2>نتائج «{result.query}»</h2><span className="badge">{number(result.hits.length)} نتائج · {number(result.latency_ms)} مللي ثانية</span></div><p className="form-note">الطريقة المستخدمة: <bdi>{result.mode}</bdi> · درجات ترتيب وليست نسب ثقة. {result.policy==='experimental'?'مجموعة تجريبية.':'مجموعة مراجعة محدودة.'}</p>{result.warnings.length>0&&<Notice>{result.mode!==result.requested_mode?'النموذج الدلالي غير متاح؛ استُخدم البحث بالكلمات.':'تحتوي المجموعة التجريبية على نصوص لم تُراجع.'}</Notice>}{result.hits.length ? result.hits.map((h,i)=><HitCard key={h.chunk.id} hit={h} index={i}/>) : <Empty title="لم نجد نصوصا تطابق البحث">غيّر الكلمات أو أزل مرشّح الفصل أو الكتاب. لا تزال المكتبة قيد المراجعة.</Empty>}</> : !busy&&!error&&<Empty title="بين يديك، النص ومصدره">ابدأ بكلمة أو رمز. ستجد الاقتباس واسم الكتاب والمؤلف ورابط صفحة PDF هنا.</Empty>}
    </div></>;
}
