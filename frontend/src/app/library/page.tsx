'use client';
import { BookOpen, ArrowUpLeft } from 'lucide-react';
import { pdfLink, type Book } from '@/lib/api';
import { number } from '@/lib/utils';
import { ErrorNotice, Loading, Notice, PageIntro, useResource } from '@/components/shared';
const status: Record<string, string> = {
  partially_available: 'متاح جزئيا',
  processing: 'قيد المراجعة',
  OCR_PENDING: 'بانتظار استخراج بصري · OCR',
  not_ingested: 'لم يُستخرج بعد',
};
export default function LibraryPage() {
  const { data, error, loading, reload } = useResource<Book[]>('/api/books');
  return (
    <>
      <PageIntro
        eyebrow="المكتبة الرقمية"
        title="ثلاثة مصادر، وقراءة متأنّية."
        description="كتب تاريخية في تعبير الرؤى. نُظهر حالة كل مصدر كما هي؛ وجود الكتاب لا يعني اكتمال مراجعته أو جاهزيته للبحث."
      />
      {loading && <Loading />}
      {error && <ErrorNotice error={error} retry={reload} />}
      {data && (
        <div className="book-grid">
          {data.map((b) => (
            <article className="book-card" key={b.id}>
              <div
                className={`book-cover ${b.id === 'ibn-Shahin' ? 'shahin' : b.id === 'ibn-sirin' ? 'sirin' : ''}`}
              >
                <div className="book-cover-inner">
                  <BookOpen size={23} />
                  <h2>{b.title}</h2>
                  <small>{b.author}</small>
                </div>
              </div>
              <div className="book-content">
                <span
                  className={`badge ${b.status === 'partially_available' ? 'verified' : 'pending'}`}
                >
                  {status[b.status] || b.status}
                </span>
                <p>
                  {b.id === 'ibn-sirin'
                    ? 'نسبة الكتاب إلى ابن سيرين غير مؤكدة. النسخة ممسوحة ضوئيا وتحتاج إلى OCR ومراجعة.'
                    : b.verified_passages
                      ? 'المتاح للبحث المراجع جزء محدود من الكتاب، بمراجعة مساعدة آليا.'
                      : 'استُخرجت نصوص مرشحة، ولم تُعتمد بعد للمجموعة المراجعة.'}
                </p>
                <div className="book-stats">
                  <div>
                    <b>{number(b.candidate_passages)}</b>
                    <span>نصوص مرشحة</span>
                  </div>
                  <div>
                    <b>{number(b.verified_passages)}</b>
                    <span>نصوص مراجعة</span>
                  </div>
                </div>
                <p>
                  {number(b.pages_extracted)} صفحة فُحصت · {number(b.reviewed_index_chunks)} مقاطع
                  في الفهرس المراجع
                </p>
                {b.source_available ? (
                  <a
                    href={pdfLink(b.source_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-link"
                  >
                    تصفّح النسخة الأصلية <ArrowUpLeft size={16} />
                    <span className="sr-only"> (نافذة جديدة)</span>
                  </a>
                ) : (
                  <span className="muted">ملف المصدر غير متاح</span>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
      <Notice>
        حالة «مراجعة» تشير إلى مقارنة بالنص الأصلي بمساعدة آلية، ولا تعني تحقيقا بشريا مستقلا أو صحة
        التأويل. أرقام الصفحات تحيل إلى ترتيب صفحات PDF.
      </Notice>
    </>
  );
}
