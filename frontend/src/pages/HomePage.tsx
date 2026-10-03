import React, { useState, useEffect } from 'react';
import { HERO_MOVIE, MOCK_RECOMMENDATION_ROWS } from '../data/mockMovies';
import { HeroSpotlight } from '../components/movie/HeroSpotlight';
import { RecommendationRow } from '../components/recommendations/RecommendationRow';
import { WhyThisModal } from '../components/feedback/WhyThisModal';
import { TasteRadarDock } from '../components/feedback/TasteRadarDock';
import { MovieCardSkeleton } from '../components/common/MovieCardSkeleton';
import { fetchHome } from '../api/client';
import type { HomeResponse, ApiMovie } from '../api/types';

// Honesty banner shown when falling back to mock data
const DemoBanner: React.FC = () => (
  <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/20 border border-amber-500/50 text-amber-400 text-xs font-mono font-semibold shadow-lg backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-300">
    <span>⚠</span>
    <span>Demo data (backend offline) — no real recommendations</span>
  </div>
);

export const HomePage: React.FC = () => {
  const [homeData, setHomeData] = useState<HomeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);

  // WhyThis modal — only shown when movie has a non-null explanation (never in Phase 2E.2)
  const [selectedMovieForWhyThis, setSelectedMovieForWhyThis] = useState<ApiMovie | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;

    const load = async () => {
      try {
        const data = await fetchHome(controller.signal);
        if (mounted) {
          setHomeData(data);
          setIsOffline(false);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) {
          setIsOffline(true);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  // Build a mock ApiMovie for the hero from HERO_MOVIE when offline
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mockHeroAsApi: ApiMovie = {
    movie_id: 0,
    tmdb_id: null,
    title: HERO_MOVIE.title,
    year: HERO_MOVIE.year,
    genres: HERO_MOVIE.genres,
    overview: HERO_MOVIE.overview,
    poster_url: HERO_MOVIE.poster,
    backdrop_url: HERO_MOVIE.backdrop || null,
    runtime: null,
    vote_average: null,
    tagline: null,
    cast: [],
    directors: [HERO_MOVIE.director],
    train_positive_count: null,
    rank: 1,
    score: null,
    match_percent: null,
    reason_codes: [],
    explanation: null,
    source: 'popularity',
  };

  // Convert mock rows to API shape for offline fallback
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mockRowsAsApi = MOCK_RECOMMENDATION_ROWS.map((row) => ({
    id: row.id,
    title: row.title.replace(/Because you liked.*|Neural.*|Trending.*|Cluster.*|Archival.*/, 'Popular Films'),
    subtitle: 'Demo data — real recommendations require backend',
    movies: row.movies.map((m): ApiMovie => ({
      movie_id: Math.abs(m.id.split('').reduce((a, c) => a + c.charCodeAt(0), 0)),
      tmdb_id: null,
      title: m.title,
      year: m.year,
      genres: m.genres,
      overview: m.overview,
      poster_url: m.poster,
      backdrop_url: m.backdrop || null,
      runtime: null,
      vote_average: null,
      tagline: null,
      cast: [],
      directors: [m.director],
      train_positive_count: null,
      rank: null,
      score: null,
      match_percent: null,
      reason_codes: [],
      explanation: null,
      source: 'popularity',
    })),
  }));

  const displayHero = homeData?.hero ?? (isOffline ? mockHeroAsApi : null);
  const displayRows = homeData?.rows ?? (isOffline ? mockRowsAsApi : []);

  return (
    <div className="relative min-h-screen">
      {/* Demo offline banner */}
      {isOffline && <DemoBanner />}

      {/* Hero Spotlight */}
      {loading ? (
        <div className="relative pt-24 pb-16 min-h-[820px] lg:min-h-[880px] flex items-center justify-center bg-[#0d0e12]">
          <div className="w-full max-w-7xl mx-auto px-6 sm:px-12 space-y-6">
            <div className="h-3 w-24 bg-white/10 rounded animate-pulse" />
            <div className="h-16 w-96 bg-white/10 rounded animate-pulse" />
            <div className="h-4 w-72 bg-white/5 rounded animate-pulse" />
            <div className="h-24 w-full max-w-xl bg-white/5 rounded animate-pulse" />
          </div>
        </div>
      ) : displayHero ? (
        <HeroSpotlight
          movie={displayHero}
          onOpenWhyThis={(m) => {
            // Only show WhyThis if the movie has a non-null explanation
            // In Phase 2E.2, explanation is always null, so this never fires
            if (m.explanation != null) setSelectedMovieForWhyThis(m);
          }}
        />
      ) : null}

      {/* Recommendation Rows */}
      <main className="relative z-20 space-y-16 pb-28 max-w-7xl mx-auto px-6 sm:px-12">
        {loading
          ? // Skeleton rows
            [1, 2, 3].map((i) => (
              <section key={i} className="space-y-4">
                <div className="space-y-2">
                  <div className="h-3 w-32 bg-white/10 rounded animate-pulse" />
                  <div className="h-7 w-64 bg-white/10 rounded animate-pulse" />
                  <div className="h-3 w-80 bg-white/5 rounded animate-pulse" />
                </div>
                <div className="flex gap-5 overflow-hidden">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <MovieCardSkeleton key={j} />
                  ))}
                </div>
              </section>
            ))
          : displayRows.map((row) => (
              <RecommendationRow key={row.id} rowData={row} />
            ))}
      </main>

      {/* TasteRadarDock — shows local state only, no fake vector */}
      <TasteRadarDock />

      {/* WhyThis modal — only renders when explanation is non-null (never in Phase 2E.2) */}
      {selectedMovieForWhyThis && selectedMovieForWhyThis.explanation != null && (
        <WhyThisModal
          isOpen={!!selectedMovieForWhyThis}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          movie={selectedMovieForWhyThis as any}
          onClose={() => setSelectedMovieForWhyThis(null)}
        />
      )}
    </div>
  );
};
