'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  BookOpen,
  Search,
  Library,
  ChartNoAxesCombined,
  Info,
  Moon,
  Sun,
  ArrowUpLeft,
  PanelRightClose,
  PanelRightOpen,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
const navigation = [
  { href: '/', label: 'قراءة الرؤيا', icon: Moon, caption: 'من النص إلى المعنى' },
  { href: '/search', label: 'البحث في المصادر', icon: Search, caption: 'استكشف النصوص' },
  { href: '/library', label: 'المكتبة الرقمية', icon: Library, caption: 'أمهات كتب التعبير' },
  {
    href: '/dashboard',
    label: 'لوحة الجودة',
    icon: ChartNoAxesCombined,
    caption: 'البيانات والأداء',
  },
  { href: '/about', label: 'عن المشروع', icon: Info, caption: 'المنهج والحدود' },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [dark, setDark] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const current = document.documentElement.classList.contains('dark');
    setDark(current);
  }, []);
  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    try {
      localStorage.setItem('ruya-theme', next ? 'dark' : 'light');
    } catch {
      /* Theme still works without storage. */
    }
  }
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        انتقل إلى المحتوى
      </a>
      <aside className={cn('sidebar', open && 'is-open')}>
        <Link href="/" className="brand" aria-label="رؤيا — الرئيسية">
          <span className="brand-mark">
            <BookOpen size={26} />
          </span>
          <span>
            <strong>رُؤيا</strong>
            <small>معرفةٌ تستند إلى مصدر</small>
          </span>
        </Link>
        <div className="sidebar-label">مساحة المعرفة</div>
        <nav aria-label="التنقل الرئيسي">
          {navigation.map(({ href, label, icon: Icon, caption }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              aria-current={pathname === href ? 'page' : undefined}
              className={cn('nav-link', pathname === href && 'active')}
            >
              <Icon size={20} />
              <span>
                <b>{label}</b>
                <small>{caption}</small>
              </span>
              {pathname === href && <span className="nav-dot" />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="mini-label">منهج رؤيا</span>
          <p>
            نعود إلى النص،
            <br />
            ونترك اليقين لأهله.
          </p>
          <Link href="/about" onClick={() => setOpen(false)}>
            تعرّف على المنهج <ArrowUpLeft size={16} />
          </Link>
        </div>
        <div className="sidebar-bottom">
          <span className="status-dot" /> نسخة بحثية · قيد التطوير
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="topbar-location">
            <Button
              variant="ghost"
              size="icon"
              className="mobile-menu"
              aria-label={open ? 'إغلاق القائمة' : 'فتح القائمة'}
              aria-expanded={open}
              onClick={() => setOpen(!open)}
            >
              {open ? <PanelRightClose /> : <PanelRightOpen />}
            </Button>
            <span>رُؤيا</span>
            <span className="divider">/</span>
            <span>{navigation.find((n) => n.href === pathname)?.label || 'المصدر'}</span>
          </div>
          <div className="topbar-actions">
            <span className="research-tag">قراءة تاريخية موثّقة</span>
            <Button
              variant="ghost"
              size="icon"
              aria-label={dark ? 'تفعيل الوضع الفاتح' : 'تفعيل الوضع الداكن'}
              onClick={toggleTheme}
            >
              {dark ? <Sun /> : <Moon />}
            </Button>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <footer className="footer">
          <span>رُؤيا · النص أولاً، والتأويل باحتراز.</span>
          <Link href="/about">
            المصادر والمنهج <ArrowUpLeft size={13} />
          </Link>
        </footer>
      </div>
    </div>
  );
}
