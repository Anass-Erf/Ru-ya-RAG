import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const apiUrl = `http://127.0.0.1:${Number(process.env.RUYA_E2E_API_PORT ?? 18000)}`;

test('reviewed interpretation, parent passage, and real PDF citation', async ({
  page,
  request,
}) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await page.getByLabel('اكتب رؤياك أو الرمز الذي تبحث عنه').fill('يعسوب');
  await page.getByText('خيارات القراءة', { exact: true }).click();
  await page.getByLabel('طريقة البحث', { exact: true }).selectOption('bm25');
  await page.getByRole('button', { name: 'ابحث عن الشواهد' }).click();
  await expect(page.getByRole('heading', { name: 'الشواهد الأصلية' })).toBeVisible();
  const pdf = page.getByRole('link', { name: /صفحة PDF/ }).first();
  await expect(pdf).toHaveAttribute('href', `${apiUrl}/api/books/nabulsi/source#page=1405`);
  const response = await request.get((await pdf.getAttribute('href'))!, {
    headers: { Range: 'bytes=0-7' },
  });
  expect(response.status()).toBe(206);
  expect((await response.body()).toString().startsWith('%PDF')).toBeTruthy();
  await page.getByRole('button', { name: 'عرض النص الأصلي وبياناته' }).first().click();
  await expect(page.getByText('النص الخام ومواضع الاستخراج')).toBeVisible();
  await expect(page.getByRole('checkbox')).toBeDisabled();
});

test('search filters and honest empty results', async ({ page }) => {
  await page.goto('/search');
  await page.getByLabel('رمز أو كلمات البحث').fill('يعسوب');
  await page.getByLabel('طريقة البحث').selectOption('bm25');
  await page.getByRole('button', { name: 'بحث في المصادر' }).click();
  await expect(page.locator('.hit-card')).toHaveCount(1);
  await page.getByLabel('الكتاب', { exact: true }).selectOption('ibn-Shahin');
  await page.getByRole('button', { name: 'بحث في المصادر' }).click();
  await expect(page.getByRole('heading', { name: 'لم نجد نصوصا تطابق البحث' })).toBeVisible();
  await page.getByLabel('الكتاب', { exact: true }).selectOption('');
  await page.getByLabel(/الفصل أو الباب/).fill('عنوان غير موجود');
  await page.getByRole('button', { name: 'بحث في المصادر' }).click();
  await expect(page.locator('.hit-card')).toHaveCount(0);
});

test('reviewed Ibn Shahin section appears with its original PDF citation', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('اكتب رؤياك أو الرمز الذي تبحث عنه').fill('رأيت السراب في المنام');
  await page.getByText('خيارات القراءة', { exact: true }).click();
  await page.getByLabel('طريقة البحث', { exact: true }).selectOption('bm25');
  await page.getByRole('button', { name: 'ابحث عن الشواهد' }).click();
  await expect(page.getByRole('heading', { name: 'الشواهد الأصلية' })).toBeVisible();
  await expect(page.getByText(/الرموز المطابقة:/)).toContainText('السراب');
  await expect(page.getByRole('link', { name: /صفحة PDF/ }).first()).toHaveAttribute(
    'href',
    `${apiUrl}/api/books/ibn-Shahin/source#page=22`,
  );
  await expect(page.locator('.synthesis')).toHaveCount(0);
});

test('unrelated dream abstains without synthesis', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('اكتب رؤياك أو الرمز الذي تبحث عنه').fill('كلمةمعدومة');
  await page.getByText('خيارات القراءة', { exact: true }).click();
  await page.getByLabel('طريقة البحث', { exact: true }).selectOption('bm25');
  await page.getByRole('button', { name: 'ابحث عن الشواهد' }).click();
  await expect(page.getByRole('heading', { name: 'لا تتوفر شواهد كافية' })).toBeVisible();
  await expect(page.locator('.synthesis')).toHaveCount(0);
});

test('real library statuses and dashboard metrics match backend', async ({ page, request }) => {
  const stats = await (await request.get(`${apiUrl}/api/stats`)).json();
  await page.goto('/library');
  await expect(page.locator('.book-card')).toHaveCount(stats.books.length);
  await expect(page.getByText('بانتظار استخراج بصري · OCR', { exact: true })).toBeVisible();
  await expect(page.getByText('متاح جزئيا', { exact: true })).toHaveCount(
    stats.books.filter((book: { status: string }) => book.status === 'partially_available').length,
  );
  for (const book of stats.books) {
    const card = page
      .locator('.book-card')
      .filter({ has: page.getByRole('heading', { name: book.title }) });
    await expect(card.locator('.book-stats b').nth(1)).toHaveText(
      new Intl.NumberFormat('ar').format(book.verified_passages),
    );
  }
  await page.goto('/dashboard');
  await expect(page.locator('.stat-card')).toHaveCount(4);
  const verified = stats.books.reduce(
    (n: number, b: { verified_passages: number }) => n + b.verified_passages,
    0,
  );
  await expect(
    page.locator('.stat-card').filter({ hasText: 'نصوص مراجعة' }).locator('strong'),
  ).toHaveText(new Intl.NumberFormat('ar').format(verified));
  await expect(page.getByRole('columnheader', { name: 'Recall@k' })).toBeVisible();
  await expect(
    page.getByText('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', { exact: true }),
  ).toBeVisible();
});

