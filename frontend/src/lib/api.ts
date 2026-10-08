export const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(
  /\/$/,
  '',
);
export type Book = {
  id: string;
  title: string;
  author: string;
  status: string;
  source_available: boolean;
  pages_extracted: number;
  candidate_passages: number;
  verified_passages: number;
  verified_excerpts: number;
  reviewed_index_chunks: number;
  experimental_index_chunks: number;
  source_url: string;
};
export type Health = { ready: boolean; generation_configured: boolean; dense_model: string };
export type Chunk = {
  id: string;
  parent_entry_id: string;
  book_id: string;
  book_title: string;
  author: string;
  chapter: string | null;
  section: string | null;
  symbol: string | null;
  page_start: number;
  page_end: number;
  text: string;
  validation_status: string;
  review_flags: string[];
};
export type Hit = {
  chunk: Chunk;
  pdf_url: string;
  score: number;
  bm25_score: number | null;
  dense_cosine: number | null;
};
export type SearchResult = {
  query: string;
  mode: string;
  requested_mode: string;
  policy: string;
  hits: Hit[];
  latency_ms: number;
  warnings: string[];
  score_notice: string;
};
export type Source = {
  review_scope: 'full_passage' | 'excerpt';
  id: string;
  passage_id: string;
  book_title: string;
  author: string;
  symbol: string | null;
  page_start: number;
  page_end: number;
  pdf_url: string;
  quote: string;
  validation_status: string;
};
export type Citation = {
  source_id: string;
  quote: string;
  book_title: string;
  author: string;
  page_start: number;
  page_end: number;
  pdf_url: string;
};
export type Claim = { text: string; citations: Citation[] };
export type Interpretation = {
  status: 'retrieval_only' | 'insufficient_sources' | 'generated' | 'generation_failed';
  message: string;
  disclaimer: string;
  evidence_sufficient: boolean;
  matched_symbols: string[];
  generation_requested: boolean;
  generation_available: boolean;
  coverage_notice: string;
  retrieval: SearchResult;
  sources: Source[];
  synthesis: Claim[];
  differences: Claim[];
  generation_issue: { code: string; message: string; retryable: boolean } | null;
  provider_model: string | null;
};
export type Stats = {
  books: Book[];
  model_details: { name: string; revision: string; dimension: number; max_seq_length: number };
  searches_completed: number;
  mean_search_latency_ms: number | null;
  last_search_latency_ms: number | null;
  generation_enabled: boolean;
  experimental_search_enabled: boolean;
  warning: string;
};
export type Evaluation = {
  dataset_id: string;
  judgment_status: string;
  limitation: string;
  corpus_policy: string;
  aggregate: Record<
    string,
    {
      query_count: number;
      mean_latency_ms: number;
      at_k: Record<string, { recall: number; precision: number; reciprocal_rank: number }>;
    }
  >;
};
export type Ingestion = {
  books: Record<
    string,
    {
      candidate_passages: number;
      pages_extracted: number;
      passage_flag_counts: Record<string, number>;
      structural_warnings: string[];
    }
  >;
};
export type Passage = Chunk & {
  id: string;
  raw_text: string;
  source_file: string;
  extraction_method: string;
  source_ranges: { pdf_page: number; line_start: number; line_end: number }[];
};
const errorLabels: Record<string, string> = {
  corpus_unavailable: 'المجموعة النصية غير جاهزة حاليا. يرجى المحاولة بعد إعداد المصادر.',
  query_token_limit: 'الطلب أطول من حد البحث الدلالي. اختصره أو اختر البحث بالكلمات.',
  experimental_disabled: 'البحث في النصوص غير المراجعة غير مفعّل.',
  search_busy: 'البحث مشغول الآن. حاول بعد قليل.',
  invalid_request: 'تحقق من النص العربي وخيارات البحث ثم أعد المحاولة.',
  request_too_large: 'حجم الطلب أكبر من المسموح.',
};
export class APIError extends Error {
  constructor(
    message: string,
    public requestId?: string,
    public status?: number,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(90000);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  let response: Response;
  try {
    response = await fetch(API_URL + path, {
      ...init,
      signal,
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', ...init.headers },
    });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new APIError(
      timeout.aborted
        ? 'استغرق الاتصال وقتا طويلا. حاول مجددا.'
        : 'تعذر الاتصال بالخدمة. تحقق من تشغيل الخادم ثم أعد المحاولة.',
    );
  }
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new APIError(
      errorLabels[data?.error?.code] || 'تعذر إكمال الطلب. حاول مجددا.',
      data?.error?.request_id,
      response.status,
    );
  if (data === null) throw new APIError('وصلت استجابة غير صالحة من الخدمة.');
  return data as T;
}
export function pdfLink(path: string) {
  // Only catalog PDF links returned by this API may become navigable links.
  if (!/^\/api\/books\/(nabulsi|ibn-Shahin|ibn-sirin)\/source(?:#page=\d+)?$/.test(path))
    return '#';
  return API_URL + path;
}
