import React from 'react';
import { Bookmark, ThumbsUp, Play, Sparkles } from 'lucide-react';
import type { Movie } from '../../types/movie';
import { useAmbientBackdrop } from '../../context/AmbientBackdropContext';
import { useUserTaste } from '../../context/UserTasteContext';
import { usePopcornCursor } from '../../context/PopcornCursorContext';
import { useRouter } from '../../router/Router';

interface MovieCardProps {
  movie: Movie;
  index?: number;
}

export const MovieCard: React.FC<MovieCardProps> = ({ movie, index = 0 }) => {
  const { setHoveredMovie } = useAmbientBackdrop();
  const { setIsCardHovered } = usePopcornCursor();
  const { isInWatchlist, isLiked, toggleWatchlist, toggleLike } = useUserTaste();
  const { navigate } = useRouter();

  const inWatchlist = isInWatchlist(movie.id);
  const liked = isLiked(movie.id);

  const handleMouseEnter = () => {
    setHoveredMovie(movie);
    setIsCardHovered(true);
  };

  const handleMouseLeave = () => {
    setHoveredMovie(null);
    setIsCardHovered(false);
  };

  const handleCardClick = (e: React.MouseEvent) => {
    // If clicked on an interactive button, do not navigate
    if ((e.target as HTMLElement).closest('button')) {
      return;
    }
    navigate(`/movie/${movie.id}`);
  };

  return (
    <div
      onClick={handleCardClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group relative flex-shrink-0 w-60 rounded-xl bg-[#1a1b20] border border-white/10 hover:border-amber-500/60 transition-all duration-300 hover:shadow-[0_20px_40px_-8px_rgba(0,0,0,0.85),0_0_20px_rgba(245,158,11,0.12)] hover:-translate-y-1.5 hover:scale-[1.03] hover:z-30 cursor-pointer flex flex-col overflow-hidden"
      style={{
        animationDelay: `${index * 40}ms`,
      }}
    >
      {/* 2:3 Aspect Ratio Theatrical Poster */}
      <div className="aspect-[2/3] w-full overflow-hidden rounded-t-xl relative bg-[#121317]">
        <img
          src={movie.poster}
          alt={movie.title}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
        />

        {/* Personalized Match Pill / Badge */}
        <div className="absolute top-2.5 left-2.5 z-10 bg-amber-500 text-[#0d0e12] font-mono text-[11px] font-bold px-2 py-0.5 rounded shadow-md flex items-center gap-1">
          {movie.matchScore >= 95 && <Sparkles className="w-2.5 h-2.5" />}
          <span>{movie.matchBadgeText || `${movie.matchScore}% MATCH`}</span>
        </div>

        {/* Watchlist Quick Bookmark button (Top Right) */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleWatchlist(movie);
          }}
          className={`absolute top-2.5 right-2.5 z-10 w-7 h-7 rounded-full flex items-center justify-center transition-all ${
            inWatchlist
              ? 'bg-amber-500 text-[#0d0e12]'
              : 'bg-black/60 text-slate-300 hover:text-white hover:bg-black/80'
          }`}
          title={inWatchlist ? 'On Watchlist' : 'Add to Watchlist'}
        >
          <Bookmark className={`w-3.5 h-3.5 ${inWatchlist ? 'fill-current' : ''}`} />
        </button>

        {/* Poster Bottom Dark Gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#1a1b20] via-transparent to-transparent opacity-90" />
      </div>

      {/* Movie Metadata Surface */}
      <div className="p-4 space-y-2 flex-1 flex flex-col justify-between bg-[#1a1b20]">
        <div>
          {/* Release Year & Director / Tag */}
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>
              {movie.year} • {movie.director}
            </span>
            {movie.tags?.[0] && (
              <span className="text-amber-400 font-medium truncate max-w-[90px]">
                {movie.tags[0]}
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="font-serif text-base text-white font-semibold truncate group-hover:text-amber-400 transition-colors mt-1">
            {movie.title}
          </h3>

          {/* Synopsis (revealed/expanded on hover) */}
          <p className="text-xs text-slate-400 line-clamp-2 mt-1 transition-opacity duration-200">
            {movie.overview}
          </p>
        </div>

        {/* Bottom Actions Cluster */}
        <div className="pt-2 flex items-center justify-between border-t border-white/10 mt-auto">
          {/* Secondary tag or runtime */}
          <span className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">
            {movie.tags?.[1] || movie.genres[0]}
          </span>

          <div className="flex items-center gap-1.5 text-slate-400">
            {/* Quick Details Action */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/movie/${movie.id}`);
              }}
              className="w-7 h-7 rounded-md hover:bg-white/10 flex items-center justify-center hover:text-amber-400 transition-colors"
              title="Inspect Details"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
            </button>

            {/* Like Action */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleLike(movie);
              }}
              className={`w-7 h-7 rounded-md hover:bg-white/10 flex items-center justify-center transition-colors ${
                liked ? 'text-amber-400' : 'hover:text-amber-400'
              }`}
              title="Like affinity"
            >
              <ThumbsUp className={`w-3.5 h-3.5 ${liked ? 'fill-amber-400' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
