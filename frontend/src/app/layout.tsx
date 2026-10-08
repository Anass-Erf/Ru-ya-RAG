import type { Metadata } from 'next';
import '@fontsource/noto-sans-arabic/400.css';
import '@fontsource/noto-sans-arabic/500.css';
import '@fontsource/noto-sans-arabic/600.css';
import '@fontsource/noto-naskh-arabic/400.css';
import '@fontsource/noto-naskh-arabic/600.css';
import './globals.css';
import { Shell } from '@/components/shell';
export const metadata: Metadata = { title: { default: 'رُؤيا — قراءة تستند إلى مصدر', template: '%s | رُؤيا' }, description: 'قراءة بحثية في نصوص تعبير الرؤى التاريخية، مع شواهد قابلة للتتبع وحدود واضحة.' };
const themeScript = `try{var t=localStorage.getItem('ruya-theme');document.documentElement.classList.toggle('dark',t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))}catch(e){}`;
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ar" dir="rtl" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: themeScript }}/></head><body><Shell>{children}</Shell></body></html>;
}
