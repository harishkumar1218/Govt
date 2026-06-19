export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function apiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalized}`;
}

export interface PlatformConfig {
  app_name: string;
  eligibility_categories: string[];
  quiz: {
    default_start_hour: number;
    default_start_minute: number;
  };
  essay: {
    practice_node_tags: string[];
  };
  tracks: Record<string, { rag_slug: string; default_stage: string }>;
}

let cachedPlatformConfig: PlatformConfig | null = null;

export async function fetchPlatformConfig(): Promise<PlatformConfig> {
  if (cachedPlatformConfig) return cachedPlatformConfig;
  const res = await fetch(apiUrl('/api/config/'));
  if (!res.ok) throw new Error('Failed to load platform config');
  cachedPlatformConfig = await res.json();
  return cachedPlatformConfig!;
}

export function formatQuizStartTime(
  startsAt: string | null | undefined,
  config?: PlatformConfig | null,
): string {
  if (startsAt) {
    return new Date(startsAt).toLocaleTimeString('en-IN', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  }
  const hour = config?.quiz.default_start_hour ?? 18;
  const minute = config?.quiz.default_start_minute ?? 0;
  const d = new Date();
  d.setHours(hour, minute, 0, 0);
  return d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true });
}
