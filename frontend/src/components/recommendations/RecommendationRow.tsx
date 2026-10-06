import React, { useRef } from 'react';
import { ChevronLeft, ChevronRight, TrendingUp, Clock, Star, Sparkles } from 'lucide-react';
import type { ApiMovie } from '../../api/types';
import { MovieCard } from '../movie/MovieCard';
import { MovieCardSkeleton } from '../common/MovieCardSkeleton';

interface ApiRecommendationRowData {
  id: string;
  title: string;
  subtitle: string;
  movies: ApiMovie[];
}

interface RecommendationRowProps {
  rowData: ApiRecommendationRowData;
  loading?: boolean;
  onOpenWhyThis?: (movie: ApiMovie) => void;
  badge?: string;
}

function getRowIcon(id: string): React.ReactNode {
  if (id.startsWith('row-personalized') || id.startsWith('row-because')) {
    return <Sparkles className="w-4 h-4 text-amber-500" />;
  }
  if (id.includes('scifi')) return <Star className="w-4 h-4 text-amber-500" />;
  if (id.includes('drama')) return <Clock className="w-4 h-4 text-amber-500" />;
  return <TrendingUp className="w-4 h-4 text-amber-500" />;
}

export const RecommendationRow: React.FC<RecommendationRowProps> = ({
  rowData,
  loading,
  onOpenWhyThis,
  badge,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -480 : 480,
        behavior: 'smooth',
      });
    }
  };

  const isPickedForYou = rowData.id.startsWith('row-personalized');
  const isBecauseLiked = rowData.id.startsWith('row-because');

  const defaultBadge = isPickedForYou
    ? 'PERSONALIZED · COLLABORATIVE FILTERING'
    : isBecauseLiked
    ? 'SIMILAR BY GENRES & TAGS'
    : 'MovieLens · Model 0 (Popularity)';

  const displayBadge = badge || defaultBadge;

  return (
    <section className="space-y-4 reveal-on-scroll">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-amber-500 font-mono text-xs tracking-widest uppercase font-semibold">
            {getRowIcon(rowData.id)}
            <span
              className={
                isPickedForYou || isBecauseLiked
                  ? 'px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-amber-400 font-bold'
                  : ''
              }
            >
              {displayBadge}
            </span>
          </div>

          <h2 className="font-serif text-2xl sm:text-3xl text-white font-bold tracking-tight">
            {rowData.title}
          </h2>

          <p className="text-sm text-slate-400 max-w-2xl">{rowData.subtitle}</p>
        </div>

        <div className="flex items-center gap-2 shrink-0 self-end md:self-auto">
          <button
            onClick={() => scroll('left')}
            className="w-9 h-9 rounded-full bg-[#1f1f24] border border-white/10 hover:border-amber-500/80 text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
            aria-label={`Scroll ${rowData.title} left`}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => scroll('right')}
            className="w-9 h-9 rounded-full bg-[#1f1f24] border border-white/10 hover:border-amber-500/80 text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
            aria-label={`Scroll ${rowData.title} right`}
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Movie Slider */}
      <div
        ref={scrollContainerRef}
        className="flex gap-5 overflow-x-auto no-scrollbar scroll-smooth py-4 -my-4 px-1"
        style={{ scrollSnapType: 'x proximity' }}
      >
        {loading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{ scrollSnapAlign: 'start' }}>
                <MovieCardSkeleton />
              </div>
            ))
          : rowData.movies.map((movie, idx) => (
              <div key={movie.movie_id} style={{ scrollSnapAlign: 'start' }}>
                <MovieCard movie={movie} index={idx} onOpenWhyThis={onOpenWhyThis} />
              </div>
            ))}
      </div>
    </section>
  );
};
