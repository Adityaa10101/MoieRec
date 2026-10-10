import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Compass,
  ArrowUpDown,
  RotateCcw,
  AlertCircle,
  Loader2,
  ChevronDown,
  X,
} from 'lucide-react';
import { fetchMetaFilters, fetchPopular } from '../api/client';
import type { ApiMovie, GenreFilter, DecadeFilter } from '../api/types';
import { MovieCard } from '../components/movie/MovieCard';
import { MovieCardSkeleton } from '../components/common/MovieCardSkeleton';
import { useUserTaste } from '../context/UserTasteContext';

function readUrlParams(): { genres: string[]; decade: number | null; sort: 'popular' | 'newest' | 'oldest' } {
  if (typeof window === 'undefined') {
    return { genres: [], decade: null, sort: 'popular' };
  }
  const params = new URLSearchParams(window.location.search);
  const gRaw = params.get('genres') || params.get('genre') || '';
  const parsedGenres = gRaw
    ? gRaw.split(',').map((s) => s.trim()).filter(Boolean)
    : [];
  const dRaw = params.get('decade');
  const parsedDecade = dRaw ? Number(dRaw) : null;
  const sRaw = params.get('sort');
  const parsedSort =
    sRaw === 'newest' || sRaw === 'oldest' || sRaw === 'popular' ? sRaw : 'popular';
  return {
    genres: parsedGenres,
    decade: Number.isInteger(parsedDecade) ? parsedDecade : null,
    sort: parsedSort,
  };
}

