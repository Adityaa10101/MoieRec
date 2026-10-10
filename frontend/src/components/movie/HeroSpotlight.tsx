import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { Play, ThumbsUp, ThumbsDown, ChevronLeft, ChevronRight } from 'lucide-react';
import type { ApiMovie } from '../../api/types';
import { useUserTaste } from '../../context/UserTasteContext';
import { useRouter } from '../../router/Router';
import { useHeroRotation } from '../../hooks/useHeroRotation';
import { WatchStatusControl } from './WatchStatusControl';

/**
 * Ensures TMDB backdrop image uses high-res wide backdrop (w1280).
 */
function getHeroBackdropUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.replace(/\/t\/p\/w\d+\//, '/t/p/w1280/');
}

interface HeroSpotlightProps {
  candidateMovies?: ApiMovie[];
  fallbackMovie?: ApiMovie | null;
  movie?: ApiMovie; // backward compatibility
  isPersonalized?: boolean;
  onOpenWhyThis?: (movie: ApiMovie) => void;
}

export const HeroSpotlight: React.FC<HeroSpotlightProps> = ({
  candidateMovies,
  fallbackMovie,
  movie,
  isPersonalized = false,
}) => {
  const { isLiked, isDisliked, toggleLike, toggleDislike, isWatchedOrDropped } =
    useUserTaste();
  const { navigate } = useRouter();

  const heroRef = useRef<HTMLElement>(null);
  const touchStartPosRef = useRef<{ x: number; y: number } | null>(null);

  // Pause ONLY when mouse/pointer is hovering directly over the text/buttons block
  const [isTextHovered, setIsTextHovered] = useState(false);
  const [isHeroFocused, setIsHeroFocused] = useState(false);

  // Pool of candidate movies
  const candidates = useMemo(() => {
    if (candidateMovies && candidateMovies.length > 0) return candidateMovies;
    if (movie) return [movie];
    if (fallbackMovie) return [fallbackMovie];
    return [];
  }, [candidateMovies, movie, fallbackMovie]);

  // Keep latest candidates and taste helpers in refs so handleRotate doesn't change identity on every render
  const candidatesRef = useRef(candidates);
  const isLikedRef = useRef(isLiked);
  const isDislikedRef = useRef(isDisliked);
  const isWatchedOrDroppedRef = useRef(isWatchedOrDropped);
  const isMovieExcluded = useCallback(
    (
      m: ApiMovie,
      checkLiked: (id: string) => boolean = isLikedRef.current,
      checkDisliked: (id: string) => boolean = isDislikedRef.current,
    ): boolean => {
      if (!m.backdrop_url || !m.backdrop_url.trim()) return true;
      if (!m.overview || !m.overview.trim()) return true;
      const midStr = String(m.movie_id);
      return (
        checkLiked(midStr) ||
        checkDisliked(midStr) ||
        isWatchedOrDroppedRef.current(m.movie_id)
      );
    },
    [],
  );

  // Active hero slides state
  const [activeMovies, setActiveMovies] = useState<ApiMovie[]>(() => {
    const valid = candidates
      .filter((m) => !isMovieExcluded(m, isLiked, isDisliked))
      .slice(0, 7);
    if (valid.length > 0) return valid;
    if (fallbackMovie) return [fallbackMovie];
    if (movie) return [movie];
    return candidates.slice(0, 1);
  });

  const activeMoviesRef = useRef(activeMovies);

  useEffect(() => {
    candidatesRef.current = candidates;
    isLikedRef.current = isLiked;
    isDislikedRef.current = isDisliked;
    isWatchedOrDroppedRef.current = isWatchedOrDropped;
    activeMoviesRef.current = activeMovies;
  });

  // Initialize active movies when candidates first become available
  useEffect(() => {
    if (candidates.length > 0) {
      setActiveMovies((prev) => {
        if (prev.length > 0) return prev;
        const valid = candidates.filter((m) => !isMovieExcluded(m)).slice(0, 7);
        if (valid.length > 0) return valid;
        if (fallbackMovie) return [fallbackMovie];
        if (movie) return [movie];
        return candidates.slice(0, 1);
      });
    }
  }, [candidates, isMovieExcluded, fallbackMovie, movie]);

  // Rotation handler: filters out acted-upon movies ONLY at rotation boundary, not mid-slide
  // Stable identity across re-renders (reads from refs)
  const handleRotate = useCallback(
    (targetIndex: number): number => {
      const currentList = activeMoviesRef.current;
      const currentTargetMovie = currentList[targetIndex] ?? currentList[0];

      // Re-filter candidates removing any items the user liked/disliked/saved
      let nextList = candidatesRef.current.filter((m) => !isMovieExcluded(m)).slice(0, 7);
      if (nextList.length === 0) {
        nextList = fallbackMovie ? [fallbackMovie] : (movie ? [movie] : candidatesRef.current.slice(0, 1));
      }

      // Reconcile index of targetMovie in nextList
      let nextIndex = nextList.findIndex((m) => m.movie_id === currentTargetMovie?.movie_id);
      if (nextIndex < 0) {
        nextIndex = Math.min(targetIndex, Math.max(0, nextList.length - 1));
      }

      setActiveMovies(nextList);
      return nextIndex;
    },
    [isMovieExcluded, fallbackMovie, movie],
  );

  const {
    currentIndex,
    rotationKey,
    goTo,
    nextSlide,
    prevSlide,
    isPaused,
    prefersReducedMotion,
  } = useHeroRotation({
    count: activeMovies.length,
    intervalMs: 10000,
    isTextHovered,
    onRotate: handleRotate,
  });

  // Keyboard navigation: ArrowLeft/ArrowRight change slides when hero is focused or hovered
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't hijack arrow keys when typing in input, textarea, or search
      const target = e.target as HTMLElement | null;
      const tagName = target?.tagName?.toLowerCase();
      if (
        tagName === 'input' ||
        tagName === 'textarea' ||
        tagName === 'select' ||
        target?.isContentEditable
      ) {
        return;
      }

      // Only respond if hero has keyboard focus or mouse is over hero
      const isFocusedInHero =
        heroRef.current?.contains(document.activeElement) || isHeroFocused;
      if (!isFocusedInHero) {
        return;
      }

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prevSlide();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        nextSlide();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isHeroFocused, prevSlide, nextSlide]);

  // Touch swipe support on mobile (swiping left = next, right = prev)
  // Only changes slides when horizontal movement is > 50px AND greater than vertical movement
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartPosRef.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
    };
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartPosRef.current) return;
    const deltaX = e.changedTouches[0].clientX - touchStartPosRef.current.x;
    const deltaY = e.changedTouches[0].clientY - touchStartPosRef.current.y;
    touchStartPosRef.current = null;

    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    if (absX > 50 && absX > absY) {
      if (deltaX < 0) {
        nextSlide();
      } else {
        prevSlide();
      }
    }
  };

  // Preload next slide's backdrop image so there is never a blank frame
  useEffect(() => {
    if (activeMovies.length < 2) return;
    const nextIdx = (currentIndex + 1) % activeMovies.length;
    const nextMovie = activeMovies[nextIdx];
    const url = getHeroBackdropUrl(nextMovie?.backdrop_url);
    if (url) {
      const img = new Image();
      img.src = url;
    }
  }, [currentIndex, activeMovies]);

  // Currently active movie
  const activeMovie = activeMovies[currentIndex] ?? activeMovies[0] ?? fallbackMovie ?? movie;

  if (!activeMovie) return null;

  // Derive signals for active movie
  const movieIdStr = String(activeMovie.movie_id);
  const liked = isLiked(movieIdStr);
  const disliked = isDisliked(movieIdStr);

  // Context movie shape
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const asContextMovie = (): any => ({
    id: movieIdStr,
    title: activeMovie.title,
    year: activeMovie.year,
    genres: activeMovie.genres,
    overview: activeMovie.overview || '',
    poster: activeMovie.poster_url || '',
    backdrop: activeMovie.backdrop_url || '',
    matchScore: 0,
    tags: [],
    director: activeMovie.directors?.[0] || '',
  });

  const runtimeStr = activeMovie.runtime
    ? `${Math.floor(activeMovie.runtime / 60)}h ${activeMovie.runtime % 60}m`
    : null;

  return (
    <section
      ref={heroRef}
      tabIndex={0}
      aria-label="Featured movie carousel"
      className="relative pt-24 pb-16 min-h-[820px] lg:min-h-[880px] flex items-center justify-center overflow-hidden z-20 outline-none focus-visible:ring-1 focus-visible:ring-amber-500/30"
      onFocus={() => setIsHeroFocused(true)}
      onBlur={(e) => {
        if (!heroRef.current?.contains(e.relatedTarget as Node)) {
          setIsHeroFocused(false);
        }
      }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Stacked Backdrops with ~1s Crossfade */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none" aria-hidden="true">
        {activeMovies.map((m, idx) => {
          const isActive = idx === currentIndex;
          const backdropUrl = getHeroBackdropUrl(m.backdrop_url);
          return (
            <div
              key={m.movie_id}
              className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${
                isActive ? 'opacity-100' : 'opacity-0'
              }`}
            >
              {backdropUrl ? (
                <img
                  src={backdropUrl}
                  alt=""
                  loading={idx === 0 ? 'eager' : 'lazy'}
                  className="w-full h-full object-cover object-[right_center] transition-transform duration-1000 ease-out"
                  style={{ filter: 'brightness(1.1) saturate(1.05)' }}
                />
              ) : (
                <div className="w-full h-full bg-[#1a1b20]" />
              )}
            </div>
          );
        })}
      </div>

      {/* Overlays: Consolidate into strictly two layers */}
      {/* a) Left-side scrim for text legibility: rgba(0,0,0,0.85) at 0%, rgba(0,0,0,0.5) at 35%, transparent by 65% (right 40% unobscured) */}
      <div
        className="absolute inset-0 pointer-events-none z-[1]"
        style={{
          background:
            'linear-gradient(to right, rgba(0, 0, 0, 0.85) 0%, rgba(0, 0, 0, 0.5) 35%, rgba(0, 0, 0, 0) 65%)',
        }}
      />

      {/* b) Short bottom fade (~20% only) blending cleanly into the page background */}
      <div
        className="absolute bottom-0 left-0 right-0 h-[20%] pointer-events-none z-[1]"
        style={{
          background:
            'linear-gradient(to top, #0d0e12 0%, rgba(13, 14, 18, 0) 100%)',
        }}
      />

      {/* Hero Content — Re-fades / slides in on slide change keyed by movie id */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-12 w-full pt-12">
        <motion.div
          key={activeMovie.movie_id}
          initial={prefersReducedMotion ? false : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={
            prefersReducedMotion
              ? { duration: 0 }
              : { duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }
          }
          className="max-w-3xl space-y-6"
          onPointerEnter={() => setIsTextHovered(true)}
          onPointerLeave={() => setIsTextHovered(false)}
          onPointerCancel={() => setIsTextHovered(false)}
        >
          {/* Honest badge — "Picked for you" when personalized, "Popular right now" when fallback */}
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold tracking-wider uppercase bg-amber-500/15 border border-amber-500/30 text-amber-400">
              {isPersonalized ? 'Picked for you' : 'Popular right now'}
            </span>
          </div>

          {/* Metadata row — NO fake match score, shadow for legibility over bright backdrops */}
          <div className="flex flex-wrap items-center gap-2.5 text-slate-200 font-mono text-xs tracking-wider uppercase drop-shadow-[0_1px_4px_rgba(0,0,0,0.95)] [text-shadow:_0_1px_4px_rgba(0,0,0,0.85)]">
            {activeMovie.directors?.[0] && (
              <>
                <span>{activeMovie.directors[0]}</span>
                <span className="text-slate-400">•</span>
              </>
            )}
            {activeMovie.year && <span>{activeMovie.year}</span>}
            {runtimeStr && (
              <>
                <span className="text-slate-400">•</span>
                <span>{runtimeStr}</span>
              </>
            )}
            {/* TMDB rating — labelled honestly */}
            {activeMovie.vote_average != null && activeMovie.vote_average > 0 && (
              <>
                <span className="text-slate-400">•</span>
                <span className="text-amber-400 font-bold">
                  ★ {activeMovie.vote_average.toFixed(1)} TMDB
                </span>
              </>
            )}
          </div>

          {/* Title */}
          <h1 className="font-serif text-4xl sm:text-6xl lg:text-7xl text-white leading-none tracking-tight drop-shadow-[0_2px_8px_rgba(0,0,0,0.95)] [text-shadow:_0_2px_12px_rgba(0,0,0,0.75)] font-bold">
            {activeMovie.title}
          </h1>

          {/* Genre pills */}
          <div className="flex flex-wrap items-center gap-2">
            {activeMovie.genres.map((genre) => (
              <span
                key={genre}
                className="px-3 py-1 rounded-full bg-[#1f2026]/90 backdrop-blur-sm border border-white/15 text-slate-200 font-mono text-xs"
              >
                {genre}
              </span>
            ))}
          </div>

          {/* Overview — shadow for legibility across bright backgrounds without adding dark fog */}
          {activeMovie.overview && (
            <p className="text-slate-100 text-base sm:text-lg leading-relaxed max-w-2xl text-balance drop-shadow-[0_1px_4px_rgba(0,0,0,0.95)] [text-shadow:_0_1px_5px_rgba(0,0,0,0.85)] font-normal">
              {activeMovie.overview}
            </p>
          )}

          {/* CTAs */}
          <div className="pt-2 flex flex-wrap items-center gap-4">
            <button
              onClick={() => navigate(`/movie/${activeMovie.movie_id}`)}
              className="px-7 py-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-[#0d0e12] font-sans font-semibold text-sm sm:text-base flex items-center gap-2.5 shadow-lg shadow-amber-500/20 transition-all duration-200 active:scale-95 cursor-pointer"
            >
              <Play className="w-5 h-5 fill-[#0d0e12]" />
              <span>View Movie</span>
            </button>

            <WatchStatusControl movie={asContextMovie()} variant="hero" />

            {/* Thumbs up/down — local taste signals only */}
            <div className="flex items-center gap-2 ml-1 sm:ml-2 pl-3 sm:pl-4 border-l border-white/15">
              <button
                type="button"
                onClick={() => toggleLike(asContextMovie())}
                aria-label={`Like ${activeMovie.title}`}
                className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
                  liked
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400 scale-105'
                    : 'bg-[#1a1b20]/80 border-white/15 text-slate-300 hover:text-amber-400 hover:border-amber-500/50'
                }`}
                title={liked ? `Unlike ${activeMovie.title}` : `Like ${activeMovie.title}`}
              >
                <ThumbsUp className={`w-4 h-4 ${liked ? 'fill-amber-400' : ''}`} />
              </button>

              <button
                type="button"
                onClick={() => toggleDislike(asContextMovie())}
                aria-label={`Dislike ${activeMovie.title}`}
                className={`w-11 h-11 rounded-lg border flex items-center justify-center transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
                  disliked
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400 scale-105'
                    : 'bg-[#1a1b20]/80 border-white/15 text-slate-300 hover:text-amber-400 hover:border-amber-500/50'
                }`}
                title={disliked ? `Undo dislike for ${activeMovie.title}` : `Dislike ${activeMovie.title}`}
              >
                <ThumbsDown className={`w-4 h-4 ${disliked ? 'fill-amber-400' : ''}`} />
              </button>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Controls Container: Progress Indicators + Prev/Next Buttons (Bottom-Right) */}
      {activeMovies.length > 1 && (
        <div className="absolute bottom-8 right-6 sm:right-12 z-20 flex items-center gap-3 sm:gap-4">
          {/* Progress Indicators */}
          <div
            className="flex items-center gap-1.5 sm:gap-2"
            role="tablist"
            aria-label="Personalized picks carousel navigation"
          >
            {activeMovies.map((m, idx) => {
              const isActive = idx === currentIndex;
              return (
                <button
                  key={m.movie_id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  aria-label={`Go to slide ${idx + 1} of ${activeMovies.length}: ${m.title}`}
                  onClick={() => goTo(idx)}
                  className="group relative h-6 w-7 sm:w-11 flex items-center justify-center cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 rounded transition-all"
                >
                  {/* Track */}
                  <div className="w-full h-1 bg-white/20 rounded-full overflow-hidden transition-colors duration-200 group-hover:bg-white/40">
                    {isActive ? (
                      <span
                        key={`${rotationKey}-${isPaused ? 'paused' : 'playing'}`}
                        className="block h-full w-full bg-amber-400 rounded-full origin-left"
                        style={{
                          animation:
                            isPaused || prefersReducedMotion
                              ? 'none'
                              : 'heroProgressFill 10s linear forwards',
                          animationPlayState: isPaused ? 'paused' : 'running',
                          transform: isPaused ? 'scaleX(0)' : undefined,
                        }}
                      />
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Prev / Next circular buttons */}
          <div className="flex items-center gap-1.5 sm:gap-2 pl-2 sm:pl-3 border-l border-white/20">
            <button
              type="button"
              aria-label="Previous movie"
              onClick={prevSlide}
              className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border border-white/20 bg-[#14151b]/80 hover:bg-[#23252b] text-slate-300 hover:text-amber-400 hover:border-amber-500/50 backdrop-blur-md flex items-center justify-center transition-all duration-200 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 active:scale-95 shadow-md shadow-black/40"
            >
              <ChevronLeft className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
            <button
              type="button"
              aria-label="Next movie"
              onClick={nextSlide}
              className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border border-white/20 bg-[#14151b]/80 hover:bg-[#23252b] text-slate-300 hover:text-amber-400 hover:border-amber-500/50 backdrop-blur-md flex items-center justify-center transition-all duration-200 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 active:scale-95 shadow-md shadow-black/40"
            >
              <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
          </div>
        </div>
      )}
    </section>
  );
};
