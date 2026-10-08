'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowUpLeft, BookOpen, Feather, ShieldCheck, Sparkles } from 'lucide-react';
import { api, type Interpretation, type Health, type Stats, type Claim } from '@/lib/api';
import { number } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Empty,
  ErrorNotice,
  HitCard,
  Loading,
  Notice,
  PageIntro,
  PassagePreview,
  PdfAnchor,
  ReviewBadge,
  useResource,
} from '@/components/shared';
function Claims({ claims }: { claims: Claim[] }) {
  return claims.map((claim, i) => (
    <article className="synthesis" key={i}>
      <p>{claim.text}</p>
      <details>
        <summary>الشواهد التي يستند إليها هذا التلخيص</summary>
        {claim.citations.map((c, j) => (
          <div className="source-excerpt" key={j}>
            <h3>{c.book_title}</h3>
            <p>{c.author}</p>
            <blockquote>{c.quote}</blockquote>
            <PdfAnchor url={c.pdf_url} start={c.page_start} end={c.page_end} />
          </div>
        ))}
      </details>
    </article>
  ));
}
export default function InterpretationPage() {
  const health = useResource<Health>('/health');
  const stats = useResource<Stats>('/api/stats');
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [generate, setGenerate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [result, setResult] = useState<Interpretation | null>(null);
  const controller = useRef<AbortController | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await api<Interpretation>('/api/interpret', {
        method: 'POST',
        signal: current.signal,
        body: JSON.stringify({
          query,
          mode,
          generate: generate && Boolean(health.data?.generation_configured),
        }),
      });
      setResult(response);
      requestAnimationFrame(() => resultRef.current?.focus());
    } catch (e) {
      if (!current.signal.aborted) setError(e as Error);
    } finally {
      if (!current.signal.aborted) setBusy(false);
    }
  }
  const reviewed = stats.data?.books.reduce((n, b) => n + b.verified_passages, 0);
  return (
    <>
      <div className="hero">
        <PageIntro
          eyebrow="بين الرؤيا والنص"
          title="لكل قراءةٍ، شاهد."
          description="استكشف ما ورد في كتب تعبير الرؤى، واقرأ المعنى إلى جانب مصدره. معرفة تاريخية موثّقة، لا تنبؤ بالمستقبل."
        />
        <div className="hero-decoration" aria-hidden="true">
          <Feather size={31} />
        </div>
      </div>
      <div className="two-columns">
        <div>
          <section className="panel">
            <div className="panel-heading">
              <h2>ماذا رأيت في رؤياك؟</h2>
              <span className="step-label">ابدأ من هنا</span>
            </div>
            <form onSubmit={submit} aria-busy={busy}>
              <label htmlFor="dream">اكتب رؤياك أو الرمز الذي تبحث عنه</label>
              <textarea
                id="dream"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setResult(null);
                }}
                required
                minLength={2}
                maxLength={2000}
                placeholder="رأيت في المنام…"
                aria-describedby="dream-help"
              />
              <p id="dream-help" className="form-note">
                اكتب وصفا موجزا بالعربية، وتجنّب الأسماء والمعلومات الشخصية.
              </p>
              <div className="examples">
                <span>جرّب رمزا من النصوص المراجعة:</span>
                {['يعسوب', 'ذل'].map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="example-chip"
                    onClick={() => {
                      setQuery(s);
                      setResult(null);
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <details>
                <summary>خيارات القراءة</summary>
                <label htmlFor="mode">طريقة البحث</label>
                <select id="mode" value={mode} onChange={(e) => setMode(e.target.value)}>
                  <option value="hybrid">بحث هجين · بالكلمات والمعنى</option>
                  <option value="bm25">بحث بالكلمات · BM25</option>
                  <option value="dense">بحث بالمعنى · Dense</option>
                </select>
              </details>
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={generate}
                  disabled={!health.data?.generation_configured}
                  onChange={(e) => setGenerate(e.target.checked)}
                />
                إضافة تلخيص بالذكاء الاصطناعي
              </label>
              <p className="form-note">
                {health.data?.generation_configured
                  ? 'عند التفعيل، يُرسل النص والشواهد المختارة إلى DeepSeek. لا يُولّد التلخيص دون شواهد مؤهلة.'
                  : 'التلخيص الآلي غير متاح حاليا؛ يمكنك قراءة الشواهد مباشرة.'}
              </p>
              <div className="form-actions">
                <Button type="submit" disabled={busy || query.trim().length < 2}>
                  {busy ? 'جارٍ البحث…' : 'ابحث عن الشواهد'}
                  {!busy && <ArrowLeft />}
                </Button>
                <span className="char-count" aria-live="off">
                  {number(query.length)} / {number(2000)} حرف
                </span>
              </div>
            </form>
          </section>
          {stats.data && (
            <div className="metric-strip">
              <div>
                <strong>{number(stats.data.books.length)}</strong>
                <span>
                  كتب في المكتبة
                  <br />
                  بدرجات جاهزية مختلفة
                </span>
              </div>
              <div>
                <strong>{number(reviewed || 0)}</strong>
                <span>
                  نصوص مراجعة
                  <br />
                  بمساعدة آلية
                </span>
              </div>
              <div>
                <ShieldCheck size={23} className="text-primary" />
                <span>
                  الاقتباس الأصلي
                  <br />
                  مع كل شاهد مؤهل
                </span>
              </div>
            </div>
          )}
          {health.error && <ErrorNotice error={health.error} retry={health.reload} />}
          {health.data && !health.data.ready && (
            <Notice>المصادر غير جاهزة للبحث حاليا. يمكنك تصفح صفحة المنهج إلى حين إعدادها.</Notice>
          )}
          <Notice>
            المجموعة المراجعة محدودة{reviewed !== undefined ? ` (${number(reviewed)} نصوص)` : ''}؛
            قد لا نجد شاهدا مناسبا لرؤياك. المراجعة الآلية ليست تحقيقا علميا بشريا.
          </Notice>
        </div>
        <aside className="aside-stack" aria-label="دليل القراءة">
          <section className="panel aside-panel">
            <h2>كيف نقرأ الرؤيا؟</h2>
            <p>خطوات واضحة، من سؤالك إلى النص الذي يمكن الرجوع إليه.</p>
            <ol className="workflow">
              <li>
                <span className="workflow-num">١</span>
                <div>
                  <b>نبحث في المصادر</b>
                  <small>نسترجع النصوص الأقرب إلى طلبك.</small>
                </div>
              </li>
              <li>
                <span className="workflow-num">٢</span>
                <div>
                  <b>نُظهر الشاهد</b>
                  <small>الكتاب والمؤلف وصفحة المصدر.</small>
                </div>
              </li>
              <li>
                <span className="workflow-num">٣</span>
                <div>
                  <b>نوضح حدود القراءة</b>
                  <small>نصرّح حين لا تكفي الشواهد.</small>
                </div>
              </li>
            </ol>
            <Link href="/about" className="text-link">
              اقرأ عن المنهج <ArrowUpLeft size={15} />
            </Link>
          </section>
          <section className="panel aside-panel quote-panel">
            <BookOpen size={25} className="large-icon" />
            <p className="serif">
              الشاهد قبل التأويل،
              <br />
              والمصدر قبل النتيجة.
            </p>
            <p className="mt-3">النصوص هنا تراث تاريخي، وليست حقائق أو أحكاما قطعية.</p>
          </section>
        </aside>
      </div>
      <div
        ref={resultRef}
        tabIndex={-1}
        role="region"
        className="results"
        aria-label="نتيجة القراءة"
      >
        {busy && (
          <Loading label="نبحث في المصادر ونراجع الشواهد… قد يستغرق تحميل النموذج أول مرة بعض الوقت." />
        )}
        {error && <ErrorNotice error={error} />}
        {result && (
          <>
            <div className="section-title">
              <h2>
                {result.status === 'generated'
                  ? 'قراءة تستند إلى الشواهد'
                  : 'نتيجة البحث عن الشواهد'}
              </h2>
              <span className="badge">
                {result.status === 'generated' ? 'تلخيص آلي' : 'من المصادر'}
              </span>
            </div>
            <p className="muted">{result.message}</p>
            <p className="form-note">الطلب: {result.retrieval.query}</p>
            {result.generation_issue && (
              <Notice>{result.generation_issue.message} الشواهد أدناه متاحة للقراءة.</Notice>
            )}
            {result.synthesis.length > 0 && (
              <section aria-label="التلخيص الآلي">
                <h3 className="flex items-center gap-2">
                  <Sparkles size={17} /> تلخيص مولّد · منفصل عن النص الأصلي
                </h3>
                <Claims claims={result.synthesis} />
              </section>
            )}
            {result.differences.length > 0 && (
              <section>
                <h3>اختلافات بين الشواهد</h3>
                <Claims claims={result.differences} />
              </section>
            )}
            {result.sources.length > 0 ? (
              <section>
                <h2 className="mt-6">الشواهد الأصلية</h2>
                {result.sources.map((s) => (
                  <article key={s.id} className="hit-card">
                    <div className="panel-heading">
                      <h3>{s.book_title}</h3>
                      <ReviewBadge status={s.validation_status} />
                    </div>
                    <p className="muted">
                      {s.author} · {s.symbol}
                    </p>
                    <details open>
                      <summary>الاقتباس الأصلي</summary>
                      <blockquote>{s.quote}</blockquote>
                    </details>
                    <PdfAnchor url={s.pdf_url} start={s.page_start} end={s.page_end} />
                    <div>
                      <PassagePreview id={s.passage_id} />
                    </div>
                  </article>
                ))}
              </section>
            ) : (
              <Empty title="لا تتوفر شواهد كافية">
                جرّب رمزا محددا أو اطلع على المكتبة لمعرفة النصوص المتاحة. غياب الشاهد لا يحمل معنى
                تأويليا.
              </Empty>
            )}
            <details className="panel mt-5">
              <summary>فحص نتائج الاسترجاع ({number(result.retrieval.hits.length)})</summary>
              <p className="form-note">
                الترتيب يقيس صلة النص بالطلب، ولا يقيس صحة التأويل. ظهور نتيجة لا يعني أنها تكفي
                للإجابة.
              </p>
              {result.retrieval.warnings.length > 0 && (
                <Notice>
                  استخدم البحث بديلا متاحا أو مجموعة محدودة؛ راجع طريقة البحث الفعلية:{' '}
                  <bdi>{result.retrieval.mode}</bdi>.
                </Notice>
              )}
              {result.retrieval.hits.map((h, i) => (
                <HitCard key={h.chunk.id} hit={h} index={i} />
              ))}
            </details>
            <Notice>{result.disclaimer}</Notice>
          </>
        )}
      </div>
    </>
  );
}
