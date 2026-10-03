import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Play, Bookmark, ThumbsUp, ThumbsDown, Sliders, Sparkles } from 'lucide-react';
import type { Movie } from '../../types/movie';
import { useUserTaste } from '../../context/UserTasteContext';
import { useRouter } from '../../router/Router';

interface HeroSpotlightProps {
  movie: Movie;
  onOpenWhyThis: (movie: Movie) => void;
}

export const HeroSpotlight: React.FC<HeroSpotlightProps> = ({ movie, onOpenWhyThis }) => {
  const { isInWatchlist, isLiked, isDisliked, toggleWatchlist, toggleLike, toggleDislike } = useUserTaste();
  const { navigate } = useRouter();

  const inWatchlist = isInWatchlist(movie.id);
  const liked = isLiked(movie.id);
  const disliked = isDisliked(movie.id);

  // Animated match score count-up: 0% -> movie.matchScore (runs once on mount)
  const [displayScore, setDisplayScore] = useState(() => {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return movie.matchScore;
    }
    return 0;
  });

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    const duration = 650; // ms
    const target = movie.matchScore;
    const start = performance.now();

    const animateScore = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(easeProgress * target);
      setDisplayScore(current);

      if (progress < 1) {
        requestAnimationFrame(animateScore);
      } else {
        setDisplayScore(target);
      }
    };

    const animFrame = requestAnimationFrame(animateScore);
    return () => cancelAnimationFrame(animFrame);
  }, [movie.matchScore]);

  return (
    <section className="relative pt-24 pb-16 min-h-[820px] lg:min-h-[880px] flex items-center justify-center overflow-hidden z-20">
      {/* Hero Cinematic Backdrop with smooth entrance */}
      <motion.div
        initial={{ opacity: 0, scale: 1.05 }}
        animate={{ opacity: 1, scale: 1.0 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        className="absolute inset-0 z-0"
      >
        <img
          src={movie.backdrop || movie.poster}
          alt={movie.title}
          className="w-full h-full object-cover object-center filter brightness-[0.42] contrast-125 transition-transform duration-1000 ease-out"
        />
        {/* Multi-stop Dark Radial & Linear Gradients for seamless cinematic bleed */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0d0e12] via-[#0d0e12]/80 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0d0e12] via-[#0d0e12]/60 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_40%,rgba(245,158,11,0.12),transparent_70%)]" />
      </motion.div>

      {/* Hero Editorial Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-12 w-full pt-12">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl space-y-6"
        >
          {/* Dual-segment Explainability Match Chip */}
          <div className="inline-flex flex-wrap items-center rounded-lg overflow-hidden border border-white/10 shadow-xl backdrop-blur-md">
            <div className="bg-amber-500 text-[#0d0e12] px-3.5 py-1.5 flex items-center gap-1.5 font-mono text-xs font-bold tracking-wide">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{displayScore}% MATCH FOR YOU</span>
            </div>
            <div className="bg-[#0d0e12]/90 px-4 py-1.5 text-slate-300 font-mono text-[11px] tracking-wider uppercase">
              {movie.matchReason || 'BECAUSE OF WORLD-BUILDING, PHILOSOPHICAL SCALE & ZIMMER SCORE'}
            </div>
          </div>

          {/* Master Title & Editorial Metadata */}
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2.5 text-slate-400 font-mono text-xs tracking-wider uppercase">
              <span>{movie.director}</span>
              <span className="text-slate-600">•</span>
              <span>{movie.year}</span>
              <span className="text-slate-600">•</span>
              <span className="px-1.5 py-0.5 rounded bg-white/10 text-white font-bold">
                {movie.certificate || 'R'}
              </span>
              <span className="text-slate-600">•</span>
              <span>{movie.runtime || '2h 44m'}</span>
              {movie.formats?.map((fmt) => (
                <React.Fragment key={fmt}>
                  <span className="text-slate-600">•</span>
                  <span className="px-1.5 py-0.5 rounded border border-amber-500/40 text-amber-400 text-[10px]">
                    {fmt}
                  </span>
                </React.Fragment>
              ))}
            </div>

            <h1 className="font-serif text-4xl sm:text-6xl lg:text-7xl text-white leading-none tracking-tight drop-shadow-lg font-bold">
              {movie.title}
            </h1>
          </div>

          {/* Genre Pill Tags */}
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

          {/* Editorial Synopsis */}
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed max-w-2xl text-balance">
            {movie.overview}
          </p>

          {/* CTAs & Micro-Interactions */}
          <div className="pt-2 flex flex-wrap items-center gap-4">
            {/* Primary Amber View Movie Button */}
            <button
              onClick={() => navigate(`/movie/${movie.id}`)}
              className="px-7 py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-[#0d0e12] font-sans font-semibold text-sm sm:text-base flex items-center gap-2.5 shadow-lg shadow-amber-500/20 transition-all duration-200 active:scale-95 cursor-pointer"
            >
              <Play className="w-5 h-5 fill-[#0d0e12]" />
              <span>View Movie</span>
            </button>

            {/* Secondary Outline Add to Watchlist Button */}
            <button
              onClick={() => toggleWatchlist(movie)}
              className={`px-6 py-3 rounded-lg border font-medium text-sm sm:text-base backdrop-blur-md flex items-center gap-2 transition-all duration-200 cursor-pointer ${
                inWatchlist
                  ? 'bg-amber-500/15 border-amber-500/60 text-amber-400 hover:bg-amber-500/25'
                  : 'bg-[#1f1f24]/70 hover:bg-[#23252b] border-white/15 hover:border-amber-500/50 text-white'
              }`}
            >
              <Bookmark className={`w-4 h-4 ${inWatchlist ? 'fill-amber-400' : ''}`} />
              <span>{inWatchlist ? '✓ On Watchlist' : '+ Add to Watchlist'}</span>
            </button>

            {/* Taste Calibration Cluster: Thumbs up, Thumbs down, Why This */}
            <div className="flex items-center gap-2 ml-1 sm:ml-2 pl-3 sm:pl-4 border-l border-white/15">
              <button
                onClick={() => toggleLike(movie)}
                className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer ${
                  liked
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400 scale-105'
                    : 'bg-[#1a1b20]/70 border-white/10 text-slate-400 hover:text-amber-400 hover:border-amber-500/50'
                }`}
                title="More films with this cinematography & pacing"
              >
                <ThumbsUp className={`w-4 h-4 ${liked ? 'fill-amber-400' : ''}`} />
              </button>

              <button
                onClick={() => toggleDislike(movie)}
                className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer ${
                  disliked
                    ? 'bg-red-500/20 border-red-500 text-red-400'
                    : 'bg-[#1a1b20]/70 border-white/10 text-slate-400 hover:text-red-400 hover:border-red-500/50'
                }`}
                title="Less films like this"
              >
                <ThumbsDown className="w-4 h-4" />
              </button>

              <button
                onClick={() => onOpenWhyThis(movie)}
                className="px-3.5 h-11 rounded-lg bg-[#1a1b20]/70 hover:bg-[#23252b] border border-white/10 hover:border-amber-500/50 text-slate-300 hover:text-amber-400 flex items-center gap-1.5 font-mono text-xs tracking-wider uppercase transition-all cursor-pointer"
                title="Inspect Telemetry Breakdown"
              >
                <Sliders className="w-4 h-4 text-amber-500" />
                <span>Why This?</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
