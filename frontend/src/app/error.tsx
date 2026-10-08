'use client';
import { Button } from '@/components/ui/button';
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <section className="empty" role="alert">
      <h1>تعذر عرض الصفحة</h1>
      <p>حدث خطأ غير متوقع. حاول تحميلها مجددا.</p>
      <Button className="mt-5" onClick={reset}>
        إعادة المحاولة
      </Button>
    </section>
  );
}
