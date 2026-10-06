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

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, options);
  if (!resp.ok) {
    throw new Error(`API error ${resp.status}: ${resp.statusText}`);
  }
  return resp.json() as Promise<T>;
}

/** GET /home */
export async function fetchHome(signal?: AbortSignal): Promise<HomeResponse> {
  return apiFetch<HomeResponse>('/home', { signal });
}

/** POST /personalized/home */
export async function fetchPersonalizedHome(
  likedMovieIds: number[],
  excludeMovieIds: number[] = [],
  signal?: AbortSignal,
): Promise<PersonalizedHomeResponse> {
  return apiFetch<PersonalizedHomeResponse>('/personalized/home', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      liked_movie_ids: likedMovieIds,
      exclude_movie_ids: excludeMovieIds,
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
