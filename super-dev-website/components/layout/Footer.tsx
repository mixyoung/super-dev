/**
 * 开发：Excellent（11964948@qq.com）
 * 功能：页脚组件
 * 作用：四栏链接布局 + 版权信息 + 多语言入口
 * 创建时间：2026-03-08
 * 最后修改：2026-03-08
 */
import Image from 'next/image';
import Link from 'next/link';
import { Github } from 'lucide-react';
import { assetPath, localizedPath, type SiteLocale } from '@/lib/site-locale';

interface FooterProps {
  locale?: SiteLocale;
}

const COPY = {
  zh: {
    brand: 'AI 编码工具的流程治理层',
    source: '在 GitHub 查看源代码',
    builtWith: 'Built with',
    sections: [
      {
        title: '产品',
        links: [
          { label: '功能特性', href: '/#features' },
          { label: '宿主兼容性', href: '/#hosts' },
          { label: '更新日志', href: '/changelog' },
        ],
      },
      {
        title: '资源',
        links: [
          { label: '文档中心', href: '/docs' },
          { label: 'README', href: 'https://github.com/mixyoung/super-dev#readme', external: true },
          { label: '发布', href: 'https://github.com/mixyoung/super-dev/releases', external: true },
        ],
      },
      {
        title: '项目',
        links: [
          { label: 'GitHub', href: 'https://github.com/mixyoung/super-dev', external: true },
          { label: 'Issues', href: 'https://github.com/mixyoung/super-dev/issues', external: true },
          { label: 'MIT 许可证', href: 'https://github.com/mixyoung/super-dev/blob/main/LICENSE', external: true },
        ],
      },
      {
        title: '联系',
        links: [
          { label: '贡献指南', href: 'https://github.com/mixyoung/super-dev/blob/main/CONTRIBUTING.md', external: true },
          { label: 'mixyoung', href: 'https://github.com/mixyoung', external: true },
        ],
      },
    ],
  },
  en: {
    brand: 'The governance layer for AI coding tools',
    source: 'View source on GitHub',
    builtWith: 'Built with',
    sections: [
      {
        title: 'Product',
        links: [
          { label: 'Features', href: '/#features' },
          { label: 'Hosts', href: '/#hosts' },
          { label: 'Changelog', href: '/changelog' },
        ],
      },
      {
        title: 'Resources',
        links: [
          { label: 'Docs', href: '/docs' },
          { label: 'README', href: 'https://github.com/mixyoung/super-dev#readme', external: true },
          { label: 'Releases', href: 'https://github.com/mixyoung/super-dev/releases', external: true },
        ],
      },
      {
        title: 'Project',
        links: [
          { label: 'GitHub', href: 'https://github.com/mixyoung/super-dev', external: true },
          { label: 'Issues', href: 'https://github.com/mixyoung/super-dev/issues', external: true },
          { label: 'MIT License', href: 'https://github.com/mixyoung/super-dev/blob/main/LICENSE', external: true },
        ],
      },
      {
        title: 'Contact',
        links: [
          { label: 'Contributing', href: 'https://github.com/mixyoung/super-dev/blob/main/CONTRIBUTING.md', external: true },
          { label: 'mixyoung', href: 'https://github.com/mixyoung', external: true },
        ],
      },
    ],
  },
} as const;

export function Footer({ locale = 'zh' }: FooterProps) {
  const currentYear = new Date().getFullYear();
  const copy = COPY[locale];

  return (
    <footer className="bg-bg-primary border-t border-border-muted" role="contentinfo">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 lg:py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 lg:gap-12">
          <div className="col-span-2 md:col-span-1">
            <Link
              href={localizedPath(locale, '/')}
              className="flex items-center gap-2 mb-3 group w-fit"
              aria-label="Super Dev 首页"
            >
              <span className="relative h-7 w-7 overflow-hidden rounded-lg border border-border-default/80 bg-bg-secondary/70 ring-1 ring-white/5 transition-all duration-150 group-hover:border-accent-blue/60">
                <Image
                  src={assetPath('/logo.png')}
                  alt=""
                  fill
                  sizes="28px"
                  className="object-cover"
                  aria-hidden="true"
                  unoptimized
                />
              </span>
              <span className="font-mono font-bold text-text-primary text-base">Super Dev</span>
            </Link>
            <p className="text-sm text-text-muted leading-relaxed max-w-[220px]">{copy.brand}</p>
            <a
              href="https://github.com/mixyoung/super-dev"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-4 text-sm text-text-muted hover:text-text-secondary transition-colors"
              aria-label={copy.source}
            >
              <Github size={14} aria-hidden="true" />
              MIT Open Source
            </a>
          </div>

          {copy.sections.map((section) => (
            <div key={section.title}>
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-4">
                {section.title}
              </h3>
              <ul className="space-y-3" role="list">
                {section.links.map((link) => (
                  <li key={link.label}>
                    {'external' in link ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-150"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={localizedPath(locale, link.href)}
                        className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-150"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-6 border-t border-border-muted flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-text-muted">&copy; {currentYear} mixyoung. MIT License.</p>
          <p className="text-xs text-text-muted">
            {copy.builtWith}{' '}
            <a
              href="https://github.com/mixyoung/super-dev"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent-blue hover:text-accent-blue-hover transition-colors"
            >
              Super Dev
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
