import React from 'react';

import { motion } from 'framer-motion';
import { Play, Bookmark, ThumbsUp, ThumbsDown } from 'lucide-react';
import type { ApiMovie } from '../../api/types';
import { useUserTaste } from '../../context/UserTasteContext';
import { useRouter } from '../../router/Router';

interface HeroSpotlightProps {
  movie: ApiMovie;
  onOpenWhyThis?: (movie: ApiMovie) => void;
}

export const HeroSpotlight: React.FC<HeroSpotlightProps> = ({ movie }) => {
  const { isInWatchlist, isLiked, isDisliked, toggleWatchlist, toggleLike, toggleDislike } = useUserTaste();
  const { navigate } = useRouter();

  // Derive a compatible id string for context functions
  const movieIdStr = String(movie.movie_id);
  const inWatchlist = isInWatchlist(movieIdStr);
  const liked = isLiked(movieIdStr);
  const disliked = isDisliked(movieIdStr);

  // Cast movie to the shape expected by context (local state only)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const asContextMovie = (): any => ({
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
  });

  const runtimeStr = movie.runtime ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m` : null;

  return (
    <section className="relative pt-24 pb-16 min-h-[820px] lg:min-h-[880px] flex items-center justify-center overflow-hidden z-20">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0, scale: 1.05 }}
        animate={{ opacity: 1, scale: 1.0 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        className="absolute inset-0 z-0"
      >
        {movie.backdrop_url ? (
          <img
            src={movie.backdrop_url}
            alt={movie.title}
            loading="lazy"
            className="w-full h-full object-cover object-center filter brightness-[0.42] contrast-125 transition-transform duration-1000 ease-out"
          />
        ) : (
          <div className="w-full h-full bg-[#1a1b20]" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0d0e12] via-[#0d0e12]/80 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0d0e12] via-[#0d0e12]/60 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_40%,rgba(245,158,11,0.12),transparent_70%)]" />
      </motion.div>

      {/* Hero Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-12 w-full pt-12">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl space-y-6"
        >
          {/* Metadata row — NO fake match score */}
          <div className="flex flex-wrap items-center gap-2.5 text-slate-400 font-mono text-xs tracking-wider uppercase">
            {movie.directors?.[0] && (
              <>
                <span>{movie.directors[0]}</span>
                <span className="text-slate-600">•</span>
              </>
            )}
            {movie.year && <span>{movie.year}</span>}
            {runtimeStr && (
              <>
                <span className="text-slate-600">•</span>
                <span>{runtimeStr}</span>
              </>
            )}
            {/* TMDB rating — labelled honestly */}
            {movie.vote_average != null && movie.vote_average > 0 && (
              <>
                <span className="text-slate-600">•</span>
                <span className="text-amber-400 font-bold">
                  ★ {movie.vote_average.toFixed(1)} TMDB
                </span>
              </>
            )}
          </div>

          {/* Title */}
          <h1 className="font-serif text-4xl sm:text-6xl lg:text-7xl text-white leading-none tracking-tight drop-shadow-lg font-bold">
            {movie.title}
          </h1>

          {/* Genre pills */}
          <div className="flex flex-wrap items-center gap-2">
            {movie.genres.map((genre) => (
              <span
                key={genre}
                className="px-3 py-1 rounded-full bg-[#23252b]/80 backdrop-blur-sm border border-white/10 text-slate-300 font-mono text-xs"
              >
                {genre}
              </span>
            ))}
          </div>

          {/* Overview */}
          {movie.overview && (
            <p className="text-slate-300 text-base sm:text-lg leading-relaxed max-w-2xl text-balance">
              {movie.overview}
            </p>
          )}

          {/* CTAs */}
          <div className="pt-2 flex flex-wrap items-center gap-4">
            <button
              onClick={() => navigate(`/movie/${movie.movie_id}`)}
              className="px-7 py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-[#0d0e12] font-sans font-semibold text-sm sm:text-base flex items-center gap-2.5 shadow-lg shadow-amber-500/20 transition-all duration-200 active:scale-95 cursor-pointer"
            >
              <Play className="w-5 h-5 fill-[#0d0e12]" />
              <span>View Movie</span>
            </button>

            <button
              onClick={() => toggleWatchlist(asContextMovie())}
              className={`px-6 py-3 rounded-lg border font-medium text-sm sm:text-base backdrop-blur-md flex items-center gap-2 transition-all duration-200 cursor-pointer ${
                inWatchlist
                  ? 'bg-amber-500/15 border-amber-500/60 text-amber-400 hover:bg-amber-500/25'
                  : 'bg-[#1f1f24]/70 hover:bg-[#23252b] border-white/15 hover:border-amber-500/50 text-white'
              }`}
            >
              <Bookmark className={`w-4 h-4 ${inWatchlist ? 'fill-amber-400' : ''}`} />
              <span>{inWatchlist ? '✓ On Watchlist' : '+ Add to Watchlist'}</span>
            </button>

            {/* Thumbs up/down — local taste signals only */}
            <div className="flex items-center gap-2 ml-1 sm:ml-2 pl-3 sm:pl-4 border-l border-white/15">
              <button
                onClick={() => toggleLike(asContextMovie())}
                className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer ${
                  liked
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400 scale-105'
                    : 'bg-[#1a1b20]/70 border-white/10 text-slate-400 hover:text-amber-400 hover:border-amber-500/50'
                }`}
                title="Like"
              >
                <ThumbsUp className={`w-4 h-4 ${liked ? 'fill-amber-400' : ''}`} />
              </button>

              <button
                onClick={() => toggleDislike(asContextMovie())}
                className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer ${
                  disliked
                    ? 'bg-red-500/20 border-red-500 text-red-400'
                    : 'bg-[#1a1b20]/70 border-white/10 text-slate-400 hover:text-red-400 hover:border-red-500/50'
                }`}
                title="Dislike"
              >
                <ThumbsDown className="w-4 h-4" />
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
