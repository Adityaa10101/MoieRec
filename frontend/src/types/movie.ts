export interface MovieExplainability {
  directorAffinity: number;
  thematicFit: number;
  audiovisualScore: number;
  naturalLanguageReason: string;
}

import type { MovieExplanation } from '../api/types';

export interface Movie {
  id: string;
  movie_id?: number;
  tmdb_id?: number | null;
  title: string;
  year: number;
  director: string;
  runtime?: string;
  certificate?: string;
  rating?: number;
  matchScore: number;
  matchBadgeText?: string;
  matchReason?: string;
  anchorTitle?: string;
  genres: string[];
  tags: string[];
  overview: string;
  poster: string;
  backdrop?: string;
  formats?: string[];
  explainability?: MovieExplainability;
  // Phase 2F Personalization fields
  score?: number | null;
  match_percent?: number | null;
  reason_codes?: string[];
  explanation?: MovieExplanation | null;
  source?: 'popularity' | 'hybrid_v1' | 'hybrid_v1.1' | 'hybrid_v2' | 'content_similarity';
}

export interface RecommendationRowData {
  id: string;
  title: string;
  subtitle: string;
  anchorBadge: string;
  iconType: 'hub' | 'psychology' | 'diamond' | 'trending' | 'archive';
  movies: Movie[];
}
