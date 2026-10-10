/**
 * frontend/src/api/client.ts
 * Typed API fetchers using VITE_API_URL (default http://127.0.0.1:8000).
 * Each fetcher uses AbortController so stale requests can be cancelled.
 */

import type {
  ApiMovie,
  HomeResponse,
  PersonalizedHomeResponse,
  MetaFiltersResponse,
  PopularParams,
} from './types';

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  'http://127.0.0.1:8000/api';

export interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number;
}

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { timeoutMs = 75000, signal, ...fetchOptions } = options;

  const controller = new AbortController();
  let timeoutTimer: ReturnType<typeof setTimeout> | undefined;

  if (timeoutMs > 0) {
    timeoutTimer = setTimeout(() => {
      controller.abort(new Error(`Request to ${path} timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  }

  if (signal) {
    if (signal.aborted) {
      controller.abort(signal.reason);
    } else {
      signal.addEventListener('abort', () => controller.abort(signal.reason), { once: true });
    }
  }

  try {
    const resp = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      signal: controller.signal,
    });
    if (!resp.ok) {
      throw new Error(`API error ${resp.status}: ${resp.statusText}`);
    }
    return (await resp.json()) as T;
  } finally {
    if (timeoutTimer) clearTimeout(timeoutTimer);
  }
}

/** GET /home */
export async function fetchHome(signal?: AbortSignal, timeoutMs = 75000): Promise<HomeResponse> {
  return apiFetch<HomeResponse>('/home', { signal, timeoutMs });
}

/** POST /personalized/home */
export async function fetchPersonalizedHome(
  likedMovieIds: number[],
  excludeMovieIds: number[] = [],
  limit = 30,
  signal?: AbortSignal,
): Promise<PersonalizedHomeResponse> {
  return apiFetch<PersonalizedHomeResponse>('/personalized/home', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      liked_movie_ids: likedMovieIds,
      exclude_movie_ids: excludeMovieIds,
      limit,
    }),
    signal,
  });
}

/** GET /movies/{id}/similar */
export async function fetchSimilarMovies(
  movieId: number | string,
  limit = 20,
  signal?: AbortSignal,
): Promise<ApiMovie[]> {
  return apiFetch<ApiMovie[]>(`/movies/${movieId}/similar?limit=${limit}`, { signal });
}

/** GET /movies/{movie_id} */
export async function fetchMovieDetail(
  movieId: number | string,
  signal?: AbortSignal,
): Promise<ApiMovie> {
  return apiFetch<ApiMovie>(`/movies/${movieId}`, { signal });
}

/** GET /movies/batch?ids=1,2,3 (max 100 ids) */
export async function fetchMoviesBatch(
  movieIds: number[],
  signal?: AbortSignal,
): Promise<ApiMovie[]> {
  if (!movieIds || movieIds.length === 0) return [];
  // Slice to max 100 as specified
  const idsStr = movieIds.slice(0, 100).join(',');
  return apiFetch<ApiMovie[]>(`/movies/batch?ids=${encodeURIComponent(idsStr)}`, { signal });
}

/** GET /meta/filters */
export async function fetchMetaFilters(signal?: AbortSignal): Promise<MetaFiltersResponse> {
  return apiFetch<MetaFiltersResponse>('/meta/filters', { signal });
}

/** GET /movies/popular */
export async function fetchPopular(
  params: PopularParams = {},
  signal?: AbortSignal,
): Promise<ApiMovie[]> {
  const qs = new URLSearchParams();
  if (params.genre) qs.set('genre', params.genre);
  if (params.decade != null) qs.set('decade', String(params.decade));
  if (params.year != null) qs.set('year', String(params.year));
  if (params.sort) qs.set('sort', params.sort);
  if (params.limit != null) qs.set('limit', String(params.limit));
  if (params.offset != null) qs.set('offset', String(params.offset));
  const query = qs.toString() ? `?${qs.toString()}` : '';
  return apiFetch<ApiMovie[]>(`/movies/popular${query}`, { signal });
}

/** GET /search?q=&limit= */
export async function fetchSearch(
  q: string,
  limit = 10,
  signal?: AbortSignal,
): Promise<ApiMovie[]> {
  if (q.trim().length < 2) return [];
  const qs = new URLSearchParams({ q: q.trim(), limit: String(limit) });
  return apiFetch<ApiMovie[]>(`/search?${qs.toString()}`, { signal });
}
