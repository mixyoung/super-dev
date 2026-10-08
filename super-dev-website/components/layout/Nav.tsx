'use client';
/**
 * 开发：Excellent（11964948@qq.com）
 * 功能：顶部导航栏
 * 作用：固定导航、响应式汉堡菜单、GitHub Star 数显示、官方群弹窗
 * 创建时间：2026-03-08
 * 最后修改：2026-03-26
 */
import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
// usePathname removed - no longer needed after handleGetStarted removal
import { Github, Menu, X, Star, Users, Copy, Check, Mail } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { LocaleSwitch } from '@/components/ui/LocaleSwitch';
import { formatStarCount, GITHUB_REPO_URL } from '@/lib/github';
import { useGithubStars } from '@/lib/useGithubStars';
import { assetPath, localizedPath, type SiteLocale } from '@/lib/site-locale';

interface NavProps {
  locale?: SiteLocale;
}

const COPY = {
  zh: {
    nav: [
      { label: '功能', href: '/#features' },
      { label: '宿主', href: '/#hosts' },
      { label: '案例', href: '/showcase' },
      { label: '文档', href: '/docs' },
      { label: '更新', href: '/changelog' },
    ],
    start: '联系开发者',
    qrTitle: '联系 Super Dev 开发者',
    mobileOpen: '打开菜单',
    mobileClose: '关闭菜单',
    ariaHome: 'Super Dev 首页',
    ariaNav: '主导航',
    github: 'GitHub',
  },
  en: {
    nav: [
      { label: 'Features', href: '/#features' },
      { label: 'Hosts', href: '/#hosts' },
      { label: 'Showcase', href: '/showcase' },
      { label: 'Docs', href: '/docs' },
      { label: 'Changelog', href: '/changelog' },
    ],
    start: 'Contact',
    qrTitle: 'Contact the Super Dev Developer',
    mobileOpen: 'Open menu',
    mobileClose: 'Close menu',
    ariaHome: 'Super Dev home',
    ariaNav: 'Main navigation',
    github: 'GitHub',
  },
} as const;

