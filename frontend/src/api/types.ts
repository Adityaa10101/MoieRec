/**
 * frontend/src/api/types.ts
 * Typed API response shapes matching the backend MovieOut schema.
 * Honesty contract enforced: match_percent and explanation are always null.
 */

export interface CastMember {
  name: string;
  character: string | null;
}

export interface ApiMovie {
  movie_id: number;
  tmdb_id: number | null;
  title: string;
  year: number | null;
  genres: string[];
  overview: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
  runtime: number | null;         // minutes
  vote_average: number | null;    // TMDB rating
  tagline: string | null;
  cast: CastMember[];
  directors: string[];
  train_positive_count: number | null;
  rank: number | null;
  score: null;                    // always null — no personalization
  match_percent: null;            // always null — honesty contract
  reason_codes: string[];
  explanation: null;              // always null
  source: 'popularity';
}

export interface RecommendationRow {
  id: string;
  title: string;
  subtitle: string;
  movies: ApiMovie[];
}

export interface HomeResponse {
  hero: ApiMovie | null;
  rows: RecommendationRow[];
}