export const ExplorePage: React.FC = () => {
  const { avoidedGenres } = useUserTaste();

  // Metadata filter options
  const [genres, setGenres] = useState<GenreFilter[]>([]);
  const [decades, setDecades] = useState<DecadeFilter[]>([]);

  // Active filters initialized from URL query params
  const [selectedGenres, setSelectedGenres] = useState<string[]>(() => readUrlParams().genres);
  const [selectedDecade, setSelectedDecade] = useState<number | null>(() => readUrlParams().decade);
  const [sortOrder, setSortOrder] = useState<'popular' | 'newest' | 'oldest'>(() => readUrlParams().sort);

  // Movies & pagination state
  const [movies, setMovies] = useState<ApiMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const PAGE_SIZE = 24;
  const abortControllerRef = useRef<AbortController | null>(null);

  // Avoided genres to hide (unless user explicitly selected that genre in selectedGenres)
  const effectiveAvoidedSet = useMemo(() => {
    const explicitlySelected = new Set(selectedGenres.map((g) => g.toLowerCase()));
    return new Set(
      avoidedGenres
        .filter((g) => !explicitlySelected.has(g.toLowerCase()))
        .map((g) => g.toLowerCase()),
    );
  }, [avoidedGenres, selectedGenres]);

  // Sync state to URL query string
  const syncToUrl = useCallback(
    (nextGenres: string[], nextDecade: number | null, nextSort: string) => {
      if (typeof window === 'undefined') return;
      const url = new URL(window.location.href);
      if (nextGenres.length > 0) {
        url.searchParams.set('genre', nextGenres.join(','));
        url.searchParams.delete('genres');
      } else {
        url.searchParams.delete('genre');
        url.searchParams.delete('genres');
      }
      if (nextDecade != null) {
        url.searchParams.set('decade', String(nextDecade));
      } else {
        url.searchParams.delete('decade');
      }
      if (nextSort && nextSort !== 'popular') {
        url.searchParams.set('sort', nextSort);
      } else {
        url.searchParams.delete('sort');
      }

      const nextSearch = url.search;
      const currentSearch = window.location.search;
      if (nextSearch !== currentSearch) {
        window.history.pushState(null, '', url.pathname + (nextSearch ? nextSearch : ''));
      }
    },
    [],
  );

  // Listen to browser Back / Forward buttons (popstate)
  useEffect(() => {
    const handlePopState = () => {
      const urlState = readUrlParams();
      setSelectedGenres(urlState.genres);
      setSelectedDecade(urlState.decade);
      setSortOrder(urlState.sort);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Load available genre & decade filter chips from /api/meta/filters
  useEffect(() => {
    let mounted = true;
    fetchMetaFilters()
      .then((data) => {
        if (!mounted) return;
        setGenres(data.genres || []);
        setDecades(data.decades || []);
      })
      .catch((err) => {
        console.error('Failed to load catalog filters', err);
      });

    return () => {
      mounted = false;
    };
  }, []);

  // Fetch initial batch or next page of movies
  const loadMovies = useCallback(
    async (isReset = true) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      if (isReset) {
        setLoading(true);
        setError(null);
      } else {
        setLoadingMore(true);
      }

      const offset = isReset ? 0 : movies.length;

      try {
        const results = await fetchPopular(
          {
            genre: selectedGenres.length > 0 ? selectedGenres.join(',') : undefined,
            decade: selectedDecade || undefined,
            sort: sortOrder,
            limit: PAGE_SIZE,
            offset,
          },
          controller.signal,
        );

        // Filter out avoided genres display-side
        const displayResults = results.filter((m) => {
          if (!m.genres || m.genres.length === 0) return true;
          return !m.genres.some((g) => effectiveAvoidedSet.has(g.toLowerCase()));
        });

        if (isReset) {
          setMovies(displayResults);
        } else {
          setMovies((prev) => {
            const seen = new Set(prev.map((m) => m.movie_id));
            const fresh = displayResults.filter((m) => !seen.has(m.movie_id));
            return [...prev, ...fresh];
          });
        }

        setHasMore(results.length >= PAGE_SIZE);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError('Failed to load movies. Please check your connection and try again.');
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [selectedGenres, selectedDecade, sortOrder, movies.length, effectiveAvoidedSet],
  );

  // Trigger reset load on filter change and sync URL
  useEffect(() => {
    syncToUrl(selectedGenres, selectedDecade, sortOrder);
    loadMovies(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedGenres, selectedDecade, sortOrder]);

  const handleToggleGenre = (genreName: string) => {
    setSelectedGenres((prev) => {
      const exists = prev.some((g) => g.toLowerCase() === genreName.toLowerCase());
      if (exists) {
        return prev.filter((g) => g.toLowerCase() !== genreName.toLowerCase());
      } else {
        return [...prev, genreName];
      }
    });
  };

  const handleClearGenres = () => {
    setSelectedGenres([]);
  };

  const handleResetFilters = () => {
    setSelectedGenres([]);
    setSelectedDecade(null);
    setSortOrder('popular');
  };

  return (
    <div className="min-h-screen pt-28 pb-24 max-w-7xl mx-auto px-6 space-y-8">
      {/* Page Header */}
      <div className="space-y-3 border-b border-white/10 pb-6">
        <div className="flex items-center gap-2.5">
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            MODEL 0 (POPULARITY)
          </span>
          <span className="text-xs text-slate-400 font-mono">
            Popular with MovieLens viewers
          </span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-white font-bold tracking-tight">
          Explore Catalog
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
          Filter and discover 18,259 canonical films ranked by MovieLens viewer ratings and release decade.
        </p>
      </div>

      {/* Filter and Sort Toolbar */}
      <div className="space-y-5 p-5 rounded-2xl bg-[#14151a] border border-white/10">
        {/* Genre Chips - Horizontally scrollable row with Clear action */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Genre {selectedGenres.length > 0 && `(${selectedGenres.length} selected)`}
            </div>
            {selectedGenres.length > 0 && (
              <button
                type="button"
                onClick={handleClearGenres}
                className="text-xs font-mono text-amber-400 hover:text-amber-300 flex items-center gap-1 cursor-pointer transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                <span>Clear</span>
              </button>
            )}
          </div>
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar scroll-smooth py-1 pr-1">
            <button
              type="button"
              onClick={handleClearGenres}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer whitespace-nowrap shrink-0 ${
                selectedGenres.length === 0
                  ? 'bg-amber-500 text-black font-bold shadow-md'
                  : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white border border-white/5'
              }`}
            >
              All Genres
            </button>
            {genres.map((g) => {
              const active = selectedGenres.some(
                (sg) => sg.toLowerCase() === g.name.toLowerCase(),
              );
              return (
                <button
                  type="button"
                  key={g.name}
                  onClick={() => handleToggleGenre(g.name)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 shrink-0 ${
                    active
                      ? 'bg-amber-500 text-black font-bold shadow-md'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white border border-white/5'
                  }`}
                >
                  <span>{g.name}</span>
                  <span
                    className={`text-[10px] ${
                      active ? 'text-black/70 font-bold' : 'text-slate-500'
                    }`}
                  >
                    ({g.count.toLocaleString()})
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Decade Chips + Sort Dropdown */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pt-3 border-t border-white/5">
          {/* Decades */}
          <div className="space-y-1.5 flex-1">
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Decade
            </div>
            <div className="flex flex-wrap gap-1.5 overflow-x-auto no-scrollbar">
              <button
                type="button"
                onClick={() => setSelectedDecade(null)}
                className={`px-3 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer whitespace-nowrap ${
                  selectedDecade === null
                    ? 'bg-amber-500 text-black font-bold shadow-md'
                    : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white border border-white/5'
                }`}
              >
                All Decades
              </button>
              {decades.map((d) => {
                const active = selectedDecade === d.decade;
                return (
                  <button
                    type="button"
                    key={d.decade}
                    onClick={() => setSelectedDecade(active ? null : d.decade)}
                    className={`px-3 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                      active
                        ? 'bg-amber-500 text-black font-bold shadow-md'
                        : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white border border-white/5'
                    }`}
                  >
                    <span>{d.label}</span>
                    <span
                      className={`text-[10px] ${
                        active ? 'text-black/70 font-bold' : 'text-slate-500'
                      }`}
                    >
                      ({d.count.toLocaleString()})
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Sort Controls */}
          <div className="space-y-1.5 shrink-0">
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
              <ArrowUpDown className="w-3 h-3 text-amber-500" />
              <span>Sort By</span>
            </div>
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[#1d1f27] border border-white/10">
              <button
                type="button"
                onClick={() => setSortOrder('popular')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                  sortOrder === 'popular'
                    ? 'bg-amber-500 text-black font-bold shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Most liked
              </button>
              <button
                type="button"
                onClick={() => setSortOrder('newest')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                  sortOrder === 'newest'
                    ? 'bg-amber-500 text-black font-bold shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Newest
              </button>
              <button
                type="button"
                onClick={() => setSortOrder('oldest')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                  sortOrder === 'oldest'
                    ? 'bg-amber-500 text-black font-bold shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Oldest
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Movie Results Grid */}
      {error ? (
        <div className="p-12 rounded-2xl bg-[#14151a] border border-red-500/20 text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto text-red-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="font-serif text-lg font-bold text-white">Error Loading Catalog</h3>
            <p className="text-xs text-slate-400">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => loadMovies(true)}
            className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-all cursor-pointer"
          >
            Retry
          </button>
        </div>
      ) : loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-5">
          {Array.from({ length: 12 }).map((_, i) => (
            <MovieCardSkeleton key={i} />
          ))}
        </div>
      ) : movies.length === 0 ? (
        <div className="p-12 rounded-2xl bg-[#14151a] border border-white/10 text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto text-amber-500">
            <Compass className="w-6 h-6" />
          </div>
          <div className="space-y-1 max-w-sm mx-auto">
            <h3 className="font-serif text-lg font-bold text-white">No Movies Found</h3>
            <p className="text-xs text-slate-400">
              {selectedGenres.length > 0
                ? `No titles match the selected genre filters (${selectedGenres.join(', ')}).`
                : 'No titles match the chosen combination of genre and decade filters.'}
            </p>
          </div>
          <button
            type="button"
            onClick={handleResetFilters}
            className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-all flex items-center gap-1.5 mx-auto cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset filters</span>
          </button>
        </div>
      ) : (
        <div className="space-y-10">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-5">
            {movies.map((movie, idx) => (
              <MovieCard
                key={movie.movie_id}
                movie={movie}
                index={idx}
                className="w-full h-full"
              />
            ))}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="flex flex-col items-center justify-center gap-2 pt-4">
              <button
                type="button"
                onClick={() => loadMovies(false)}
                disabled={loadingMore}
                className="px-6 py-3 rounded-xl bg-[#1a1b20] hover:bg-[#23252b] border border-white/10 hover:border-amber-500/40 text-white text-xs font-mono font-semibold transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-amber-500" />
                    <span>Loading more movies...</span>
                  </>
                ) : (
                  <>
                    <span>Load more</span>
                    <ChevronDown className="w-4 h-4 text-amber-500" />
                  </>
                )}
              </button>
              <span className="text-[11px] font-mono text-slate-500">
                Showing {movies.length} movies
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
