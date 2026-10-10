import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
    watchedAndDroppedIds,
    isWatchedOrDropped,
    isOnboardingOpen,
    setIsOnboardingOpen,
    onboardingDismissed,
    avoidedGenres,
  } = useUserTaste();

  const [homeData, setHomeData] = useState<HomeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSlowLoading, setIsSlowLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isOffline, setIsOffline] = useState(false);

  // Personalized feed state
  const [personalizedRows, setPersonalizedRows] = useState<ApiRecommendationRow[]>([]);
  const [personalizedLoading, setPersonalizedLoading] = useState(false);
  const [personalizedError, setPersonalizedError] = useState(false);

  // WhyThis modal — opens only for cards with real explanation evidence
  const [selectedMovieForWhyThis, setSelectedMovieForWhyThis] = useState<ApiMovie | null>(null);

  // Avoided genres set for display-only filtering
  const avoidedSet = useMemo(() => {
    return new Set(avoidedGenres.map((g) => g.toLowerCase()));
  }, [avoidedGenres]);

  const hasAvoidedGenre = useCallback(
    (m: ApiMovie): boolean => {
      if (!m.genres || m.genres.length === 0 || avoidedSet.size === 0) return false;
      return m.genres.some((g) => avoidedSet.has(g.toLowerCase()));
    },
    [avoidedSet],
  );

  // Onboarding prompt on first visit when < 3 likes exist and not dismissed
  useEffect(() => {
    if (validLikedIds.length < 3 && !onboardingDismissed) {
      setIsOnboardingOpen(true);
    }
  }, [validLikedIds.length, onboardingDismissed, setIsOnboardingOpen]);

  // Load standard popularity home feed with cold-start timeout (>=70s) and auto-retry once
  const loadHomeFeed = useCallback(async () => {
    setLoading(true);
    setHasError(false);
    setIsSlowLoading(false);

    const slowTimer = setTimeout(() => {
      setIsSlowLoading(true);
    }, 8000);

    const maxAttempts = 2; // Initial attempt + 1 auto-retry on failure
    let lastError: unknown = null;

    try {
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          const data = await fetchHome(undefined, 75000);
          setHomeData(data);
          setIsOffline(false);
          setHasError(false);
          return;
        } catch (err: unknown) {
          lastError = err;
          if (err instanceof Error && err.name === 'AbortError' && !err.message.includes('timed out')) {
            return;
          }
          if (attempt < maxAttempts) {
            console.warn(`Home feed attempt ${attempt} failed, auto-retrying...`, err);
            await new Promise((resolve) => setTimeout(resolve, 1500));
          }
        }
      }

      console.error('All Home feed attempts failed:', lastError);
      setHasError(true);
      setIsOffline(true);
    } finally {
      clearTimeout(slowTimer);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHomeFeed();
  }, [loadHomeFeed]);

  // Fetch personalized feed (debounced ~400ms, cancellable, reacts to likes/dislikes/watch status)
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
        const excludeIds = Array.from(new Set([...validDislikedIds, ...watchedAndDroppedIds]));
        const resp = await fetchPersonalizedHome(
          validLikedIds,
          excludeIds,
          30,
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
  }, [validLikedIds, validDislikedIds, watchedAndDroppedIds]);

  // Build a mock ApiMovie for the hero from HERO_MOVIE when offline
  const mockHeroAsApi: ApiMovie = useMemo(
    () => ({
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
    }),
    [],
  );

  // Convert mock rows to API shape for offline fallback
  const mockRowsAsApi = useMemo(
    () =>
      MOCK_RECOMMENDATION_ROWS.map((row) => ({
        id: row.id,
        title: row.title.replace(
          /Because you liked.*|Neural.*|Trending.*|Cluster.*|Archival.*/,
          'Popular Films',
        ),
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
      })),
    [],
  );

  const displayHero = useMemo(
    () => homeData?.hero ?? (isOffline ? mockHeroAsApi : null),
    [homeData?.hero, isOffline, mockHeroAsApi],
  );

  const displayRows = useMemo(
    () => homeData?.rows ?? (isOffline ? mockRowsAsApi : []),
    [homeData?.rows, isOffline, mockRowsAsApi],
  );

  // Hero candidates: prioritize personalized feed, fall back to popularity feed for guests or failed/empty personalized requests
  const { candidates: heroCandidates, isFromPersonalizedFeed } = useMemo(() => {
    if (!personalizedError && personalizedRows.length > 0) {
      const pickedRow = personalizedRows.find((r) => r.id === 'row-personalized-picked');
      const otherRows = personalizedRows.filter((r) => r.id !== 'row-personalized-picked');
      const combined = [
        ...(pickedRow ? pickedRow.movies : []),
        ...otherRows.flatMap((r) => r.movies),
      ];
      const seen = new Set<number>();
      const unique: ApiMovie[] = [];
      for (const m of combined) {
        if (!seen.has(m.movie_id)) {
          seen.add(m.movie_id);
          unique.push(m);
        }
      }
      if (unique.length > 0) {
        return { candidates: unique, isFromPersonalizedFeed: true };
      }
    }

    // Guest, failed, or empty picks fallback: popularity feed
    const popMovies = [
      ...(displayHero ? [displayHero] : []),
      ...displayRows.flatMap((r) => r.movies),
    ];
    const seen = new Set<number>();
    const unique: ApiMovie[] = [];
    for (const m of popMovies) {
      if (!seen.has(m.movie_id)) {
        seen.add(m.movie_id);
        unique.push(m);
      }
    }
    return { candidates: unique, isFromPersonalizedFeed: false };
  }, [personalizedError, personalizedRows, displayHero, displayRows]);

  // Top ~7 movie IDs shown in the hero (exclude avoided genres and watched/dropped)
  const filteredHeroCandidates = useMemo(() => {
    const valid = heroCandidates.filter(
      (m) => !hasAvoidedGenre(m) && !isWatchedOrDropped(m.movie_id),
    );
    // Edge case: if filtering leaves fewer than 2 hero candidates, use the existing static hero; never produce an empty Home.
    if (valid.length < 2) {
      if (displayHero && !isWatchedOrDropped(displayHero.movie_id)) return [displayHero];
      return valid.length > 0 ? valid : (displayHero ? [displayHero] : heroCandidates.slice(0, 1));
    }
    return valid;
  }, [heroCandidates, hasAvoidedGenre, isWatchedOrDropped, displayHero]);

  // The hero label is derived strictly from the actual source of the candidates (personalized feed vs popularity fallback).
  // If the personalized request fails or returns empty, the label is false ("Popular right now"), regardless of like count.
  const isPersonalized = useMemo(() => {
    if (!isFromPersonalizedFeed || personalizedError || personalizedRows.length === 0) {
      return false;
    }
    if (filteredHeroCandidates.length < 2 && displayHero) {
      return false;
    }
    return filteredHeroCandidates.some((m) => m.source !== 'popularity');
  }, [isFromPersonalizedFeed, personalizedError, personalizedRows.length, filteredHeroCandidates, displayHero]);

  const heroMovieIds = useMemo(() => {
    return new Set(filteredHeroCandidates.slice(0, 7).map((m) => m.movie_id));
  }, [filteredHeroCandidates]);

  // Pool of popularity movies for backfilling popularity rows only
  const popularityPool = useMemo(() => {
    const seen = new Set<number>();
    const unique: ApiMovie[] = [];
    for (const r of displayRows) {
      for (const m of r.movies) {
        if (!seen.has(m.movie_id) && !hasAvoidedGenre(m) && !isWatchedOrDropped(m.movie_id)) {
          seen.add(m.movie_id);
          unique.push(m);
        }
      }
    }
    return unique;
  }, [displayRows, hasAvoidedGenre, isWatchedOrDropped]);

  // Exclude avoided genres, watched/dropped, and hero movie IDs
  // For rows labeled personalized/CF: backfill ONLY from deeper results of that same ranked list. Never mix popularity items into a personalized row. If exhausted, show a shorter row.
  // For popularity rows: backfill from the popularity pool.
  const filterAndBackfillRow = useCallback(
    (row: ApiRecommendationRow, isFirstRow: boolean, isPersonalizedRow: boolean): ApiRecommendationRow => {
      const targetCount = 20;
      const validMovies = row.movies.filter((m) => {
        if (hasAvoidedGenre(m)) return false;
        if (isWatchedOrDropped(m.movie_id)) return false;
        if (isFirstRow && heroMovieIds.has(m.movie_id)) return false;
        return true;
      });

      // 1. Personalized / CF rows: backfill strictly from deeper results of that same ranked list
      // Never mix popularity items into a personalized row. If list is exhausted, show shorter row.
      if (isPersonalizedRow) {
        return {
          ...row,
          movies: validMovies.slice(0, targetCount),
        };
      }

      // 2. Popularity rows: if full, slice and return
      if (validMovies.length >= targetCount) {
        return {
          ...row,
          movies: validMovies.slice(0, targetCount),
        };
      }

      // Backfill popularity row from popularityPool
      const seen = new Set<number>([
        ...(isFirstRow ? Array.from(heroMovieIds) : []),
        ...validMovies.map((m) => m.movie_id),
      ]);
      const backfilled = [...validMovies];

      for (const cand of popularityPool) {
        if (!seen.has(cand.movie_id)) {
          seen.add(cand.movie_id);
          backfilled.push(cand);
          if (backfilled.length === targetCount) {
            break;
          }
        }
      }

      return {
        ...row,
        movies: backfilled,
      };
    },
    [hasAvoidedGenre, heroMovieIds, popularityPool, isWatchedOrDropped],
  );

  return (
    <div className="relative min-h-screen">
      {/* Demo offline banner */}
      {isOffline && !hasError && <DemoBanner />}

      {/* Failure State with Retry button */}
      {hasError && !homeData ? (
        <div className="relative pt-32 pb-24 min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
          <div className="max-w-md w-full p-8 rounded-2xl bg-[#14151b] border border-white/10 shadow-2xl space-y-6">
            <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-mono text-xl mx-auto">
              !
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-serif text-white font-bold">Unable to load recommendations</h2>
              <p className="text-slate-400 text-sm leading-relaxed">
                The recommender backend is temporarily unavailable or still warming up.
              </p>
            </div>
            <button
              onClick={() => loadHomeFeed()}
              className="w-full py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-[#0d0e12] font-semibold text-sm transition-all cursor-pointer shadow-lg shadow-amber-500/20 active:scale-95"
            >
              Retry Connection
            </button>
          </div>
        </div>
      ) : loading ? (
        /* Cold-Start Loading State: Shimmer Dark Skeleton with 8s Server Wake Message */
        <div className="relative pt-24 pb-16 min-h-[820px] lg:min-h-[880px] flex items-center justify-center bg-[#0d0e12] overflow-hidden">
          {/* Subtle Shimmer background */}
          <div className="absolute inset-0 bg-[#121317] animate-shimmer" />
          <div className="relative z-10 w-full max-w-7xl mx-auto px-6 sm:px-12 space-y-6 pt-12">
            {isSlowLoading ? (
              <div className="flex items-center gap-2.5 px-4 py-2 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-400 font-mono text-xs w-fit animate-in fade-in duration-500 shadow-lg backdrop-blur-md">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping inline-block" />
                <span>Waking up the server, this can take up to a minute on first load.</span>
              </div>
            ) : (
              <div className="h-6 w-32 bg-white/10 rounded-full animate-pulse" />
            )}
            <div className="h-4 w-48 bg-white/10 rounded animate-pulse" />
            <div className="h-16 w-3/4 max-w-2xl bg-white/10 rounded-lg animate-pulse" />
            <div className="flex gap-2">
              <div className="h-7 w-20 bg-white/5 rounded-full animate-pulse" />
              <div className="h-7 w-24 bg-white/5 rounded-full animate-pulse" />
              <div className="h-7 w-20 bg-white/5 rounded-full animate-pulse" />
            </div>
            <div className="space-y-2 max-w-xl">
              <div className="h-4 w-full bg-white/5 rounded animate-pulse" />
              <div className="h-4 w-5/6 bg-white/5 rounded animate-pulse" />
              <div className="h-4 w-2/3 bg-white/5 rounded animate-pulse" />
            </div>
            <div className="pt-2 flex gap-4">
              <div className="h-12 w-36 bg-amber-500/20 rounded-lg animate-pulse" />
              <div className="h-12 w-44 bg-white/10 rounded-lg animate-pulse" />
            </div>
          </div>
        </div>
      ) : displayHero || filteredHeroCandidates.length > 0 ? (
        <HeroSpotlight
          candidateMovies={filteredHeroCandidates}
          fallbackMovie={displayHero}
          isPersonalized={isPersonalized}
          onOpenWhyThis={(m) => {
            if (m.explanation != null) setSelectedMovieForWhyThis(m);
          }}
        />
      ) : null}

      {/* Recommendation Rows */}
      {!hasError && (
        <main className="relative z-20 space-y-16 pb-28 max-w-7xl mx-auto px-6 sm:px-12">
          {/* Notice if personalized request failed */}
          {personalizedError && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-mono flex items-center gap-2">
              <span>ℹ</span>
              <span>Personalized recommendations temporarily unavailable (backend offline)</span>
            </div>
          )}

          {/* Personalized Loading Rows */}
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

          {/* Personalized Rows (rendered with honest labels, row 0 deduplicated against hero) */}
          {personalizedRows.map((row, idx) => {
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
            const isFirstRow = idx === 0;
            const rowToRender = filterAndBackfillRow(row, isFirstRow, true);
            if (rowToRender.movies.length === 0) return null;
            return (
              <RecommendationRow
                key={row.id}
                rowData={rowToRender}
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
            : displayRows.map((row, idx) => {
                const isFirstRow = personalizedRows.length === 0 && idx === 0;
                const rowToRender = filterAndBackfillRow(row, isFirstRow, false);
                if (rowToRender.movies.length === 0) return null;
                return (
                  <RecommendationRow
                    key={row.id}
                    rowData={rowToRender}
                    badge="MODEL 0 (POPULARITY)"
                    onOpenWhyThis={(movie) => setSelectedMovieForWhyThis(movie)}
                  />
                );
              })}
        </main>
      )}

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
