import React, { useRef } from 'react';
import { ChevronLeft, ChevronRight, Layers, Brain, Diamond, TrendingUp, Archive, Sparkles } from 'lucide-react';
import type { RecommendationRowData } from '../../types/movie';
import { MovieCard } from '../movie/MovieCard';

interface RecommendationRowProps {
  rowData: RecommendationRowData;
}

export const RecommendationRow: React.FC<RecommendationRowProps> = ({ rowData }) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = 480;
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  const getSectionIcon = (iconType: string) => {
    switch (iconType) {
      case 'hub':
        return <Layers className="w-4 h-4 text-amber-500" />;
      case 'psychology':
        return <Brain className="w-4 h-4 text-amber-500" />;
      case 'diamond':
        return <Diamond className="w-4 h-4 text-amber-500" />;
      case 'trending':
        return <TrendingUp className="w-4 h-4 text-amber-500" />;
      case 'archive':
        return <Archive className="w-4 h-4 text-amber-500" />;
      default:
        return <Sparkles className="w-4 h-4 text-amber-500" />;
    }
  };

  return (
    <section className="space-y-4 reveal-on-scroll">
      {/* Section Header with Explainability Context and Controls */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1">
          {/* Explainable Anchor Pill / Tag */}
          <div className="flex items-center gap-2 text-amber-500 font-mono text-xs tracking-widest uppercase font-semibold">
            {getSectionIcon(rowData.iconType)}
            <span>{rowData.anchorBadge}</span>
          </div>

          {/* Row Heading */}
          <h2 className="font-serif text-2xl sm:text-3xl text-white font-bold tracking-tight">
            {rowData.title}
          </h2>

          {/* Subtitle / Telemetry Evidence */}
          <p className="text-sm text-slate-400 max-w-2xl">{rowData.subtitle}</p>
        </div>

        {/* Horizontal Navigation Chevron Controls */}
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

      {/* Horizontal Movie Slider Container */}
      <div
        ref={scrollContainerRef}
        className="flex gap-5 overflow-x-auto no-scrollbar scroll-smooth py-4 -my-4 px-1"
        style={{ scrollSnapType: 'x proximity' }}
      >
        {rowData.movies.map((movie, idx) => (
          <div key={movie.id} style={{ scrollSnapAlign: 'start' }}>
            <MovieCard movie={movie} index={idx} />
          </div>
        ))}
      </div>
    </section>
  );
};
