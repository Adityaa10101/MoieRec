import React, { useState, useEffect } from 'react';
import { useRouter, Link } from '../router/Router';
import { fetchMovieDetail, fetchSimilarMovies } from '../api/client';
import { ALL_MOCK_MOVIES } from '../data/mockMovies';
import type { ApiMovie } from '../api/types';
import { ArrowLeft, Clock, Calendar, Star, User, ThumbsUp, ThumbsDown, Sparkles } from 'lucide-react';
import { useUserTaste } from '../context/UserTasteContext';
import { RecommendationRow } from '../components/recommendations/RecommendationRow';
import { WhyThisModal } from '../components/feedback/WhyThisModal';
import { WatchStatusControl } from '../components/movie/WatchStatusControl';

function SkeletonDetail() {
  return (
    <div className="space-y-8 animate-pulse">
      <div className="rounded-2xl overflow-hidden border border-white/10 bg-[#1a1b20]">
        <div className="h-80 sm:h-[420px] lg:h-[480px] w-full bg-[#23252b]" />
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
  const {
    isLiked,
    isDisliked,
    toggleLike,
    toggleDislike,
    validLikedIds,
  } = useUserTaste();

  const rawId = params.id;
  const numericId = rawId ? parseInt(rawId, 10) : null;

  const [movie, setMovie] = useState<ApiMovie | null>(null);
  const [similarMovies, setSimilarMovies] = useState<ApiMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showWhyThis, setShowWhyThis] = useState(false);

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
  }, [numericId]);

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
  const liked = movie ? isLiked(movieIdStr) : false;
  const disliked = movie ? isDisliked(movieIdStr) : false;

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
    explanation: movie.explanation,
  }) : null;

  const runtimeStr = movie?.runtime
    ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
    : null;

  const rawBackdrop = movie?.backdrop_url || movie?.poster_url;
  // Ensure w1280 TMDB backdrop size if a smaller size is returned
  const backdropUrl = rawBackdrop ? rawBackdrop.replace(/\/w\d+\//, '/w1280/') : null;

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
          <div className="relative h-80 sm:h-[420px] lg:h-[480px] w-full overflow-hidden bg-[#16171c]">
            {backdropUrl ? (
              <img
                src={backdropUrl}
                alt={movie.title}
                loading="eager"
                className="w-full h-full object-cover opacity-100 transition-all duration-300"
                style={{
                  objectPosition: 'center 22%',
                  filter: 'brightness(1.1) saturate(1.05)',
                }}
              />
            ) : (
              <div className="w-full h-full bg-[#23252b]" />
            )}

            {/* a) Bottom fade: roughly bottom 35-40% blending into card background (#1a1b20) */}
            <div
              className="absolute bottom-0 left-0 right-0 h-[38%] pointer-events-none z-[1]"
              style={{
                background:
                  'linear-gradient(to top, #1a1b20 0%, rgba(26, 27, 32, 0.85) 45%, rgba(26, 27, 32, 0) 100%)',
              }}
            />

            {/* b) Light left scrim for title/meta text contrast without darkening top of image */}
            <div
              className="absolute inset-0 pointer-events-none z-[1]"
              style={{
                background:
                  'linear-gradient(to right, rgba(15, 16, 20, 0.6) 0%, rgba(15, 16, 20, 0.2) 35%, rgba(15, 16, 20, 0) 65%)',
              }}
            />

            <div className="absolute bottom-6 left-6 sm:left-10 right-6 space-y-3 z-10">
              {/* No fake match score */}
              <h1
                className="font-serif text-3xl sm:text-5xl font-bold tracking-tight text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.95)]"
                style={{ textShadow: '0 2px 10px rgba(0, 0, 0, 0.85), 0 1px 3px rgba(0, 0, 0, 0.9)' }}
              >
                {movie.title}
              </h1>
              <div
                className="flex flex-wrap items-center gap-4 text-xs sm:text-sm text-slate-200 font-mono drop-shadow-[0_1px_4px_rgba(0,0,0,0.95)]"
                style={{ textShadow: '0 1px 4px rgba(0, 0, 0, 0.95)' }}
              >
                {movie.directors?.[0] && (
                  <span className="flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-slate-300" />
                    <span>Dir. {movie.directors[0]}</span>
                  </span>
                )}
                {movie.year && (
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-300" />
                    <span>{movie.year}</span>
                  </span>
                )}
                {runtimeStr && (
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-300" />
                    <span>{runtimeStr}</span>
                  </span>
                )}
                {/* TMDB vote_average — labelled as TMDB rating */}
                {movie.vote_average != null && movie.vote_average > 0 && (
                  <span className="flex items-center gap-1.5 text-amber-400 font-bold">
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    <span>{movie.vote_average.toFixed(1)} TMDB rating</span>
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
              <WatchStatusControl movie={asContextMovie() || movie} variant="detail" />

              {/* Thumbs up/down — local taste signals only */}
              <div className="flex items-center gap-2 ml-1 sm:ml-2 pl-3 sm:pl-4 border-l border-white/15">
                <button
                  type="button"
                  onClick={() => toggleLike(asContextMovie())}
                  aria-label={`Like ${movie.title}`}
                  className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
                    liked
                      ? 'bg-amber-500/20 border-amber-500 text-amber-400 scale-105'
                      : 'bg-[#1a1b20]/80 border-white/15 text-slate-300 hover:text-amber-400 hover:border-amber-500/50'
                  }`}
                  title={liked ? `Unlike ${movie.title}` : `Like ${movie.title}`}
                >
                  <ThumbsUp className={`w-4 h-4 ${liked ? 'fill-amber-400' : ''}`} />
                </button>

                <button
                  type="button"
                  onClick={() => toggleDislike(asContextMovie())}
                  aria-label={`Dislike ${movie.title}`}
                  className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
                    disliked
                      ? 'bg-amber-500/20 border-amber-500 text-amber-400 scale-105'
                      : 'bg-[#1a1b20]/80 border-white/15 text-slate-300 hover:text-amber-400 hover:border-amber-500/50'
                  }`}
                  title={disliked ? `Undo dislike for ${movie.title}` : `Dislike ${movie.title}`}
                >
                  <ThumbsDown className={`w-4 h-4 ${disliked ? 'fill-amber-400' : ''}`} />
                </button>
              </div>

              {/* TMDB attribution inline / Explanation */}
              <div className="flex items-center gap-2 text-xs text-slate-500 italic ml-auto">
                {movie.explanation ? (
                  <div className="flex items-center gap-2 not-italic">
                    <span className="text-amber-400/90 font-medium font-sans">
                      Personalized recommendation
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowWhyThis(true)}
                      className="px-2 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs font-mono flex items-center gap-1 cursor-pointer transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span>Why recommended?</span>
                    </button>
                  </div>
                ) : (
                  <span>
                    Rating data from TMDB.{' '}
                    {validLikedIds.length >= 3
                      ? 'No personalized explanation for this title yet; showing popularity-based info.'
                      : 'Recommendation: popularity-based (Model 0).'}
                  </span>
                )}
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

      {/* WhyThis Explainability Modal */}
      {showWhyThis && movie && (
        <WhyThisModal
          isOpen={showWhyThis}
          onClose={() => setShowWhyThis(false)}
          movie={asContextMovie()}
        />
      )}
    </div>
  );
};
