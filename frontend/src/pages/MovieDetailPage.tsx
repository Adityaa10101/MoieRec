import React, { useState, useEffect } from 'react';
import { useRouter, Link } from '../router/Router';
import { fetchMovieDetail, fetchSimilarMovies } from '../api/client';
import { ALL_MOCK_MOVIES } from '../data/mockMovies';
import type { ApiMovie } from '../api/types';
import { ArrowLeft, Clock, Calendar, Star, Bookmark, User } from 'lucide-react';
import { useUserTaste } from '../context/UserTasteContext';
import { RecommendationRow } from '../components/recommendations/RecommendationRow';

function SkeletonDetail() {
  return (
    <div className="space-y-8 animate-pulse">
      <div className="rounded-2xl overflow-hidden border border-white/10 bg-[#1a1b20]">
        <div className="h-80 sm:h-96 w-full bg-[#23252b]" />
        <div className="p-6 sm:p-10 space-y-4">
          <div className="flex gap-2">
            {[1,2,3].map(i => <div key={i} className="h-6 w-20 bg-white/10 rounded-full" />)}
          </div>
          <div className="h-24 w-full bg-white/5 rounded" />
        </div>
      </div>
    </div>
  );
}

export const MovieDetailPage: React.FC = () => {
  const { params } = useRouter();
  const { isInWatchlist, toggleWatchlist } = useUserTaste();

  const rawId = params.id;
  const numericId = rawId ? parseInt(rawId, 10) : null;

  const [movie, setMovie] = useState<ApiMovie | null>(null);
  const [similarMovies, setSimilarMovies] = useState<ApiMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!numericId || isNaN(numericId)) return;
    const controller = new AbortController();
    fetchSimilarMovies(numericId, 20, controller.signal)
      .then((items) => setSimilarMovies(items))
      .catch(() => setSimilarMovies([]));
    return () => controller.abort();
  }, [numericId]);

  useEffect(() => {
    if (!numericId || isNaN(numericId)) {
      setError('Invalid movie ID');
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    let mounted = true;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchMovieDetail(numericId, controller.signal);
        if (mounted) setMovie(data);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) {
          // Try mock fallback (by string id match)
          const mockFallback = ALL_MOCK_MOVIES.find((m) => m.id === rawId);
          if (mockFallback) {
            const apiShape: ApiMovie = {
              movie_id: numericId,
              tmdb_id: null,
              title: mockFallback.title,
              year: mockFallback.year,
              genres: mockFallback.genres,
              overview: mockFallback.overview,
              poster_url: mockFallback.poster,
              backdrop_url: mockFallback.backdrop || null,
              runtime: null,
              vote_average: null,
              tagline: null,
              cast: [],
              directors: [mockFallback.director],
              train_positive_count: null,
              rank: null,
              score: null,
              match_percent: null,
              reason_codes: [],
              explanation: null,
              source: 'popularity',
            };
            setMovie(apiShape);
          } else {
            setError('Movie not found.');
          }
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    return () => { mounted = false; controller.abort(); };
  }, [numericId, rawId]);

  const movieIdStr = movie ? String(movie.movie_id) : '';
  const inWatchlist = movie ? isInWatchlist(movieIdStr) : false;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const asContextMovie = (): any => movie ? ({
    id: movieIdStr,
    title: movie.title,
    year: movie.year,
    genres: movie.genres,
    overview: movie.overview || '',
    poster: movie.poster_url || '',
    backdrop: movie.backdrop_url || '',
    matchScore: 0,
    tags: [],
    director: movie.directors?.[0] || '',
  }) : null;

  const runtimeStr = movie?.runtime
    ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
    : null;

  return (
    <div className="min-h-screen pt-24 pb-20 max-w-6xl mx-auto px-6 lg:px-12 space-y-12">
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-amber-400 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Return to Feed</span>
      </Link>

      {loading && <SkeletonDetail />}

      {error && !loading && (
        <div className="rounded-2xl border border-white/10 bg-[#1a1b20] p-12 text-center space-y-3">
          <p className="text-slate-300 text-lg">{error}</p>
          <Link to="/" className="text-amber-400 hover:text-amber-300 text-sm transition-colors">
            ← Back to home
          </Link>
        </div>
      )}

      {!loading && !error && movie && (
        <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-[#1a1b20]">
          {/* Backdrop */}
          <div className="relative h-80 sm:h-96 w-full">
            {movie.backdrop_url ? (
              <img
                src={movie.backdrop_url}
                alt={movie.title}
                loading="lazy"
                className="w-full h-full object-cover filter brightness-[0.4] contrast-125"
              />
            ) : movie.poster_url ? (
              <img
                src={movie.poster_url}
                alt={movie.title}
                loading="lazy"
                className="w-full h-full object-cover object-top filter brightness-[0.4] contrast-125"
              />
            ) : (
              <div className="w-full h-full bg-[#23252b]" />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-[#1a1b20] via-transparent to-transparent" />

            <div className="absolute bottom-6 left-6 sm:left-10 right-6 space-y-3">
              {/* No fake match score */}
              <h1 className="font-serif text-3xl sm:text-5xl font-bold tracking-tight text-white">
                {movie.title}
              </h1>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 font-mono">
                {movie.directors?.[0] && (
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" /> {movie.directors[0]}
                  </span>
                )}
                {movie.year && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> {movie.year}
                  </span>
                )}
                {runtimeStr && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {runtimeStr}
                  </span>
                )}
                {/* TMDB vote_average — labelled as TMDB rating */}
                {movie.vote_average != null && movie.vote_average > 0 && (
                  <span className="flex items-center gap-1 text-amber-400 font-bold">
                    <Star className="w-3 h-3 fill-amber-400" />
                    {movie.vote_average.toFixed(1)} TMDB rating
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-10 space-y-6">
            {/* Genre chips */}
            <div className="flex flex-wrap gap-2">
              {movie.genres.map((g) => (
                <span
                  key={g}
                  className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300 font-mono"
                >
                  {g}
                </span>
              ))}
            </div>

            {/* Overview */}
            {movie.overview && (
              <p className="text-slate-300 text-base sm:text-lg leading-relaxed max-w-3xl">
                {movie.overview}
              </p>
            )}

            {/* Cast */}
            {movie.cast && movie.cast.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-mono uppercase tracking-widest text-slate-500">Cast</h3>
                <div className="flex flex-wrap gap-2">
                  {movie.cast.slice(0, 8).map((c, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-300">
                      {c.name}
                      {c.character && <span className="text-slate-500"> · {c.character}</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="pt-4 flex flex-wrap items-center gap-4 border-t border-white/10">
              <button
                onClick={() => toggleWatchlist(asContextMovie())}
                className={`px-6 py-3 rounded-lg font-medium text-sm flex items-center gap-2 transition-all ${
                  inWatchlist
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                    : 'bg-white/10 hover:bg-white/20 text-white border border-white/20'
                }`}
              >
                <Bookmark className={`w-4 h-4 ${inWatchlist ? 'fill-amber-400' : ''}`} />
                <span>{inWatchlist ? '✓ On Watchlist' : '+ Add to Watchlist'}</span>
              </button>

              {/* TMDB attribution inline */}
              <div className="text-xs text-slate-500 italic">
                Rating data from TMDB. Recommendation: popularity-based (Model 0).
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Content-only Similar Movies Row (D5) */}
      {!loading && movie && similarMovies.length > 0 && (
        <div className="pt-6">
          <RecommendationRow
            rowData={{
              id: `row-similar-${numericId}`,
              title: 'More Like This',
              subtitle: 'Content-only recommendations based on shared genres and tags',
              movies: similarMovies,
            }}
            badge="SIMILAR · CONTENT SIMILARITY"
          />
        </div>
      )}
    </div>
  );
};
