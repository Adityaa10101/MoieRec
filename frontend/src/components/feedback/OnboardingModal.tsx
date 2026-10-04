import React, { useState, useEffect } from 'react';
import { X, Search, Check, Sparkles, Film, ArrowRight } from 'lucide-react';
import { useUserTaste } from '../../context/UserTasteContext';
import { fetchPopular, fetchSearch } from '../../api/client';
import type { ApiMovie } from '../../api/types';
import type { Movie } from '../../types/movie';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
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

export const OnboardingModal: React.FC<OnboardingModalProps> = ({ isOpen, onClose }) => {
  const { isLiked, toggleLike, validLikedIds, dismissOnboarding } = useUserTaste();

  const [activeGenre, setActiveGenre] = useState<string>('All');
  const [popularMovies, setPopularMovies] = useState<ApiMovie[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<ApiMovie[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searching, setSearching] = useState<boolean>(false);

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
    // Convert ApiMovie to Movie for toggleLike
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

  const handleContinue = () => {
    dismissOnboarding();
    onClose();
  };

  const handleSkip = () => {
    dismissOnboarding();
    onClose();
  };

  const displayedMovies = searchQuery.trim().length >= 2 ? searchResults : popularMovies;
  const count = validLikedIds.length;
  const canContinue = count >= 3;

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
              <Sparkles className="w-4 h-4" />
              <span>Taste Calibration &bull; Personalized Feed</span>
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl text-white font-bold tracking-tight">
              Pick at least 3 movies you love
            </h2>
            <p className="text-xs sm:text-sm text-slate-300">
              5–10 works best. Your picks tune our hybrid recommendation model to your taste.
            </p>
          </div>
          <button
            onClick={handleSkip}
            className="w-9 h-9 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
            title="Skip for now"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

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
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-amber-500/50 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-white"
              >
                Clear
              </button>
            )}
          </div>

          {/* Genre Tabs (only when not searching) */}
          {!searchQuery && (
            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
              {GENRE_TABS.map((genre) => (
                <button
                  key={genre}
                  onClick={() => setActiveGenre(genre)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                    activeGenre === genre
                      ? 'bg-amber-500 text-black font-semibold'
                      : 'bg-white/5 hover:bg-white/10 text-slate-300'
                  }`}
                >
                  {genre}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Movie Posters Grid */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#0f1015]">
          {loading || searching ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3.5 sm:gap-4">
              {Array.from({ length: 18 }).map((_, i) => (
                <div key={i} className="aspect-[2/3] rounded-xl bg-white/5 animate-pulse" />
              ))}
            </div>
          ) : displayedMovies.length === 0 ? (
            <div className="py-20 text-center space-y-3">
              <Film className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-slate-400 text-sm">No movies found matching your query.</p>
              <button
                onClick={() => setSearchQuery('')}
                className="text-xs text-amber-400 hover:underline"
              >
                Reset search
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3.5 sm:gap-4">
              {displayedMovies.map((movie) => {
                const selected = isLiked(movie.movie_id);
                return (
                  <button
                    key={movie.movie_id}
                    onClick={() => handleSelectMovie(movie)}
                    className={`group relative aspect-[2/3] rounded-xl overflow-hidden text-left border-2 transition-all duration-200 transform hover:scale-[1.02] ${
                      selected
                        ? 'border-amber-500 shadow-lg shadow-amber-500/20'
                        : 'border-transparent hover:border-white/30'
                    }`}
                  >
                    <img
                      src={movie.poster_url || ''}
                      alt={movie.title}
                      loading="lazy"
                      className="w-full h-full object-cover"
                    />

                    {/* Gradient overlay */}
                    <div
                      className={`absolute inset-0 transition-opacity ${
                        selected
                          ? 'bg-amber-950/40 opacity-100'
                          : 'bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100'
                      }`}
                    />

                    {/* Checkmark badge */}
                    {selected ? (
                      <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-amber-500 text-black flex items-center justify-center shadow-md">
                        <Check className="w-4 h-4 stroke-[3]" />
                      </div>
                    ) : (
                      <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-black/60 border border-white/20 text-white opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                        <span className="text-xs">+</span>
                      </div>
                    )}

                    {/* Movie title caption */}
                    <div className="absolute bottom-0 inset-x-0 p-2 text-white">
                      <div className="text-xs font-semibold line-clamp-1 leading-tight">{movie.title}</div>
                      {movie.year ? (
                        <div className="text-[10px] text-slate-300 font-mono">{movie.year}</div>
                      ) : null}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer with counter and action buttons */}
        <div className="p-4 sm:px-6 bg-[#16171f] border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold ${
                canContinue
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              }`}
            >
              {count} of 3 required picked
            </div>
            <div className="text-xs text-slate-400 hidden sm:block">
              {canContinue
                ? 'Ready! You can pick more or continue to your personalized feed.'
                : 'Select at least 3 movies to unlock personalized rows.'}
            </div>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              onClick={handleSkip}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-medium transition-colors"
            >
              Skip for now
            </button>

            <button
              onClick={handleContinue}
              disabled={!canContinue}
              className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                canContinue
                  ? 'bg-amber-500 hover:bg-amber-400 text-black shadow-lg shadow-amber-500/25 cursor-pointer'
                  : 'bg-white/10 text-slate-500 cursor-not-allowed'
              }`}
            >
              <span>Continue to Feed</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
