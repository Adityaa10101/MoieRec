import React, { useState, useEffect } from 'react';
import { HERO_MOVIE, MOCK_RECOMMENDATION_ROWS } from '../data/mockMovies';
import { HeroSpotlight } from '../components/movie/HeroSpotlight';
import { RecommendationRow } from '../components/recommendations/RecommendationRow';
import { WhyThisModal } from '../components/feedback/WhyThisModal';
import { OnboardingModal } from '../components/feedback/OnboardingModal';
import { TasteRadarDock } from '../components/feedback/TasteRadarDock';
import { MovieCardSkeleton } from '../components/common/MovieCardSkeleton';
import { fetchHome, fetchPersonalizedHome } from '../api/client';
import { useUserTaste } from '../context/UserTasteContext';
import type { HomeResponse, ApiMovie, RecommendationRow as ApiRecommendationRow } from '../api/types';

// Honesty banner shown when falling back to mock data
const DemoBanner: React.FC = () => (
  <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/20 border border-amber-500/50 text-amber-400 text-xs font-mono font-semibold shadow-lg backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-300">
    <span>⚠</span>
    <span>Demo data (backend offline) — no real recommendations</span>
  </div>
);

export const HomePage: React.FC = () => {
  const {
    validLikedIds,
    validDislikedIds,
    isOnboardingOpen,
    setIsOnboardingOpen,
    onboardingDismissed,
  } = useUserTaste();

  const [homeData, setHomeData] = useState<HomeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);

  // Personalized feed state
  const [personalizedRows, setPersonalizedRows] = useState<ApiRecommendationRow[]>([]);
  const [personalizedLoading, setPersonalizedLoading] = useState(false);
  const [personalizedError, setPersonalizedError] = useState(false);

  // WhyThis modal — opens only for cards with real explanation evidence
  const [selectedMovieForWhyThis, setSelectedMovieForWhyThis] = useState<ApiMovie | null>(null);

  // Onboarding prompt on first visit when < 3 likes exist and not dismissed
  useEffect(() => {
    if (validLikedIds.length < 3 && !onboardingDismissed) {
      setIsOnboardingOpen(true);
    }
  }, [validLikedIds.length, onboardingDismissed, setIsOnboardingOpen]);

  // Load standard popularity home feed
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

  // Fetch personalized feed (debounced ~400ms, cancellable, reacts to likes/dislikes)
  useEffect(() => {
    if (validLikedIds.length < 3) {
      setPersonalizedRows([]);
      setPersonalizedError(false);
      setPersonalizedLoading(false);
      return;
    }

    setPersonalizedLoading(true);
    setPersonalizedError(false);
    const controller = new AbortController();

    const timer = setTimeout(async () => {
      try {
        const resp = await fetchPersonalizedHome(
          validLikedIds,
          validDislikedIds,
          controller.signal,
        );
        if (resp.personalized && resp.rows && resp.rows.length > 0) {
          setPersonalizedRows(resp.rows);
          setPersonalizedError(false);
        } else {
          setPersonalizedRows([]);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        setPersonalizedError(true);
        setPersonalizedRows([]);
      } finally {
        setPersonalizedLoading(false);
      }
    }, 400);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [validLikedIds, validDislikedIds]);

  // Build a mock ApiMovie for the hero from HERO_MOVIE when offline
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
            if (m.explanation != null) setSelectedMovieForWhyThis(m);
          }}
        />
      ) : null}

      {/* Recommendation Rows */}
      <main className="relative z-20 space-y-16 pb-28 max-w-7xl mx-auto px-6 sm:px-12">
        {/* Notice if personalized request failed (D2: hide rows with small notice, no mock data) */}
        {personalizedError && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-mono flex items-center gap-2">
            <span>ℹ</span>
            <span>Personalized recommendations temporarily unavailable (backend offline)</span>
          </div>
        )}

        {/* Personalized Rows (rendered ABOVE popularity rows with badge) */}
        {personalizedLoading && (
          <section className="space-y-4">
            <div className="space-y-2">
              <div className="h-3 w-32 bg-amber-500/20 rounded animate-pulse" />
              <div className="h-7 w-64 bg-white/10 rounded animate-pulse" />
            </div>
            <div className="flex gap-5 overflow-hidden">
              {Array.from({ length: 5 }).map((_, j) => (
                <MovieCardSkeleton key={j} />
              ))}
            </div>
          </section>
        )}

        {personalizedRows.map((row) => {
          const isPickedForYou = row.id === 'row-personalized-picked';
          let badge: string;
          if (isPickedForYou) {
            const hasContentWeight =
              row.movies.some((m) => (m.explanation?.weights?.w_c ?? 0) > 0) ||
              validLikedIds.length >= 15;
            badge = hasContentWeight
              ? 'PERSONALIZED · COLLABORATIVE FILTERING + CONTENT'
              : 'PERSONALIZED · COLLABORATIVE FILTERING';
          } else {
            badge = 'SIMILAR BY GENRES & TAGS';
          }
          return (
            <RecommendationRow
              key={row.id}
              rowData={row}
              badge={badge}
              onOpenWhyThis={(movie) => setSelectedMovieForWhyThis(movie)}
            />
          );
        })}

        {/* Standard Popularity Rows */}
        {loading
          ? [1, 2, 3].map((i) => (
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
              <RecommendationRow
                key={row.id}
                rowData={row}
                badge="MODEL 0 (POPULARITY)"
                onOpenWhyThis={(movie) => setSelectedMovieForWhyThis(movie)}
              />
            ))}
      </main>

      {/* TasteRadarDock — shows local state only, no fake vector */}
      <TasteRadarDock />

      {/* Onboarding Modal */}
      <OnboardingModal
        isOpen={isOnboardingOpen}
        onClose={() => setIsOnboardingOpen(false)}
      />

      {/* WhyThis modal — renders only from explanation data with real numbers */}
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
