import React, { useState, useEffect } from 'react';
import {
  X,
  Search,
  Check,
  Sparkles,
  Film,
  ArrowRight,
  ArrowLeft,
  EyeOff,
  RotateCcw,
} from 'lucide-react';
import { useUserTaste } from '../../context/UserTasteContext';
import { fetchPopular, fetchSearch } from '../../api/client';
import type { ApiMovie } from '../../api/types';
import type { Movie } from '../../types/movie';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialStep?: 1 | 2;
}

const GENRE_TABS = [
  'All',
  'Sci-Fi',
  'Action',
  'Drama',
  'Comedy',
  'Thriller',
  'Animation',
];

const ALL_CATALOG_GENRES = [
  'Action',
  'Adventure',
  'Animation',
  'Children',
  'Comedy',
  'Crime',
  'Documentary',
  'Drama',
  'Fantasy',
  'Film-Noir',
  'Horror',
  'Musical',
  'Mystery',
  'Romance',
  'Sci-Fi',
  'Thriller',
  'War',
  'Western',
];

export const OnboardingModal: React.FC<OnboardingModalProps> = ({
  isOpen,
  onClose,
  initialStep = 1,
}) => {
  const {
    isLiked,
    toggleLike,
    validLikedIds,
    dismissOnboarding,
    avoidedGenres,
    toggleAvoidedGenre,
    clearAvoidedGenres,
    isGenreAvoided,
  } = useUserTaste();

  const [step, setStep] = useState<1 | 2>(initialStep);
  const [activeGenre, setActiveGenre] = useState<string>('All');
  const [popularMovies, setPopularMovies] = useState<ApiMovie[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<ApiMovie[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searching, setSearching] = useState<boolean>(false);

  // Sync step on modal open
  useEffect(() => {
    if (isOpen) {
      setStep(initialStep);
    }
  }, [isOpen, initialStep]);

  // Load popular movies spanning genres deterministically
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const genreParam = activeGenre === 'All' ? undefined : activeGenre;
        const movies = await fetchPopular({ genre: genreParam, limit: 36 });
        if (mounted) {
          // Filter for movies with poster
          setPopularMovies(movies.filter((m) => Boolean(m.poster_url)));
        }
      } catch (err) {
        console.error('Failed to load onboarding movies', err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, [activeGenre]);

  // Debounced search
  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await fetchSearch(searchQuery.trim(), 24);
        setSearchResults(results.filter((m) => Boolean(m.poster_url)));
      } catch (err) {
        console.error('Search failed in onboarding', err);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  if (!isOpen) return null;

  const handleSelectMovie = (apiMovie: ApiMovie) => {
    const movieObj: Movie = {
      id: String(apiMovie.movie_id),
      movie_id: apiMovie.movie_id,
      title: apiMovie.title,
      year: apiMovie.year || 0,
      director: apiMovie.directors?.[0] || 'Unknown',
      genres: apiMovie.genres || [],
      tags: [],
      overview: apiMovie.overview || '',
      poster: apiMovie.poster_url || '',
      matchScore: 0,
    };
    toggleLike(movieObj);
  };

  const handleFinish = () => {
    dismissOnboarding();
    onClose();
  };

  const handleSkip = () => {
    dismissOnboarding();
    onClose();
  };

  const displayedMovies = searchQuery.trim().length >= 2 ? searchResults : popularMovies;
  const count = validLikedIds.length;
  const canContinueToStep2 = count >= 3;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-4xl max-h-[92vh] flex flex-col rounded-2xl bg-[#14151a] border border-amber-500/30 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-6 border-b border-white/10 bg-[#191a22] flex items-start justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-amber-500 font-bold">
              {step === 1 ? (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Taste Calibration &bull; Step 1 of 2</span>
                </>
              ) : (
                <>
                  <EyeOff className="w-4 h-4" />
                  <span>Display Filter &bull; Step 2 of 2 (Optional)</span>
                </>
              )}
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl text-white font-bold tracking-tight">
              {step === 1
                ? 'Pick at least 3 movies you love'
                : "Any genres you'd rather not see?"}
            </h2>
            <p className="text-xs sm:text-sm text-slate-300">
              {step === 1
                ? '5–10 works best. Your picks tune our hybrid recommendation model to your taste.'
                : "Hide genres I don't want to see. Titles in these genres are hidden from Home rows, hero candidates, and Explore results."}
            </p>
          </div>
          <button
            type="button"
            onClick={handleSkip}
            className="w-9 h-9 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
            title="Skip for now"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* STEP 1: MOVIE PICKS */}
        {step === 1 && (
          <>
            {/* Search & Genre Filters Bar */}
            <div className="p-4 sm:px-6 bg-[#16171f] border-b border-white/5 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              {/* Search box */}
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by title (e.g. Matrix, Inception)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#1f2029] border border-white/10 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-500/50"
                />
              </div>

              {/* Genre Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
                {GENRE_TABS.map((genre) => (
                  <button
                    type="button"
                    key={genre}
                    onClick={() => {
                      setActiveGenre(genre);
                      setSearchQuery('');
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium whitespace-nowrap transition-all cursor-pointer ${
                      activeGenre === genre
                        ? 'bg-amber-500 text-black font-bold shadow-md'
                        : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    {genre}
                  </button>
                ))}
              </div>
            </div>

            {/* Movies Grid */}
            <div className="p-4 sm:p-6 overflow-y-auto flex-1 min-h-[360px]">
              {loading || searching ? (
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3 sm:gap-4">
                  {Array.from({ length: 18 }).map((_, i) => (
                    <div
                      key={i}
                      className="aspect-[2/3] rounded-xl bg-white/5 animate-pulse"
                    />
                  ))}
                </div>
              ) : displayedMovies.length === 0 ? (
                <div className="h-64 flex flex-col items-center justify-center text-center space-y-2">
                  <Film className="w-8 h-8 text-slate-600" />
                  <p className="text-sm text-slate-400">
                    No movies found matching &ldquo;{searchQuery}&rdquo;
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3 sm:gap-4">
                  {displayedMovies.map((movie) => {
                    const picked = isLiked(movie.movie_id);
                    return (
                      <button
                        type="button"
                        key={movie.movie_id}
                        onClick={() => handleSelectMovie(movie)}
                        className={`group relative aspect-[2/3] rounded-xl overflow-hidden text-left border transition-all cursor-pointer ${
                          picked
                            ? 'border-amber-500 ring-2 ring-amber-500 shadow-lg shadow-amber-500/20 scale-[0.98]'
                            : 'border-white/10 hover:border-amber-500/40 hover:-translate-y-1'
                        }`}
                      >
                        <img
                          src={movie.poster_url || ''}
                          alt={movie.title}
                          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                          loading="lazy"
                        />

                        {/* Picked indicator */}
                        {picked && (
                          <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-amber-500 text-black flex items-center justify-center shadow-md">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </div>
                        )}

                        {/* Title Scrim */}
                        <div className="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black via-black/80 to-transparent">
                          <p className="font-serif text-xs font-semibold text-white truncate">
                            {movie.title}
                          </p>
                          {movie.year && (
                            <p className="text-[10px] font-mono text-slate-400">{movie.year}</p>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Step 1 Footer */}
            <div className="p-4 sm:px-6 bg-[#16171f] border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold ${
                    canContinueToStep2
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {count} of 3 required picked
                </div>
                <div className="text-xs text-slate-400 hidden sm:block">
                  {canContinueToStep2
                    ? 'Ready! Continue to set genre display filters.'
                    : 'Select at least 3 movies to unlock personalized rows.'}
                </div>
              </div>

              <div className="flex items-center gap-2.5 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={handleSkip}
                  className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
                >
                  Skip for now
                </button>

                <button
                  type="button"
                  onClick={() => setStep(2)}
                  disabled={!canContinueToStep2}
                  className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                    canContinueToStep2
                      ? 'bg-amber-500 hover:bg-amber-400 text-black shadow-lg shadow-amber-500/25 cursor-pointer'
                      : 'bg-white/10 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <span>Next: Avoided Genres</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}

        {/* STEP 2: GENRES TO AVOID */}
        {step === 2 && (
          <>
            <div className="p-6 sm:p-8 overflow-y-auto flex-1 min-h-[360px] space-y-6">
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-amber-400 font-semibold uppercase tracking-wider">
                    Display filter only
                  </span>
                  {avoidedGenres.length > 0 && (
                    <button
                      type="button"
                      onClick={clearAvoidedGenres}
                      className="text-xs font-mono text-slate-400 hover:text-red-400 flex items-center gap-1 cursor-pointer transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Clear all ({avoidedGenres.length})</span>
                    </button>
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  Select any genres you would rather hide. Movies featuring these genres will be
                  automatically filtered from your Home rows, hero candidates, and Explore catalog.
                </p>
              </div>

              {/* Multi-select Genre Chips */}
              <div className="space-y-3">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
                  Catalog Genres
                </div>
                <div className="flex flex-wrap gap-2.5">
                  {ALL_CATALOG_GENRES.map((genre) => {
                    const isAvoided = isGenreAvoided(genre);
                    return (
                      <button
                        type="button"
                        key={genre}
                        onClick={() => toggleAvoidedGenre(genre)}
                        className={`px-4 py-2.5 rounded-xl text-xs font-mono transition-all cursor-pointer flex items-center gap-2 ${
                          isAvoided
                            ? 'bg-amber-500 text-black font-bold shadow-md shadow-amber-500/20 border border-amber-400 scale-[1.02]'
                            : 'bg-[#1b1c23] hover:bg-[#23242e] text-slate-300 hover:text-white border border-white/10'
                        }`}
                      >
                        {isAvoided ? (
                          <EyeOff className="w-3.5 h-3.5 stroke-[2.5]" />
                        ) : (
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                        )}
                        <span>{genre}</span>
                        {isAvoided && (
                          <span className="text-[10px] bg-black/20 text-black px-1.5 py-0.2 rounded font-bold">
                            Hidden
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Status Note */}
              <div className="text-xs font-mono text-slate-500 pt-2">
                {avoidedGenres.length === 0 ? (
                  <span>No genres hidden — all catalog categories will appear in feeds.</span>
                ) : (
                  <span className="text-amber-400/90 font-medium">
                    Hiding: {avoidedGenres.join(', ')}
                  </span>
                )}
              </div>
            </div>

            {/* Step 2 Footer */}
            <div className="p-4 sm:px-6 bg-[#16171f] border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Picks</span>
              </button>

              <div className="flex items-center gap-2.5 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={handleSkip}
                  className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
                >
                  Skip this step
                </button>

                <button
                  type="button"
                  onClick={handleFinish}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-all shadow-lg shadow-amber-500/25 cursor-pointer"
                >
                  <span>Continue to Feed</span>
                  <Check className="w-4 h-4 stroke-[3]" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
