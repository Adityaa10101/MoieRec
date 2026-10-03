import React from 'react';
import { useRouter, Link } from '../router/Router';
import { ALL_MOCK_MOVIES } from '../data/mockMovies';
import { ArrowLeft, Sparkles, Clock, Calendar, Star, Bookmark } from 'lucide-react';
import { useUserTaste } from '../context/UserTasteContext';

export const MovieDetailPage: React.FC = () => {
  const { params } = useRouter();
  const { isInWatchlist, toggleWatchlist } = useUserTaste();
  const movieId = params.id;

  const movie = ALL_MOCK_MOVIES.find((m) => m.id === movieId) || ALL_MOCK_MOVIES[0];
  const inWatchlist = isInWatchlist(movie.id);

  return (
    <div className="min-h-screen pt-24 pb-20 max-w-6xl mx-auto px-6 lg:px-12 space-y-12">
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-amber-400 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Return to Curated Feed</span>
      </Link>

      {/* Hero preview for Movie Detail */}
      <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-[#1a1b20]">
        <div className="relative h-80 sm:h-96 w-full">
          <img
            src={movie.backdrop || movie.poster}
            alt={movie.title}
            className="w-full h-full object-cover filter brightness-[0.4] contrast-125"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#1a1b20] via-transparent to-transparent" />
          <div className="absolute bottom-6 left-6 sm:left-10 right-6 space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-amber-500/20 border border-amber-500/40 text-amber-400 text-xs font-mono font-bold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{movie.matchScore}% MATCH FOR YOU</span>
            </div>
            <h1 className="font-serif text-3xl sm:text-5xl font-bold tracking-tight text-white">
              {movie.title}
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 font-mono">
              <span>{movie.director}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" /> {movie.year}
              </span>
              {movie.runtime && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {movie.runtime}
                  </span>
                </>
              )}
              {movie.rating && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1 text-amber-400 font-bold">
                    <Star className="w-3 h-3 fill-amber-400" /> {movie.rating}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="p-6 sm:p-10 space-y-6">
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

          <p className="text-slate-300 text-base sm:text-lg leading-relaxed max-w-3xl">
            {movie.overview}
          </p>

          <div className="pt-4 flex flex-wrap items-center gap-4 border-t border-white/10">
            <button
              onClick={() => toggleWatchlist(movie)}
              className={`px-6 py-3 rounded-lg font-medium text-sm flex items-center gap-2 transition-all ${
                inWatchlist
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                  : 'bg-white/10 hover:bg-white/20 text-white border border-white/20'
              }`}
            >
              <Bookmark className={`w-4 h-4 ${inWatchlist ? 'fill-amber-400' : ''}`} />
              <span>{inWatchlist ? '✓ On Watchlist' : '+ Add to Watchlist'}</span>
            </button>
            <div className="text-xs text-slate-500 italic">
              Full explainability matrix and directorial continuity graphs scheduled for Phase 3.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