export function Nav({ locale = 'zh' }: NavProps) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [qrOpen, setQrOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const stars = useGithubStars();
  const copy = COPY[locale];
  const navLinks = copy.nav.map((link) => ({ ...link, href: localizedPath(locale, link.href) }));

  useEffect(() => {
    function handleScroll() {
      setScrolled(window.scrollY > 20);
    }
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale === 'en' ? 'en' : 'zh-CN';
  }, [locale]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  function handleMobileClose() {
    setMobileOpen(false);
  }

  // handleGetStarted 已移除，改为弹出官方群二维码

  return (
    <>
      <header
        className={cn(
          'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
          scrolled
            ? 'backdrop-blur-md bg-bg-primary/80 border-b border-border-muted'
            : 'bg-transparent'
        )}
      >
        <nav
          className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14"
          aria-label={copy.ariaNav}
        >
          <Link
            href={localizedPath(locale, '/')}
            className="flex items-center gap-2.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue rounded-md"
            aria-label={copy.ariaHome}
          >
            <span className="relative h-10 w-10 overflow-hidden rounded-xl border border-border-default/80 bg-bg-secondary/70 ring-1 ring-white/5 transition-all duration-150 group-hover:border-accent-blue/60">
              <Image
                src={assetPath('/logo.png')}
                alt=""
                fill
                sizes="40px"
                className="object-cover"
                aria-hidden="true"
                unoptimized
              />
            </span>
            <span className="font-mono font-bold text-text-primary text-base tracking-tight">
              Super Dev
            </span>
          </Link>

          <ul className="hidden md:flex items-center gap-1" role="list">
            {navLinks.map((link) => (
              <li key={link.label}>
                <Link
                  href={link.href}
                  className="px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors duration-150 rounded-md"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>

          <div className="hidden md:flex items-center gap-3">
            <LocaleSwitch />
            <a
              href={GITHUB_REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm',
                'border border-border-default text-text-secondary',
                'hover:border-border-emphasis hover:text-text-primary',
                'transition-all duration-150'
              )}
              aria-label="GitHub repository"
            >
              <Github size={14} aria-hidden="true" />
              <Star size={12} aria-hidden="true" />
              {stars > 0 && <span className="font-mono">{formatStarCount(stars)}</span>}
            </a>
            <Button variant="primary" size="sm" onClick={() => setQrOpen(true)}>
              <Users size={14} aria-hidden="true" className="mr-1.5" />
              {copy.start}
            </Button>
          </div>

          <button
            className="md:hidden p-2 text-text-secondary hover:text-text-primary transition-colors rounded-md"
            onClick={() => setMobileOpen((prev) => !prev)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-menu"
            aria-label={mobileOpen ? copy.mobileClose : copy.mobileOpen}
          >
            {mobileOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
          </button>
        </nav>
      </header>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-bg-primary/95 backdrop-blur-sm pt-14"
          id="mobile-menu"
          role="dialog"
          aria-label={copy.ariaNav}
        >
          <nav className="flex flex-col p-6 gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={handleMobileClose}
                className="py-3 px-4 text-lg text-text-secondary hover:text-text-primary rounded-lg hover:bg-bg-secondary transition-colors"
              >
                {link.label}
              </Link>
            ))}
            <div className="mt-4 pt-4 border-t border-border-muted flex flex-col gap-3">
              <LocaleSwitch className="justify-center" />
              <a
                href={GITHUB_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 py-3 px-4 text-text-secondary hover:text-text-primary"
              >
                <Github size={16} aria-hidden="true" />
                {copy.github}
                {stars > 0 ? ` (★${formatStarCount(stars)})` : ''}
              </a>
              <Button
                variant="primary"
                size="lg"
                className="w-full"
                onClick={() => {
                  handleMobileClose();
                  setQrOpen(true);
                }}
              >
                <Users size={16} aria-hidden="true" className="mr-2" />
                {copy.start}
              </Button>
            </div>
          </nav>
        </div>
      )}

      {/* 官方群二维码弹窗 */}
      {qrOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setQrOpen(false)}
          role="dialog"
          aria-label={copy.qrTitle}
        >
          <div
            className="relative bg-bg-primary border border-border-default rounded-2xl p-8 max-w-sm mx-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="absolute top-3 right-3 p-1 text-text-muted hover:text-text-primary transition-colors rounded-md"
              onClick={() => setQrOpen(false)}
              aria-label={locale === 'zh' ? '关闭' : 'Close'}
            >
              <X size={20} aria-hidden="true" />
            </button>
            <div className="text-center">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-blue/10 border border-accent-blue/20 mb-4">
                <Mail size={14} className="text-accent-blue" aria-hidden="true" />
                <span className="text-sm text-accent-blue font-medium">{copy.start}</span>
              </div>
              <h3 className="text-lg font-bold text-text-primary mb-2">{copy.qrTitle}</h3>
              <div className="flex items-center justify-center gap-2 mt-4 mb-5">
                <span className="text-base text-text-primary font-mono bg-bg-secondary px-3 py-1.5 rounded-lg border border-border-default">
                  mixyoung@gmail.com
                </span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText('mixyoung@gmail.com');
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className={cn(
                    'flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150',
                    copied
                      ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                      : 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20 hover:bg-accent-blue/20'
                  )}
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  {copied ? (locale === 'zh' ? '已复制' : 'Copied') : (locale === 'zh' ? '复制' : 'Copy')}
                </button>
              </div>
              <a
                href="mailto:mixyoung@gmail.com"
                className="inline-flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-lg bg-accent-blue text-white text-sm font-medium hover:bg-accent-blue-hover transition-colors"
              >
                <Mail size={16} aria-hidden="true" />
                {locale === 'zh' ? '发送邮件' : 'Send email'}
              </a>
              <p className="text-xs text-text-muted mt-4">
                {locale === 'zh' ? '邮件是联系开发者的方式，欢迎反馈问题与需求' : 'Email is the way to reach the developer — issues and ideas welcome'}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
