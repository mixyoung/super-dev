export type SiteLocale = 'zh' | 'en';

// 与 next.config.mjs 的 basePath 逻辑保持一致：开发环境为空，生产为 GitHub Pages
// 项目路径 /super-dev。若未来重新启用自定义域名（CNAME/CUSTOM_DOMAIN），需同步调整此处。
const isDevRuntime = process.env.NODE_ENV !== 'production';
export const SITE_BASE_PATH = isDevRuntime ? '' : '/super-dev';
export const SITE_URL = 'https://mixyoung.github.io/super-dev/';

export function assetPath(path: string): string {
  if (!path) return SITE_BASE_PATH || '/';
  if (/^https?:\/\//.test(path)) return path;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${SITE_BASE_PATH}${normalized}`;
}

export function localizedPath(locale: SiteLocale, path: string): string {
  if (!path) return locale === 'en' ? '/en' : '/';
  if (/^https?:\/\//.test(path)) return path;
  if (path.startsWith('/en')) return path;
  if (locale === 'en') {
    return path === '/' ? '/en' : `/en${path}`;
  }
  return path;
}

export function detectLocaleFromPathname(pathname: string): SiteLocale {
  return pathname === '/en' || pathname.startsWith('/en/') ? 'en' : 'zh';
}

export function alternateLocalePath(pathname: string): string {
  if (pathname === '/en') return '/';
  if (pathname.startsWith('/en/')) return pathname.slice(3) || '/';
  if (pathname === '/') return '/en';
  return `/en${pathname}`;
}
