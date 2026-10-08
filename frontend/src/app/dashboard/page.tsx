'use client';
import { RefreshCw, Database, Activity } from 'lucide-react';
import { type Stats, type Evaluation, type Ingestion } from '@/lib/api';
import { number } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ErrorNotice, Loading, Notice, PageIntro, useResource } from '@/components/shared';
const qualityLabels: Record<string, string> = {
  chapter_preamble_review: 'مقدمة باب تحتاج إلى مراجعة',
  known_font_encoding_artifact: 'أثر لترميز الخط',
  long_page_span_review: 'مقطع يمتد عبر صفحات كثيرة',
  long_text_review: 'نص طويل يحتاج إلى مراجعة',
  nonmonotonic_arabic_glyph_order: 'ترتيب غير منتظم للمحارف العربية',
  unnamed_section: 'قسم بلا عنوان',
  low_text_page_in_span: 'صفحة قليلة النص داخل المقطع',
  short_text_review: 'نص قصير يحتاج إلى مراجعة',
  very_little_arabic: 'محتوى عربي قليل جدا',
};
export default function DashboardPage() {
  const stats = useResource<Stats>('/api/stats');
  const evaluation = useResource<Evaluation>('/api/evaluation/report');
  const ingestion = useResource<Ingestion>('/api/ingestion/report');
  const data = stats.data;
  const sum = (
    key: 'pages_extracted' | 'candidate_passages' | 'verified_passages' | 'reviewed_index_chunks',
  ) => data?.books.reduce((n, b) => n + b[key], 0) || 0;
  return (
    <>
      <PageIntro
        eyebrow="خلف كل نتيجة، بيانات"
        title="لوحة الجودة والأداء"
        description="مؤشرات فعلية من الخادم، دون أرقام تقديرية. افحص حجم المجموعة، حالة المراجعة، وحدود تقييم الاسترجاع."
      />
      <Button
        variant="outline"
        onClick={() => {
          stats.reload();
          evaluation.reload();
          ingestion.reload();
        }}
      >
        <RefreshCw /> تحديث المؤشرات
      </Button>
      {stats.loading && <Loading />}
      {stats.error && <ErrorNotice error={stats.error} retry={stats.reload} />}
      {data && (
        <>
          <div className="dashboard-grid">
            {[
              {
                label: 'صفحات فُحصت',
                value: sum('pages_extracted'),
                note: 'تشمل صفحات المصدر الممسوح',
              },
              {
                label: 'نصوص مرشحة',
                value: sum('candidate_passages'),
                note: 'ليست جميعها معتمدة للبحث',
              },
              {
                label: 'نصوص مراجعة',
                value: sum('verified_passages'),
                note: 'بمقارنة مساعدة آليا',
              },
              {
                label: 'مقاطع مفهرسة',
                value: sum('reviewed_index_chunks'),
                note: 'في المجموعة المراجعة فقط',
              },
            ].map((m) => (
              <div className="stat-card" key={m.label}>
                <span>{m.label}</span>
                <strong>{number(m.value)}</strong>
                <small>{m.note}</small>
              </div>
            ))}
          </div>
          <Notice>
            المجموعة المراجعة لا تزال صغيرة ({number(sum('verified_passages'))} نصوص كاملة، و
            {number(data.books.reduce((n, b) => n + b.verified_excerpts, 0))} مقتطفات مراجعة).
            الاختبار الحالي أولي، ولا يثبت جودة البحث على المكتبة كاملة.
          </Notice>
          <section className="panel">
            <div className="panel-heading">
              <h2>من الاستخراج إلى المراجعة</h2>
              <Database size={21} />
            </div>
            <div className="table-scroll">
              <table>
                <caption className="sr-only">أعداد النصوص حسب الكتاب</caption>
                <thead>
                  <tr>
                    <th scope="col">المصدر</th>
                    <th scope="col">مرشح</th>
                    <th scope="col">مراجع</th>
                    <th scope="col">غير معتمد بعد</th>
                    <th scope="col">مقاطع مراجعة</th>
                  </tr>
                </thead>
                <tbody>
                  {data.books.map((b) => (
                    <tr key={b.id}>
                      <th scope="row">{b.title}</th>
                      <td>{number(b.candidate_passages)}</td>
                      <td>{number(b.verified_passages)}</td>
                      <td>{number(b.candidate_passages - b.verified_passages)}</td>
                      <td>{number(b.reviewed_index_chunks)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="form-note">
              «غير معتمد بعد» يشمل غير المراجع والنصوص التي تحتاج إلى إصلاح. لا يدخل ابن سيرين إلى
              المقاطع قبل OCR والمراجعة.
            </p>
          </section>
          <div className="details-grid">
            <section className="panel">
              <div className="panel-heading">
                <h2>البحث في هذه الجلسة الخادمة</h2>
                <Activity size={21} />
              </div>
              <dl className="metadata">
                <dt>طلبات البحث المكتملة</dt>
                <dd>{number(data.searches_completed)}</dd>
                <dt>متوسط زمن الاسترجاع</dt>
                <dd>
                  {data.mean_search_latency_ms === null
                    ? 'لا توجد قياسات بعد'
                    : `${number(data.mean_search_latency_ms)} مللي ثانية`}
                </dd>
                <dt>آخر طلب</dt>
                <dd>
                  {data.last_search_latency_ms === null
                    ? 'لم يُنفذ بحث بعد'
                    : `${number(data.last_search_latency_ms)} مللي ثانية`}
                </dd>
                <dt>التوليد</dt>
                <dd>{data.generation_enabled ? 'مفعّل عند كفاية الشواهد' : 'غير مفعّل'}</dd>
                <dt>البحث التجريبي</dt>
                <dd>{data.experimental_search_enabled ? 'مفعّل' : 'غير مفعّل'}</dd>
              </dl>
              <p className="form-note">
                الزمن خاص بالاسترجاع، ويستثني تحميل النموذج والتوليد. العدادات تُصفّر عند إعادة
                تشغيل الخادم.
              </p>
            </section>
            <section className="panel">
              <h2 className="mb-5">نموذج التضمين</h2>
              <dl className="metadata">
                <dt>النموذج</dt>
                <dd>
                  <bdi>{data.model_details.name}</bdi>
                </dd>
                <dt>أبعاد المتجه</dt>
                <dd>{number(data.model_details.dimension)}</dd>
                <dt>حد تسلسل النموذج</dt>
                <dd>{number(data.model_details.max_seq_length)} رمزا</dd>
                <dt>مراجعة النموذج</dt>
                <dd className="text-xs">
                  <bdi>{data.model_details.revision}</bdi>
                </dd>
              </dl>
            </section>
          </div>
        </>
      )}
      <div className="section-title">
        <h2>تقييم الاسترجاع</h2>
        <span className="badge">اختبار أولي محدود</span>
      </div>
      {evaluation.loading && <Loading />}
      {evaluation.error && <ErrorNotice error={evaluation.error} retry={evaluation.reload} />}
      {evaluation.data && (
        <section className="panel">
          <p className="muted">
            أسئلة محدودة أُعدّت بمساعدة آلية على نصوص مراجعة. لا يُعد هذا تقييما بشريا مستقلا أو
            معيارا عاما لجودة التأويل.
          </p>
          <div className="table-scroll">
            <table>
              <caption className="sr-only">نتائج تقييم البحث في المجموعة المراجعة</caption>
              <thead>
                <tr>
                  <th scope="col">الطريقة</th>
                  <th scope="col">k</th>
                  <th scope="col">عدد الأسئلة</th>
                  <th scope="col">Recall@k</th>
                  <th scope="col">MRR@k</th>
                  <th scope="col">متوسط الزمن (ms)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(evaluation.data.aggregate).flatMap(([mode, metrics]) =>
                  Object.entries(metrics.at_k).map(([k, values]) => (
                    <tr key={mode + k}>
                      <th scope="row">
                        <bdi>{mode}</bdi>
                      </th>
                      <td>{number(Number(k))}</td>
                      <td>{number(metrics.query_count)}</td>
                      <td>{number(values.recall)}</td>
                      <td>{number(values.reciprocal_rank)}</td>
                      <td>{number(metrics.mean_latency_ms)}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
          <p className="form-note">
            Recall: نسبة النصوص ذات الصلة التي عُثر عليها. MRR: متوسط مقلوب رتبة أول نص ذي صلة.
            القياسات للاسترجاع، وليست دقة للتوليد.
          </p>
          <details>
            <summary>بيانات التقييم الأصلية وحدودها</summary>
            <pre dir="ltr" className="raw-text text-xs">
              {JSON.stringify(evaluation.data, null, 2)}
            </pre>
          </details>
        </section>
      )}
      <div className="section-title">
        <h2>تقرير الاستخراج والجودة</h2>
      </div>
      {ingestion.loading && <Loading />}
      {ingestion.error && <ErrorNotice error={ingestion.error} retry={ingestion.reload} />}
      {ingestion.data && (
        <section className="panel">
          <p className="muted">
            التقرير الأصلي يحتفظ بتشخيصات الاستخراج والتنبيهات لكل مصدر. هذه مؤشرات مراجعة، وليست
            نسب ثقة.
          </p>
          <div className="table-scroll">
            <table>
              <caption className="sr-only">تنبيهات جودة المقاطع المستخرجة</caption>
              <thead>
                <tr>
                  <th scope="col">المصدر</th>
                  <th scope="col">تشخيص الجودة</th>
                  <th scope="col">عدد المقاطع</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(ingestion.data.books).flatMap(([id, book]) =>
                  Object.entries(book.passage_flag_counts).map(([flag, count]) => (
                    <tr key={id + flag}>
                      <th scope="row">{data?.books.find((b) => b.id === id)?.title || id}</th>
                      <td>{qualityLabels[flag] || flag}</td>
                      <td>{number(count)}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
          <p className="form-note">
            قد يحمل المقطع أكثر من تنبيه؛ لا تجمع هذه الأعداد بوصفها نصوصا منفصلة. التقرير هنا يصف
            مرحلة الاستخراج قبل قرارات المراجعة اللاحقة.
          </p>
          <details>
            <summary>عرض التقرير الفعلي كاملا</summary>
            <pre dir="ltr" className="raw-text text-xs">
              {JSON.stringify(ingestion.data, null, 2)}
            </pre>
          </details>
        </section>
      )}
    </>
  );
}
