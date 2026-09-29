export const GITHUB_REPO_URL = 'https://github.com/mixyoung/super-dev';
export const GITHUB_API_REPO_URL = 'https://api.github.com/repos/mixyoung/super-dev';
export const DEFAULT_STAR_COUNT = 108;

const STAR_CACHE_KEY = 'super-dev:github-stars';
const STAR_CACHE_TTL_MS = 1000 * 60 * 30;

export function formatStarCount(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(count >= 10000 ? 0 : 1).replace(/\.0$/, '')}k`;
  }
  return String(count);
}

export async function loadGithubStars(): Promise<number> {
  if (typeof window !== 'undefined') {
    const cached = window.sessionStorage.getItem(STAR_CACHE_KEY);
    if (cached) {
      try {
        const parsed = JSON.parse(cached) as { value: number; expiresAt: number };
        if (parsed.expiresAt > Date.now() && Number.isFinite(parsed.value)) {
          return parsed.value;
        }
      } catch {
        window.sessionStorage.removeItem(STAR_CACHE_KEY);
      }
    }
  }

  const response = await fetch(GITHUB_API_REPO_URL, {
    headers: { Accept: 'application/vnd.github+json' },
  });
  if (!response.ok) {
    throw new Error(`GitHub API returned ${response.status}`);
  }

  const data = (await response.json()) as { stargazers_count?: number };
  const stars = Number(data.stargazers_count ?? DEFAULT_STAR_COUNT);

  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(
      STAR_CACHE_KEY,
      JSON.stringify({
        value: stars,
        expiresAt: Date.now() + STAR_CACHE_TTL_MS,
      })
    );
  }

  return stars;
}
