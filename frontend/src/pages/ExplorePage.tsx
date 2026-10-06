import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from '../router/Router';
import {
  Compass,
  ArrowUpDown,
  RotateCcw,
  Film,
  AlertCircle,
  Loader2,
  ChevronDown,
} from 'lucide-react';
import { fetchMetaFilters, fetchPopular } from '../api/client';
import type { ApiMovie, GenreFilter, DecadeFilter } from '../api/types';
import { MovieCardSkeleton } from '../components/common/MovieCardSkeleton';

export const ExplorePage: React.FC = () => {
  // Metadata filter options
  const [genres, setGenres] = useState<GenreFilter[]>([]);
  const [decades, setDecades] = useState<DecadeFilter[]>([]);

  // Active filters
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [selectedDecade, setSelectedDecade] = useState<number | null>(null);
  const [sortOrder, setSortOrder] = useState<'popular' | 'newest' | 'oldest'>('popular');

  // Movies & pagination state
  const [movies, setMovies] = useState<ApiMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const PAGE_SIZE = 24;
  const abortControllerRef = useRef<AbortController | null>(null);

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

  // Fetch initial batch of movies whenever filters or sort changes
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
            genre: selectedGenre || undefined,
            decade: selectedDecade || undefined,
            sort: sortOrder,
            limit: PAGE_SIZE,
            offset,
          },
          controller.signal,
        );

        if (isReset) {
          setMovies(results);
        } else {
          setMovies((prev) => {
            const seen = new Set(prev.map((m) => m.movie_id));
            const fresh = results.filter((m) => !seen.has(m.movie_id));
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
    [selectedGenre, selectedDecade, sortOrder, movies.length],
  );

  // Trigger reset load on filter change
  useEffect(() => {
    loadMovies(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedGenre, selectedDecade, sortOrder]);

  const handleResetFilters = () => {
    setSelectedGenre(null);
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
        {/* Genre Chips */}
        <div className="space-y-2">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Genre
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto pr-1 no-scrollbar">
            <button
              onClick={() => setSelectedGenre(null)}
              className={`px-3 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer whitespace-nowrap ${
                selectedGenre === null
                  ? 'bg-amber-500 text-black font-bold shadow-md'
                  : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white border border-white/5'
              }`}
            >
              All Genres
            </button>
            {genres.map((g) => {
              const active = selectedGenre === g.name;
              return (
                <button
                  key={g.name}
                  onClick={() => setSelectedGenre(active ? null : g.name)}
                  className={`px-3 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                    active
                      ? 'bg-amber-500 text-black font-bold shadow-md'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white border border-white/5'
                  }`}
                >
                  <span>{g.name}</span>
                  <span className={`text-[10px] ${active ? 'text-black/70 font-bold' : 'text-slate-500'}`}>
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
                    key={d.decade}
                    onClick={() => setSelectedDecade(active ? null : d.decade)}
                    className={`px-3 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                      active
                        ? 'bg-amber-500 text-black font-bold shadow-md'
                        : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white border border-white/5'
                    }`}
                  >
                    <span>{d.label}</span>
                    <span className={`text-[10px] ${active ? 'text-black/70 font-bold' : 'text-slate-500'}`}>
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
              No titles match the chosen combination of genre and decade filters.
            </p>
          </div>
          <button
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
            {movies.map((movie) => (
              <Link
                key={movie.movie_id}
                to={`/movie/${movie.movie_id}`}
                className="group relative flex flex-col rounded-xl bg-[#1a1b20] border border-white/10 hover:border-amber-500/60 overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl"
              >
                {/* 2:3 Poster */}
                <div className="aspect-[2/3] w-full bg-[#121317] relative overflow-hidden">
                  {movie.poster_url ? (
                    <img
                      src={movie.poster_url}
                      alt={movie.title}
                      loading="lazy"
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 gap-1">
                      <Film className="w-6 h-6" />
                      <span className="text-[9px] font-mono uppercase">No Poster</span>
                    </div>
                  )}

                  {/* Year badge */}
                  {movie.year && (
                    <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-black/75 backdrop-blur-md text-amber-300 border border-white/10">
                      {movie.year}
                    </span>
                  )}
                </div>

                {/* Metadata */}
                <div className="p-3 flex-1 flex flex-col justify-between space-y-1.5">
                  <h3
                    className="font-serif text-xs font-bold text-white group-hover:text-amber-400 transition-colors line-clamp-2"
                    title={movie.title}
                  >
                    {movie.title}
                  </h3>
                  {movie.genres && movie.genres.length > 0 && (
                    <p className="text-[10px] font-mono text-slate-400 truncate">
                      {movie.genres.slice(0, 2).join(' · ')}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="flex flex-col items-center justify-center gap-2 pt-4">
              <button
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
