/**
 * 开发：Excellent（11964948@qq.com）
 * 功能：Tailwind CSS 配置
 * 作用：定义设计系统颜色 token、字体、间距扩展
 * 创建时间：2026-03-08
 * 最后修改：2026-03-08
 */
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0D1117',
        'bg-secondary': '#161B22',
        'bg-tertiary': '#21262D',
        'bg-elevated': '#2D333B',
        'accent-blue': '#2563EB',
        'accent-blue-hover': '#3B82F6',
        'text-primary': '#F0F6FC',
        'text-secondary': '#8B949E',
        'text-muted': '#484F58',
        'border-default': '#30363D',
        'border-muted': '#21262D',
        'border-emphasis': '#2563EB',
        'status-green': '#3FB950',
        'status-red': '#F85149',
        'status-yellow': '#D29922',
        'status-blue': '#388BFD',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'PingFang SC', 'Microsoft YaHei', 'Menlo', 'monospace'],
      },
      animation: {
        'marquee': 'marquee 40s linear infinite',
        'marquee2': 'marquee2 40s linear infinite',
        'scroll': 'scroll 50s linear infinite',
        'fade-up': 'fadeUp 0.6s ease forwards',
        'blink': 'blink 1s step-end infinite',
      },
      keyframes: {
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-100%)' },
        },
        marquee2: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0%)' },
        },
        scroll: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
