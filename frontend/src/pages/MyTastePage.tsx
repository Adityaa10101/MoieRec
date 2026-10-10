import React, { useState, useEffect } from 'react';
import { Link } from '../router/Router';
import { Sparkles, ArrowLeft, Trash2, Edit3, Heart, Plus, EyeOff } from 'lucide-react';
import { useUserTaste } from '../context/UserTasteContext';
import { fetchMovieDetail } from '../api/client';
import type { ApiMovie } from '../api/types';

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

export const MyTastePage: React.FC = () => {
  const {
    validLikedIds,
    removeLike,
    setIsOnboardingOpen,
    clearAllPicks,
    avoidedGenres,
    toggleAvoidedGenre,
    clearAvoidedGenres,
    isGenreAvoided,
  } = useUserTaste();

  const [movieDetails, setMovieDetails] = useState<Record<number, ApiMovie>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    const missingIds = validLikedIds.filter((id) => !movieDetails[id]);

    if (missingIds.length === 0) return;

    setLoading(true);
    Promise.allSettled(missingIds.map((id) => fetchMovieDetail(id))).then((results) => {
      if (!mounted) return;
      setMovieDetails((prev) => {
        const next = { ...prev };
        results.forEach((res, i) => {
          if (res.status === 'fulfilled' && res.value) {
            next[missingIds[i]] = res.value;
          }
        });
        return next;
      });
      setLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, [validLikedIds, movieDetails]);

  return (
    <div className="min-h-screen pt-28 pb-20 max-w-5xl mx-auto px-6 space-y-8">
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-amber-400 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Return to Curated Feed</span>
      </Link>

      <div className="p-8 sm:p-12 rounded-2xl bg-[#1a1b20] border border-white/10 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-amber-400 uppercase tracking-widest font-semibold">
              <Heart className="w-4 h-4 text-amber-500" />
              <span>Taste DNA Profile</span>
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-white font-bold">
              Your Movie Picks
            </h1>
            <p className="text-xs text-slate-400">
              Personalized recommendations are generated from these titles using the Hybrid v1 model.
            </p>
          </div>

          <div className="flex items-center gap-3 self-start sm:self-auto">
            <button
              onClick={() => setIsOnboardingOpen(true)}
              className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-colors flex items-center gap-2 cursor-pointer shadow-lg"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Edit your picks</span>
            </button>
            {validLikedIds.length > 0 && (
              <button
                onClick={clearAllPicks}
                className="px-3 py-2 rounded-xl bg-white/5 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-white/10 text-xs font-medium transition-colors"
                title="Clear all picks"
              >
                Clear all
              </button>
            )}
          </div>
        </div>

        {/* User Picks List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-mono text-slate-300 uppercase tracking-wider font-semibold">
              Selected Movies ({validLikedIds.length})
            </h2>
            {validLikedIds.length < 3 && (
              <span className="text-xs font-mono text-amber-400">
                Pick at least 3 movies for personalized recommendations ({3 - validLikedIds.length} more needed)
              </span>
            )}
          </div>

          {validLikedIds.length === 0 ? (
            <div className="p-12 rounded-xl bg-[#23252b]/40 border border-dashed border-white/10 text-center space-y-4">
              <Heart className="w-8 h-8 text-slate-600 mx-auto" />
              <div className="space-y-1">
                <p className="text-slate-300 text-sm font-medium">No movies picked yet</p>
                <p className="text-slate-500 text-xs">
                  Pick at least 3 movies to activate your personalized Hybrid v1 recommendations.
                </p>
              </div>
              <button
                onClick={() => setIsOnboardingOpen(true)}
                className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold inline-flex items-center gap-2 transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Pick Movies Now</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {validLikedIds.map((id) => {
                const movie = movieDetails[id];
                return (
                  <div
                    key={id}
                    className="flex items-center gap-3.5 p-3 rounded-xl bg-[#23252b]/60 border border-white/10 hover:border-amber-500/40 transition-colors group"
                  >
                    {/* Poster */}
                    <div className="w-14 h-20 rounded-lg overflow-hidden bg-[#16171b] flex-shrink-0 relative">
                      {movie?.poster_url ? (
                        <img
                          src={movie.poster_url}
                          alt={movie.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-600">
                          {loading ? '...' : 'No Art'}
                        </div>
                      )}
                    </div>

                    {/* Title & Info */}
                    <div className="flex-1 min-w-0 space-y-1">
                      <h4 className="text-sm font-medium text-white truncate">
                        {movie?.title ?? `Movie #${id}`}
                      </h4>
                      <p className="text-xs text-slate-400">
                        {movie?.year ? `${movie.year}` : 'MovieLens ID: ' + id}
                        {movie?.genres?.length ? ` • ${movie.genres.slice(0, 2).join(', ')}` : ''}
                      </p>
                    </div>

                    {/* Remove Action */}
                    <button
                      onClick={() => removeLike(id)}
                      className="w-8 h-8 rounded-lg bg-white/5 hover:bg-red-500/20 text-slate-400 hover:text-red-400 flex items-center justify-center transition-colors cursor-pointer"
                      title="Remove pick"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Genres to Avoid (Display Settings) */}
        <div className="space-y-4 pt-6 border-t border-white/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono text-amber-400 uppercase tracking-widest font-semibold">
                <EyeOff className="w-4 h-4 text-amber-500" />
                <span>Display Preferences</span>
              </div>
              <h2 className="font-serif text-xl sm:text-2xl text-white font-bold">
                Hide genres I don't want to see
              </h2>
              <p className="text-xs text-slate-400">
                Titles in these genres are hidden from your Home rows, hero candidates, and Explore catalog. This is a display filter only and does not change recommendation scores or training.
              </p>
            </div>
            {avoidedGenres.length > 0 && (
              <button
                type="button"
                onClick={clearAvoidedGenres}
                className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-white/10 text-xs font-medium transition-colors self-start sm:self-auto cursor-pointer"
              >
                Clear all avoided ({avoidedGenres.length})
              </button>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {ALL_CATALOG_GENRES.map((g) => {
              const active = isGenreAvoided(g);
              return (
                <button
                  type="button"
                  key={g}
                  onClick={() => toggleAvoidedGenre(g)}
                  className={`px-3.5 py-2 rounded-xl text-xs font-mono transition-all cursor-pointer flex items-center gap-2 ${
                    active
                      ? 'bg-amber-500 text-black font-bold shadow-md shadow-amber-500/20 border border-amber-400 scale-[1.02]'
                      : 'bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/5'
                  }`}
                >
                  {active ? (
                    <EyeOff className="w-3.5 h-3.5 stroke-[2.5]" />
                  ) : (
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                  )}
                  <span>{g}</span>
                  {active && (
                    <span className="text-[10px] bg-black/20 text-black px-1.5 py-0.2 rounded font-bold">
                      Hidden
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300 flex items-center gap-3">
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            Hybrid v1 balances your specific taste profile with verified viewer popularity without collaborative filtering or dark patterns.
          </span>
        </div>
      </div>
    </div>
  );
};
