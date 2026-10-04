import React from 'react';
import { Bookmark, ThumbsUp, Play, Sparkles } from 'lucide-react';
import type { ApiMovie } from '../../api/types';
import { useAmbientBackdrop } from '../../context/AmbientBackdropContext';
import { useUserTaste } from '../../context/UserTasteContext';
import { usePopcornCursor } from '../../context/PopcornCursorContext';
import { useRouter } from '../../router/Router';

interface MovieCardProps {
  movie: ApiMovie;
  index?: number;
  onOpenWhyThis?: (movie: ApiMovie) => void;
}

export const MovieCard: React.FC<MovieCardProps> = ({ movie, index = 0, onOpenWhyThis }) => {
  const { setHoveredMovie } = useAmbientBackdrop();
  const { setIsCardHovered } = usePopcornCursor();
  const { isInWatchlist, isLiked, toggleWatchlist, toggleLike } = useUserTaste();
  const { navigate } = useRouter();

  const movieIdStr = String(movie.movie_id);
  const inWatchlist = isInWatchlist(movieIdStr);
  const liked = isLiked(movieIdStr);

  // Top N% chip: N = max(1, 100 - match_percent)
  const topPercent = movie.match_percent != null ? Math.max(1, 100 - movie.match_percent) : null;

  // Adapt to the shape that context expects (local state only, no scores)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const asContextMovie = (): any => ({
    id: movieIdStr,
    movie_id: movie.movie_id,
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
    reason_codes: movie.reason_codes,
  });

  const handleMouseEnter = () => {
    setHoveredMovie(asContextMovie());
    setIsCardHovered(true);
  };

  const handleMouseLeave = () => {
    setHoveredMovie(null);
    setIsCardHovered(false);
  };

  const handleCardClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    navigate(`/movie/${movie.movie_id}`);
  };

  return (
    <div
      onClick={handleCardClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group relative flex-shrink-0 w-60 rounded-xl bg-[#1a1b20] border border-white/10 hover:border-amber-500/60 transition-all duration-300 hover:shadow-[0_20px_40px_-8px_rgba(0,0,0,0.85),0_0_20px_rgba(245,158,11,0.12)] hover:-translate-y-1.5 hover:scale-[1.03] hover:z-30 cursor-pointer flex flex-col overflow-hidden"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* 2:3 Poster */}
      <div className="aspect-[2/3] w-full overflow-hidden rounded-t-xl relative bg-[#121317]">
        {movie.poster_url ? (
          <img
            src={movie.poster_url}
            alt={movie.title}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        ) : (
          /* Placeholder when no poster — no broken image icon */
          <div className="w-full h-full flex flex-col items-center justify-center gap-2 bg-[#1a1b20] text-slate-600">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 4v16M17 4v16M3 8h4m10 0h4M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
            <span className="text-[10px] font-mono uppercase tracking-wider">No Poster</span>
          </div>
        )}

        {/* Top N% pick Chip */}
        {topPercent != null && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (onOpenWhyThis && movie.explanation) onOpenWhyThis(movie);
            }}
            className="absolute top-2.5 left-2.5 z-10 px-2 py-0.5 rounded-md bg-amber-500 text-black text-[10px] font-mono font-bold shadow-md hover:bg-amber-400 transition-colors flex items-center gap-1 cursor-pointer"
            title="Relative rank among candidates for your picks, not a probability"
          >
            <Sparkles className="w-2.5 h-2.5" />
            <span>Top {topPercent}% pick</span>
          </button>
        )}

        {/* Watchlist button */}
        <button
          onClick={(e) => { e.stopPropagation(); toggleWatchlist(asContextMovie()); }}
          className={`absolute top-2.5 right-2.5 z-10 w-7 h-7 rounded-full flex items-center justify-center transition-all ${
            inWatchlist
              ? 'bg-amber-500 text-[#0d0e12]'
              : 'bg-black/60 text-slate-300 hover:text-white hover:bg-black/80'
          }`}
          title={inWatchlist ? 'On Watchlist' : 'Add to Watchlist'}
        >
          <Bookmark className={`w-3.5 h-3.5 ${inWatchlist ? 'fill-current' : ''}`} />
        </button>

        <div className="absolute inset-0 bg-gradient-to-t from-[#1a1b20] via-transparent to-transparent opacity-90" />
      </div>

      {/* Metadata */}
      <div className="p-4 space-y-2 flex-1 flex flex-col justify-between bg-[#1a1b20]">
        <div>
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>
              {movie.year}
              {movie.directors?.[0] && ` • ${movie.directors[0]}`}
            </span>
            {/* TMDB rating — labelled honestly, no fake match score */}
            {movie.vote_average != null && movie.vote_average > 0 && (
              <span className="text-amber-400 font-medium">★ {movie.vote_average.toFixed(1)}</span>
            )}
          </div>

          <h3 className="font-serif text-base text-white font-semibold truncate group-hover:text-amber-400 transition-colors mt-1">
            {movie.title}
          </h3>

          {movie.overview && (
            <p className="text-xs text-slate-400 line-clamp-2 mt-1 transition-opacity duration-200">
              {movie.overview}
            </p>
          )}
        </div>

        <div className="pt-2 flex items-center justify-between border-t border-white/10 mt-auto">
          <span className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">
            {movie.genres[0] || ''}
          </span>

          <div className="flex items-center gap-1.5 text-slate-400">
            {/* Why This Button (only if explanation exists) */}
            {movie.explanation != null && onOpenWhyThis && (
              <button
                onClick={(e) => { e.stopPropagation(); onOpenWhyThis(movie); }}
                className="w-7 h-7 rounded-md hover:bg-white/10 flex items-center justify-center text-amber-400/80 hover:text-amber-400 transition-colors"
                title="Why recommended? (Explainability Breakdown)"
              >
                <Sparkles className="w-3.5 h-3.5" />
              </button>
            )}

            <button
              onClick={(e) => { e.stopPropagation(); navigate(`/movie/${movie.movie_id}`); }}
              className="w-7 h-7 rounded-md hover:bg-white/10 flex items-center justify-center hover:text-amber-400 transition-colors"
              title="View Details"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
            </button>

            <button
              onClick={(e) => { e.stopPropagation(); toggleLike(asContextMovie()); }}
              className={`w-7 h-7 rounded-md hover:bg-white/10 flex items-center justify-center transition-colors ${
                liked ? 'text-amber-400' : 'hover:text-amber-400'
              }`}
              title="Like"
            >
              <ThumbsUp className={`w-3.5 h-3.5 ${liked ? 'fill-amber-400' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
