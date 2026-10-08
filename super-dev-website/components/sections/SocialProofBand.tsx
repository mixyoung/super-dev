import { Archive, BadgeCheck, BookCopy, PackageCheck, ShieldCheck, Users } from 'lucide-react';
import { STATS } from '@/lib/constants';
import type { SiteLocale } from '@/lib/site-locale';

const COPY = {
  zh: {
    intro: '不是装完一个 Python 包就结束。安装器会把当前宿主矩阵收敛到同一条主路径：接入、复制宿主首句、回宿主里开始 research。',
    labels: STATS.zh,
  },
  en: {
    intro: 'Installing a Python package is not the product. The installer pulls the current host matrix onto one path: onboard, copy the host-specific first prompt, then go back into the host and start research.',
    labels: STATS.en,
  },
} as const;

const PROOF = {
  zh: {
    eyebrow: 'Proof / Trust',
    title: '可信度来自可验证的证据。',
    body: '开源、已发布、多宿主、本地知识库、宿主验收、Spec 评分、质量门禁和交付产物，都直接展示给用户。',
    items: [
      { icon: BadgeCheck, title: 'MIT 开源与 GitHub Release 发布', body: '代码可见、安装路径清晰、版本可追踪；正式版本通过 GitHub Release 发布 wheel、sdist 与校验和，安装升级用 Git 标签或 Release wheel。' },
      { icon: PackageCheck, title: '多宿主接入与验收中心', body: '同一套治理逻辑可安装到 CLI 和 IDE 宿主，并通过 Host Validation Center 跟踪前置条件、运行时验收和交付就绪状态。' },
      { icon: BookCopy, title: '本地知识库优先', body: 'knowledge/ 和 knowledge bundle 会优先进入 research、三文档、Spec、质量与交付。' },
      { icon: ShieldCheck, title: 'UI Review、Spec Quality 与 Release Readiness', body: '运行验证、质量门禁、Spec Quality 和发布检查都会明确产出结果，方便判断项目是否达到交付标准。' },
      { icon: Archive, title: '交付产物可审计', body: 'Repo Map、Dependency Graph、Impact Analysis、Regression Guard、Proof Pack 等交付证据都会落盘，便于复盘、交接和审查。' },
      { icon: Users, title: '10 专家 Agent 协作', body: 'PM、架构师、UI/UX、安全、代码、DBA、QA、DevOps、RCA 十位专家各司其职，每个阶段以对应专家的专业标准约束宿主产出。' },
    ],
  },
  en: {
    eyebrow: 'Proof / Trust',
    title: 'Visible trust signals.',
    body: 'Open source, published releases, host coverage, local knowledge, host validation, spec scoring, quality gates, and delivery artifacts all appear directly on the page.',
    items: [
      { icon: BadgeCheck, title: 'MIT open source and GitHub Release distribution', body: 'The code is visible, the install path is clear, and versions are traceable; official releases publish wheel, sdist, and checksums through GitHub Releases, with installs and upgrades via Git tags or Release wheels.' },
      { icon: PackageCheck, title: 'Multi-host integration and validation', body: 'The same governance model installs into CLI and IDE hosts, while the Host Validation Center tracks prerequisites, runtime acceptance, and delivery readiness.' },
      { icon: BookCopy, title: 'Local knowledge first', body: 'knowledge/ and knowledge bundles are reused in research, the three core docs, spec generation, quality, and delivery.' },
      { icon: ShieldCheck, title: 'UI Review, Spec Quality, and Release Readiness', body: 'The work is not done when code is generated. It must pass runtime validation, quality gates, spec-quality scoring, and release checks.' },
      { icon: Archive, title: 'Auditable delivery artifacts', body: 'Repo Map, Dependency Graph, Impact Analysis, Regression Guard, Proof Pack, and release artifacts are written to disk.' },
      { icon: Users, title: '10-Expert Agent Collaboration', body: 'PM, Architect, UI/UX, Security, Code, DBA, QA, DevOps, and RCA experts each govern their stage, constraining host output to professional standards.' },
    ],
  },
} as const;

export function SocialProofBand({ locale = 'zh' }: { locale?: SiteLocale }) {
  const copy = COPY[locale];
  const proof = PROOF[locale];

  return (
    <section className="border-b border-border-muted bg-bg-secondary py-14 lg:py-16" aria-label="Site trust signals">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <p className="mb-6 max-w-3xl text-sm leading-7 text-text-secondary">{copy.intro}</p>

        <dl className="grid gap-6 sm:grid-cols-3">
          {copy.labels.map((stat) => (
            <div key={stat.label} className="rounded-xl border border-border-default bg-bg-primary/60 px-5 py-4">
              <dt className="text-sm text-text-secondary">{stat.label}</dt>
              <dd className="mt-2 text-2xl font-bold font-mono text-text-primary">{stat.value}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-16 max-w-3xl">
          <p className="mb-3 text-sm font-mono uppercase tracking-wider text-accent-blue">{proof.eyebrow}</p>
          <h2 id="trust-title" className="text-2xl font-bold tracking-tight text-text-primary sm:text-3xl">{proof.title}</h2>
          <p className="mt-3 text-base leading-7 text-text-secondary">{proof.body}</p>
        </div>

        <div className="mt-8 grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
          {proof.items.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.title} className="rounded-2xl border border-border-default bg-bg-primary/60 p-6">
                <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl border border-border-default bg-bg-secondary text-accent-blue">
                  <Icon size={20} aria-hidden="true" />
                </div>
                <h3 className="mb-3 text-xl font-semibold text-text-primary">{item.title}</h3>
                <p className="text-sm leading-7 text-text-secondary">{item.body}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
