export interface MovieExplainability {
  directorAffinity: number;
  thematicFit: number;
  audiovisualScore: number;
  naturalLanguageReason: string;
}

export interface Movie {
  id: string;
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
}

export interface RecommendationRowData {
  id: string;
  title: string;
  subtitle: string;
  anchorBadge: string;
  iconType: 'hub' | 'psychology' | 'diamond' | 'trending' | 'archive';
  movies: Movie[];
}
