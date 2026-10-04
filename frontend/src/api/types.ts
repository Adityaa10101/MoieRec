/**
 * frontend/src/api/types.ts
 * Typed API response shapes matching the backend MovieOut schema.
 * Honesty contract enforced: match_percent and explanation are always null.
 */

export interface CastMember {
  name: string;
  character: string | null;
}

export interface NearestPickExplanation {
  movie_id: number;
  title: string;
  similarity: number;
}

export interface SharedFeatureExplanation {
  feature: string;
  raw_name: string;
  contribution: number;
  feature_type: string;
}

export interface ComponentsExplanation {
  content: number;
  popularity: number;
  cf?: number;
}

export interface CfPickExplanation {
  movie_id: number;
  title: string;
  similarity: number;
  cooccurrence: number;
}

export interface MovieExplanation {
  nearest_pick: NearestPickExplanation;
  top_shared_features: SharedFeatureExplanation[];
  components: ComponentsExplanation;
  match_percent: number;
  similarity_threshold?: number;
  alpha?: number;
  weights?: { w_c: number; w_f: number; w_p: number };
  cf_pick?: CfPickExplanation;
  reason_labels?: Record<string, string>;
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
  score: number | null;           // personalized score or cosine similarity
  match_percent: number | null;   // relative rank within pool (0-100), not a probability
  reason_codes: string[];
  explanation: MovieExplanation | null;
  source: 'popularity' | 'hybrid_v1' | 'hybrid_v1.1' | 'hybrid_v2' | 'content_similarity';
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

export interface PersonalizedHomeResponse {
  personalized: boolean;
  k: number;
  config_version: string;
  alpha_used?: number | null;
  weights_used?: { w_c: number; w_f: number; w_p: number } | null;
  ignored_ids: number[];
  message?: string | null;
  rows: RecommendationRow[];
}
