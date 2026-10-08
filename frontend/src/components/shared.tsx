'use client';
import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ArrowUpLeft, LoaderCircle, BookOpen, RefreshCw } from 'lucide-react';
import { api, APIError, pdfLink, type Hit, type Passage } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { number } from '@/lib/utils';
export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [version, setVersion] = useState(0);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setData(null);
    api<T>(path, { signal: controller.signal })
      .then(setData)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, version]);
  return { data, error, loading, reload };
}
export function PageIntro({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="page-intro">
      <div className="eyebrow">
        <span />
        {eyebrow}
      </div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  );
}
export function ErrorNotice({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div role="alert" className="notice error">
      <AlertCircle size={20} />
      <div>
        <strong>{error.message}</strong>
        {error instanceof APIError && error.requestId && (
          <small>
            معرّف الطلب: <bdi>{error.requestId}</bdi>
          </small>
        )}
        {retry && (
          <Button variant="outline" size="sm" onClick={retry}>
            <RefreshCw /> إعادة المحاولة
          </Button>
        )}
      </div>
    </div>
  );
}
export function Loading({ label = 'جارٍ تحميل البيانات من المصدر…' }: { label?: string }) {
  return (
    <div role="status" className="loading">
      <LoaderCircle className="spinner" size={22} />
      {label}
    </div>
  );
}
export function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="notice">
      <AlertCircle size={18} />
      <div>{children}</div>
    </div>
  );
}
export function PdfAnchor({ url, start, end }: { url: string; start: number; end?: number }) {
  return (
    <a className="source-link" href={pdfLink(url)} target="_blank" rel="noopener noreferrer">
      صفحة PDF {number(start)}
      {end && end !== start ? `–${number(end)}` : ''}
      <ArrowUpLeft size={15} />
      <span className="sr-only"> (يفتح في نافذة جديدة)</span>
    </a>
  );
}
export function ReviewBadge({ status }: { status: string }) {
  return (
    <span className={`badge ${status === 'verified' ? 'verified' : 'pending'}`}>
      {status === 'verified'
        ? 'مراجعة بمساعدة آلية'
        : status === 'needs_review'
          ? 'يحتاج إلى مراجعة'
          : 'غير مُراجع'}
    </span>
  );
}
export function PassagePreview({ id }: { id: string }) {
  const [show, setShow] = useState(false);
  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setShow(!show)} aria-expanded={show}>
        {show ? 'إخفاء النص الكامل' : 'عرض النص الأصلي وبياناته'}
      </Button>
      {show && <PassageBody id={id} />}
    </>
  );
}
function PassageBody({ id }: { id: string }) {
  const { data, error, loading, reload } = useResource<Passage>(
    '/api/passages/' + encodeURIComponent(id),
  );
  if (loading) return <Loading />;
  if (error) return <ErrorNotice error={error} retry={reload} />;
  if (!data) return null;
  return (
    <div className="passage-body">
      <ReviewBadge status={data.validation_status} />
      <blockquote>{data.text}</blockquote>
      <details>
        <summary>النص الخام ومواضع الاستخراج</summary>
        <pre className="raw-text">{data.raw_text}</pre>
        <p className="muted">
          <bdi>{data.source_file}</bdi> · <bdi>{data.extraction_method}</bdi>
        </p>
        <ul>
          {data.source_ranges.map((r, i) => (
            <li key={i}>
              صفحة {number(r.pdf_page)} · سطور {number(r.line_start)}–{number(r.line_end)}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
export function HitCard({ hit, index }: { hit: Hit; index: number }) {
  const c = hit.chunk;
  return (
    <article className="hit-card">
      <div className="hit-header">
        <span className="result-number">{number(index + 1).padStart(2, '٠')}</span>
        <div>
          <h3>{c.symbol || c.section || 'مقطع من المصدر'}</h3>
          <p>
            {c.book_title} · {c.author}
          </p>
        </div>
        <ReviewBadge status={c.validation_status} />
      </div>
      {c.chapter && <p className="chapter-label">{c.chapter}</p>}
      <blockquote>{c.text}</blockquote>
      <div className="hit-footer">
        <PdfAnchor url={hit.pdf_url} start={c.page_start} end={c.page_end} />
        <span>
          درجة الترتيب <bdi>{hit.score.toFixed(4)}</bdi> · ليست ثقة
        </span>
      </div>
      <PassagePreview id={c.parent_entry_id} />
    </article>
  );
}
export function Empty({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="empty">
      <BookOpen size={30} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