test('offline error and retry; no fabricated books', async ({ page }) => {
  await page.route('**/api/books', (route) => route.abort());
  await page.goto('/library');
  await expect(page.locator('.notice[role=alert]')).toContainText('تعذر الاتصال بالخدمة');
  await expect(page.locator('.book-card')).toHaveCount(0);
  await page.unroute('**/api/books');
  await page.getByRole('button', { name: 'إعادة المحاولة' }).click();
  await expect(page.locator('.book-card')).toHaveCount(3);
});

test('mobile navigation, dark preference, overflow, and screenshots', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'فتح القائمة' }).click();
  await page.getByRole('link', { name: /المكتبة الرقمية/ }).click();
  await expect(page.locator('.book-card')).toHaveCount(3);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
  await page.getByRole('button', { name: 'تفعيل الوضع الداكن' }).click();
  await page.reload();
  await expect(page.locator('html')).toHaveClass('dark');
  await page.screenshot({ path: 'test-results/library-mobile-dark.png', fullPage: true });
  await page.getByRole('button', { name: 'تفعيل الوضع الفاتح' }).click();
  await page.goto('/');
  await page.screenshot({ path: 'test-results/home-mobile.png', fullPage: true });
});

test('desktop accessibility across all pages and light/dark contrast', async ({ page }) => {
  await page.goto('/');
  expect(
    await page
      .locator('.sidebar-bottom')
      .evaluate((el) => el.getBoundingClientRect().bottom <= window.innerHeight),
  ).toBeTruthy();
  await page.setViewportSize({ width: 1280, height: 900 });
  for (const path of ['/', '/search', '/library', '/dashboard', '/about']) {
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBeTruthy();
  }
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'test-results/home-desktop.png', fullPage: true });
  await page.getByRole('button', { name: 'تفعيل الوضع الداكن' }).click();
  const dark = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(dark.violations, JSON.stringify(dark.violations, null, 2)).toEqual([]);
  await page.screenshot({ path: 'test-results/home-desktop-dark.png', fullPage: true });
});

test('clearly labeled test fixture checks synthesis separation and failure recovery', async ({
  page,
  request,
}) => {
  // Provider output is simulated ONLY in this browser test; no product fixture or paid call.
  const real = await (
    await request.post(`${apiUrl}/api/interpret`, {
      data: { query: 'يعسوب', mode: 'bm25', generate: false },
    })
  ).json();
  const source = real.sources[0];
  await page.route('**/health', async (route) => {
    const response = await route.fetch();
    await route.fulfill({
      response,
      json: { ...(await response.json()), generation_configured: true },
    });
  });
  let fail = false;
  await page.route('**/api/interpret', async (route) => {
    expect(route.request().postDataJSON().generate).toBe(true);
    await route.fulfill({
      json: {
        ...real,
        status: fail ? 'generation_failed' : 'generated',
        message: 'استجابة تجريبية لاختبار الواجهة فقط',
        synthesis: fail
          ? []
          : [
              {
                text: 'تلخيص تجريبي لاختبار الفصل البصري فقط.',
                citations: [
                  {
                    source_id: source.id,
                    quote: source.quote,
                    book_title: source.book_title,
                    author: source.author,
                    page_start: source.page_start,
                    page_end: source.page_end,
                    pdf_url: source.pdf_url,
                  },
                ],
              },
            ],
        generation_issue: fail
          ? { code: 'provider_timeout', message: 'انتهت مهلة التوليد التجريبية.', retryable: true }
          : null,
      },
    });
  });
  await page.goto('/');
  await page.getByLabel('اكتب رؤياك أو الرمز الذي تبحث عنه').fill('يعسوب');
  await page.getByRole('checkbox').check();
  await expect(page.getByText(/يُرسل النص والشواهد المختارة إلى DeepSeek/)).toBeVisible();
  await page.getByRole('button', { name: 'ابحث عن الشواهد' }).click();
  await expect(page.getByRole('region', { name: 'التلخيص الآلي' })).toContainText('تلخيص تجريبي');
  await expect(page.getByRole('heading', { name: 'الشواهد الأصلية' })).toBeVisible();
  await page.getByText('الشواهد التي يستند إليها هذا التلخيص').click();
  await expect(page.locator('.synthesis blockquote')).toHaveText(source.quote);
  fail = true;
  await page.getByRole('button', { name: 'ابحث عن الشواهد' }).click();
  await expect(page.getByText(/انتهت مهلة التوليد التجريبية/)).toBeVisible();
  await expect(page.locator('.synthesis')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'الشواهد الأصلية' })).toBeVisible();
});

test('reported sea-and-ship dream returns reviewed excerpts with honest scope', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page
    .getByLabel('اكتب رؤياك أو الرمز الذي تبحث عنه')
    .fill(
      'رأيت في المنام أنني أسافر في سفينة وسط البحر، وكانت الأمواج عالية، لكنني وصلت إلى الشاطئ بسلام.',
    );
  await page.getByRole('button', { name: 'ابحث عن الشواهد' }).click();
  await expect(page.getByRole('heading', { name: 'الشواهد الأصلية' })).toBeVisible({
    timeout: 60000,
  });
  await expect(page.getByText('مقتطف مراجع · الأصل غير معتمد بالكامل').first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'لا تتوفر شواهد كافية' })).toHaveCount(0);
  await expect(page.getByText(/الرموز المطابقة:/)).toContainText('سفينة');
  await expect(page.getByText(/الرموز المطابقة:/)).toContainText('بحر');
  await expect(page.locator('.synthesis')).toHaveCount(0);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
});
