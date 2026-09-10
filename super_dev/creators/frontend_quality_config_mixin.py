"""Design-system, testing and performance configuration generators."""

from __future__ import annotations


class FrontendQualityConfigMixin:
    def generate_design_system_scaffold(self) -> dict[str, str]:
        """生成设计系统参考模板（Token 文件、主题配置、组件模板）"""
        output_dir = self.project_dir / "output" / "design-system"
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        ui_contract = self._load_ui_contract()
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})

        # Design tokens CSS
        tokens_file = output_dir / "tokens.css"
        primary = palette.get("primary", "#2563EB")
        secondary = palette.get("secondary", "#3B82F6")
        accent = palette.get("accent", "#EA580C")
        background = palette.get("background", "#FFFFFF")
        text_color = palette.get("text", "#111827")
        border = palette.get("border", "#E5E7EB")
        heading = typography.get("heading", "Manrope")
        body = typography.get("body", "Source Sans 3")

        tokens_file.write_text(
            (
                ":root {\n"
                "  /* --- Color Tokens --- */\n"
                f"  --color-primary: {primary};\n"
                f"  --color-secondary: {secondary};\n"
                f"  --color-accent: {accent};\n"
                f"  --color-background: {background};\n"
                f"  --color-text: {text_color};\n"
                f"  --color-border: {border};\n"
                "  --color-surface: #FFFFFF;\n"
                "  --color-muted: #6B7280;\n"
                "  --color-success: #059669;\n"
                "  --color-warning: #D97706;\n"
                "  --color-error: #DC2626;\n"
                "  --color-info: #2563EB;\n\n"
                "  /* --- Typography Tokens --- */\n"
                f"  --font-heading: '{heading}', system-ui, sans-serif;\n"
                f"  --font-body: '{body}', system-ui, sans-serif;\n"
                "  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;\n\n"
                "  --text-xs: 0.75rem;    /* 12px */\n"
                "  --text-sm: 0.875rem;   /* 14px */\n"
                "  --text-base: 1rem;     /* 16px */\n"
                "  --text-lg: 1.125rem;   /* 18px */\n"
                "  --text-xl: 1.25rem;    /* 20px */\n"
                "  --text-2xl: 1.5rem;    /* 24px */\n"
                "  --text-3xl: 1.875rem;  /* 30px */\n"
                "  --text-4xl: 2.25rem;   /* 36px */\n\n"
                "  /* --- Spacing Tokens --- */\n"
                "  --space-1: 0.25rem;    /* 4px */\n"
                "  --space-2: 0.5rem;     /* 8px */\n"
                "  --space-3: 0.75rem;    /* 12px */\n"
                "  --space-4: 1rem;       /* 16px */\n"
                "  --space-5: 1.25rem;    /* 20px */\n"
                "  --space-6: 1.5rem;     /* 24px */\n"
                "  --space-8: 2rem;       /* 32px */\n"
                "  --space-10: 2.5rem;    /* 40px */\n"
                "  --space-12: 3rem;      /* 48px */\n"
                "  --space-16: 4rem;      /* 64px */\n\n"
                "  /* --- Border Radius Tokens --- */\n"
                "  --radius-sm: 4px;\n"
                "  --radius-md: 8px;\n"
                "  --radius-lg: 12px;\n"
                "  --radius-xl: 16px;\n"
                "  --radius-2xl: 24px;\n"
                "  --radius-full: 9999px;\n\n"
                "  /* --- Shadow Tokens --- */\n"
                "  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);\n"
                "  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);\n"
                "  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);\n"
                "  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);\n\n"
                "  /* --- Transition Tokens --- */\n"
                "  --transition-fast: 150ms ease;\n"
                "  --transition-base: 200ms ease;\n"
                "  --transition-slow: 300ms ease;\n\n"
                "  /* --- Z-Index Tokens --- */\n"
                "  --z-dropdown: 1000;\n"
                "  --z-sticky: 1020;\n"
                "  --z-fixed: 1030;\n"
                "  --z-modal-backdrop: 1040;\n"
                "  --z-modal: 1050;\n"
                "  --z-popover: 1060;\n"
                "  --z-tooltip: 1070;\n"
                "}\n\n"
                "@media (prefers-color-scheme: dark) {\n"
                "  :root {\n"
                "    --color-background: #0F172A;\n"
                "    --color-text: #F8FAFC;\n"
                "    --color-surface: #1E293B;\n"
                "    --color-border: #334155;\n"
                "    --color-muted: #94A3B8;\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["tokens.css"] = str(tokens_file)

        # Theme config (Tailwind-compatible)
        theme_file = output_dir / "theme.ts"
        theme_file.write_text(
            (
                "/**\n"
                " * Design System Theme Configuration\n"
                " * Use with Tailwind CSS or any token-based styling system.\n"
                " */\n\n"
                "export const theme = {\n"
                "  colors: {\n"
                f"    primary: '{primary}',\n"
                f"    secondary: '{secondary}',\n"
                f"    accent: '{accent}',\n"
                f"    background: '{background}',\n"
                f"    text: '{text_color}',\n"
                f"    border: '{border}',\n"
                "    success: '#059669',\n"
                "    warning: '#D97706',\n"
                "    error: '#DC2626',\n"
                "  },\n"
                "  fonts: {\n"
                f"    heading: '{heading}',\n"
                f"    body: '{body}',\n"
                "  },\n"
                "  breakpoints: {\n"
                "    sm: '640px',\n"
                "    md: '768px',\n"
                "    lg: '1024px',\n"
                "    xl: '1280px',\n"
                "    '2xl': '1440px',\n"
                "  },\n"
                "} as const;\n"
            ),
            encoding="utf-8",
        )
        files["theme.ts"] = str(theme_file)

        # Component template (Button example)
        components_dir = output_dir / "components"
        components_dir.mkdir(parents=True, exist_ok=True)
        (components_dir / "Button.tsx").write_text(
            (
                "import React from 'react';\n\n"
                "type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive';\n"
                "type ButtonSize = 'sm' | 'md' | 'lg';\n\n"
                "interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {\n"
                "  variant?: ButtonVariant;\n"
                "  size?: ButtonSize;\n"
                "  loading?: boolean;\n"
                "}\n\n"
                "const variantStyles: Record<ButtonVariant, string> = {\n"
                "  primary: 'bg-[var(--color-primary)] text-white hover:opacity-90',\n"
                "  secondary: 'bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-gray-50',\n"
                "  ghost: 'bg-transparent text-[var(--color-text)] hover:bg-gray-100',\n"
                "  destructive: 'bg-[var(--color-error)] text-white hover:opacity-90',\n"
                "};\n\n"
                "const sizeStyles: Record<ButtonSize, string> = {\n"
                "  sm: 'h-8 px-3 text-sm rounded-[var(--radius-md)]',\n"
                "  md: 'h-10 px-4 text-base rounded-[var(--radius-lg)]',\n"
                "  lg: 'h-12 px-6 text-lg rounded-[var(--radius-lg)]',\n"
                "};\n\n"
                "export function Button({ variant = 'primary', size = 'md', loading, className = '', children, disabled, ...props }: ButtonProps) {\n"
                "  return (\n"
                "    <button\n"
                "      className={`inline-flex items-center justify-center font-semibold transition-all\n"
                "        ${variantStyles[variant]} ${sizeStyles[size]}\n"
                "        ${disabled || loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}\n"
                "        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2\n"
                "        ${className}`}\n"
                "      disabled={disabled || loading}\n"
                "      {...props}\n"
                "    >\n"
                '      {loading && <span className="mr-2 animate-spin">...</span>}\n'
                "      {children}\n"
                "    </button>\n"
                "  );\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["components/Button.tsx"] = str(components_dir / "Button.tsx")

        return files

    def generate_test_config(self) -> dict[str, str]:
        """生成测试配置（Vitest/Playwright/Storybook）"""
        output_dir = self.project_dir / "output" / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        # Vitest config
        vitest_config = output_dir / "vitest.config.ts"
        vitest_config.write_text(
            (
                "import { defineConfig } from 'vitest/config';\n"
                "import { resolve } from 'path';\n\n"
                "export default defineConfig({\n"
                "  test: {\n"
                "    globals: true,\n"
                "    environment: 'jsdom',\n"
                "    setupFiles: ['./src/test/setup.ts'],\n"
                "    include: ['src/**/*.{test,spec}.{js,ts,jsx,tsx}'],\n"
                "    coverage: {\n"
                "      reporter: ['text', 'json', 'html'],\n"
                "      include: ['src/**/*.{ts,tsx,vue}'],\n"
                "      exclude: ['src/test/**', 'src/**/*.d.ts', 'src/**/*.stories.*'],\n"
                "      thresholds: {\n"
                "        branches: 70,\n"
                "        functions: 70,\n"
                "        lines: 70,\n"
                "        statements: 70,\n"
                "      },\n"
                "    },\n"
                "  },\n"
                "  resolve: {\n"
                "    alias: { '@': resolve(__dirname, 'src') },\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vitest.config.ts"] = str(vitest_config)

        # Test setup
        test_dir = output_dir / "src" / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "setup.ts").write_text(
            (
                "import '@testing-library/jest-dom';\n\n"
                "// Global test setup\n"
                "beforeAll(() => {\n"
                "  // Add any global setup here\n"
                "});\n\n"
                "afterAll(() => {\n"
                "  // Add any global teardown here\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["src/test/setup.ts"] = str(test_dir / "setup.ts")

        # Playwright config
        playwright_config = output_dir / "playwright.config.ts"
        playwright_config.write_text(
            (
                "import { defineConfig, devices } from '@playwright/test';\n\n"
                "export default defineConfig({\n"
                "  testDir: './e2e',\n"
                "  fullyParallel: true,\n"
                "  forbidOnly: !!process.env.CI,\n"
                "  retries: process.env.CI ? 2 : 0,\n"
                "  workers: process.env.CI ? 1 : undefined,\n"
                "  reporter: [['html', { open: 'never' }]],\n"
                "  use: {\n"
                "    baseURL: 'http://localhost:3000',\n"
                "    trace: 'on-first-retry',\n"
                "    screenshot: 'only-on-failure',\n"
                "  },\n"
                "  projects: [\n"
                "    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },\n"
                "    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },\n"
                "    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },\n"
                "    { name: 'mobile-safari', use: { ...devices['iPhone 12'] } },\n"
                "  ],\n"
                "  webServer: {\n"
                "    command: 'npm run dev',\n"
                "    url: 'http://localhost:3000',\n"
                "    reuseExistingServer: !process.env.CI,\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["playwright.config.ts"] = str(playwright_config)

        # Sample e2e test
        e2e_dir = output_dir / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        (e2e_dir / "home.spec.ts").write_text(
            (
                "import { test, expect } from '@playwright/test';\n\n"
                "test.describe('Home Page', () => {\n"
                "  test('should display the page title', async ({ page }) => {\n"
                "    await page.goto('/');\n"
                "    await expect(page).toHaveTitle(/.+/);\n"
                "  });\n\n"
                "  test('should be responsive on mobile', async ({ page }) => {\n"
                "    await page.setViewportSize({ width: 375, height: 812 });\n"
                "    await page.goto('/');\n"
                "    await expect(page.locator('main')).toBeVisible();\n"
                "  });\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["e2e/home.spec.ts"] = str(e2e_dir / "home.spec.ts")

        # Storybook main.ts
        storybook_dir = output_dir / ".storybook"
        storybook_dir.mkdir(parents=True, exist_ok=True)
        (storybook_dir / "main.ts").write_text(
            (
                "import type { StorybookConfig } from '@storybook/react-vite';\n\n"
                "const config: StorybookConfig = {\n"
                "  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx|mdx)'],\n"
                "  addons: [\n"
                "    '@storybook/addon-essentials',\n"
                "    '@storybook/addon-a11y',\n"
                "    '@storybook/addon-interactions',\n"
                "  ],\n"
                "  framework: {\n"
                "    name: '@storybook/react-vite',\n"
                "    options: {},\n"
                "  },\n"
                "};\n"
                "export default config;\n"
            ),
            encoding="utf-8",
        )
        files[".storybook/main.ts"] = str(storybook_dir / "main.ts")

        return files

    def generate_performance_config(self) -> dict[str, str]:
        """生成性能优化配置（代码分割/懒加载/预加载配置）"""
        output_dir = self.project_dir / "output" / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}

        # Vite optimized config
        perf_config = output_dir / "vite.config.perf.ts"
        perf_config.write_text(
            (
                "import { defineConfig } from 'vite';\n"
                "import { resolve } from 'path';\n\n"
                "/**\n"
                " * Performance-optimized Vite configuration.\n"
                " * Merge this with your main vite.config.ts.\n"
                " */\n"
                "export default defineConfig({\n"
                "  build: {\n"
                "    target: 'es2022',\n"
                "    minify: 'esbuild',\n"
                "    sourcemap: false,\n"
                "    cssMinify: true,\n"
                "    rollupOptions: {\n"
                "      output: {\n"
                "        manualChunks(id) {\n"
                "          // Vendor chunk splitting\n"
                "          if (id.includes('node_modules')) {\n"
                "            if (id.includes('react') || id.includes('react-dom')) return 'vendor-react';\n"
                "            if (id.includes('vue')) return 'vendor-vue';\n"
                "            if (id.includes('lodash') || id.includes('date-fns')) return 'vendor-utils';\n"
                "            if (id.includes('chart') || id.includes('recharts') || id.includes('echarts')) return 'vendor-charts';\n"
                "            return 'vendor';\n"
                "          }\n"
                "        },\n"
                "        chunkFileNames: 'assets/js/[name]-[hash].js',\n"
                "        entryFileNames: 'assets/js/[name]-[hash].js',\n"
                "        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',\n"
                "      },\n"
                "    },\n"
                "    chunkSizeWarningLimit: 500,\n"
                "  },\n"
                "  css: {\n"
                "    devSourcemap: true,\n"
                "  },\n"
                "  optimizeDeps: {\n"
                "    include: ['react', 'react-dom'],\n"
                "  },\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files["vite.config.perf.ts"] = str(perf_config)

        # Lazy loading utilities
        utils_dir = output_dir / "src" / "utils"
        utils_dir.mkdir(parents=True, exist_ok=True)
        (utils_dir / "lazy.ts").write_text(
            (
                "import { lazy, Suspense, createElement, type ComponentType, type ReactNode } from 'react';\n\n"
                "/**\n"
                " * Enhanced lazy loading with preload support and error boundary.\n"
                " */\n"
                "export function lazyWithPreload<T extends ComponentType<any>>(\n"
                "  factory: () => Promise<{ default: T }>\n"
                ") {\n"
                "  const Component = lazy(factory);\n"
                "  (Component as any).preload = factory;\n"
                "  return Component;\n"
                "}\n\n"
                "/**\n"
                " * Preload a route component on hover/focus.\n"
                " */\n"
                "export function prefetchOnInteraction(preloadFn: () => Promise<any>) {\n"
                "  return {\n"
                "    onMouseEnter: () => preloadFn(),\n"
                "    onFocus: () => preloadFn(),\n"
                "  };\n"
                "}\n\n"
                "/**\n"
                " * Intersection Observer based lazy loading for below-fold sections.\n"
                " */\n"
                "export function useIntersectionLazy(ref: React.RefObject<Element>, threshold = 0.1) {\n"
                "  const [isVisible, setIsVisible] = useState(false);\n"
                "  useEffect(() => {\n"
                "    if (!ref.current) return;\n"
                "    const observer = new IntersectionObserver(\n"
                "      ([entry]) => { if (entry.isIntersecting) { setIsVisible(true); observer.disconnect(); } },\n"
                "      { threshold }\n"
                "    );\n"
                "    observer.observe(ref.current);\n"
                "    return () => observer.disconnect();\n"
                "  }, [ref, threshold]);\n"
                "  return isVisible;\n"
                "}\n\n"
                "import { useState, useEffect } from 'react';\n"
            ),
            encoding="utf-8",
        )
        files["src/utils/lazy.ts"] = str(utils_dir / "lazy.ts")

        # Resource hints helper
        (utils_dir / "resource-hints.ts").write_text(
            (
                "/**\n"
                " * Add preload/prefetch resource hints dynamically.\n"
                " */\n"
                "export function addResourceHint(\n"
                "  href: string,\n"
                "  rel: 'preload' | 'prefetch' | 'preconnect' = 'prefetch',\n"
                "  as_?: 'script' | 'style' | 'image' | 'font'\n"
                "): void {\n"
                "  if (typeof document === 'undefined') return;\n"
                '  const existing = document.querySelector(`link[href="${href}"]`);\n'
                "  if (existing) return;\n"
                "  const link = document.createElement('link');\n"
                "  link.rel = rel;\n"
                "  link.href = href;\n"
                "  if (as_) link.setAttribute('as', as_);\n"
                "  if (rel === 'preconnect') link.crossOrigin = 'anonymous';\n"
                "  document.head.appendChild(link);\n"
                "}\n\n"
                "/**\n"
                " * Preconnect to critical third-party origins.\n"
                " */\n"
                "export function preconnectCritical(): void {\n"
                "  const origins = [\n"
                "    'https://fonts.googleapis.com',\n"
                "    'https://fonts.gstatic.com',\n"
                "    'https://cdn.jsdelivr.net',\n"
                "  ];\n"
                "  origins.forEach(origin => addResourceHint(origin, 'preconnect'));\n"
                "}\n\n"
                "/**\n"
                " * Image loading optimization: generate srcSet for responsive images.\n"
                " */\n"
                "export function generateSrcSet(\n"
                "  basePath: string,\n"
                "  widths: number[] = [320, 640, 960, 1280, 1920]\n"
                "): string {\n"
                "  const ext = basePath.split('.').pop() || 'jpg';\n"
                "  const base = basePath.replace(`.${ext}`, '');\n"
                "  return widths\n"
                "    .map(w => `${base}-${w}w.${ext} ${w}w`)\n"
                "    .join(', ');\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files["src/utils/resource-hints.ts"] = str(utils_dir / "resource-hints.ts")

        return files
