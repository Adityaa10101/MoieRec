import React, { useState, useEffect, useMemo } from 'react';
import { Link, useRouter } from '../router/Router';
import {
  Heart,
  Bookmark,
  EyeOff,
  Trash2,
  Sparkles,
  Compass,
  RotateCcw,
  Film,
  AlertTriangle,
} from 'lucide-react';
import { useUserTaste } from '../context/UserTasteContext';
import { fetchMoviesBatch } from '../api/client';
import type { ApiMovie } from '../api/types';
import { MovieCardSkeleton } from '../components/common/MovieCardSkeleton';

type LibraryTab = 'liked' | 'watchlist' | 'disliked';

export const LibraryPage: React.FC = () => {
  const {
    validLikedIds,
    validWatchlistIds,
    validDislikedIds,
    removeLike,
    removeWatchlist,
    removeDislike,
    moveToList,
    clearLiked,
    clearWatchlist,
    clearDisliked,
    setIsOnboardingOpen,
    cleanLegacyIds,
  } = useUserTaste();

  const { path } = useRouter();

  // Tab state (support ?tab=liked or URL search param if present)
  const [activeTab, setActiveTab] = useState<LibraryTab>('liked');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const tabParam = urlParams.get('tab') as LibraryTab | null;
      if (tabParam && ['liked', 'watchlist', 'disliked'].includes(tabParam)) {
        setActiveTab(tabParam);
      }
    }
  }, [path]);

  // Batch-fetched metadata store
  const [movieMeta, setMovieMeta] = useState<Record<number, ApiMovie>>({});
  const [loading, setLoading] = useState(false);

  // Clear confirmation modal state
  const [confirmClearTab, setConfirmClearTab] = useState<LibraryTab | null>(null);

  // Determine current active item IDs
  const activeIds = useMemo(() => {
    if (activeTab === 'liked') return validLikedIds;
    if (activeTab === 'watchlist') return validWatchlistIds;
    return validDislikedIds;
  }, [activeTab, validLikedIds, validWatchlistIds, validDislikedIds]);

  // Fetch metadata in batch (max 100) whenever active IDs change
  useEffect(() => {
    const missing = activeIds.filter((id) => !movieMeta[id]);
    if (missing.length === 0) return;

    let mounted = true;
    setLoading(true);

    const controller = new AbortController();
    fetchMoviesBatch(missing, controller.signal)
      .then((movies) => {
        if (!mounted) return;
        const newMap: Record<number, ApiMovie> = {};
        const returnedIds = new Set<number>();
        movies.forEach((m) => {
          newMap[m.movie_id] = m;
          returnedIds.add(m.movie_id);
        });

        setMovieMeta((prev) => ({ ...prev, ...newMap }));

        // If unknown legacy ids were passed and not in catalog, clean them up
        if (missing.length > movies.length) {
          const knownValid = new Set([...Object.keys(movieMeta).map(Number), ...returnedIds]);
          cleanLegacyIds(knownValid);
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.error('Batch load error in LibraryPage', err);
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
      controller.abort();
    };
  }, [activeIds, movieMeta, cleanLegacyIds]);

  // Genre breakdown computed strictly from real genres of liked picks (no taste scores/percentages)
  const genreSummary = useMemo(() => {
    const counts: Record<string, number> = {};
    let total = 0;
    validLikedIds.forEach((id) => {
      const m = movieMeta[id];
      if (m && m.genres) {
        m.genres.forEach((g) => {
          counts[g] = (counts[g] || 0) + 1;
          total += 1;
        });
      }
    });

    if (total === 0) return [];
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, count]) => ({
        name,
        count,
        pct: Math.round((count / total) * 100),
      }));
  }, [validLikedIds, movieMeta]);

  const handleClearConfirm = () => {
    if (confirmClearTab === 'liked') clearLiked();
    else if (confirmClearTab === 'watchlist') clearWatchlist();
    else if (confirmClearTab === 'disliked') clearDisliked();
    setConfirmClearTab(null);
  };

  return (
    <div className="min-h-screen pt-28 pb-24 max-w-6xl mx-auto px-6 space-y-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-white/10 pb-8">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
              Local Library
            </span>
            <span className="text-xs text-slate-400">
              Guest mode: your picks are saved only in this browser.
            </span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl text-white font-bold tracking-tight">
            My Library
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl">
            Browse and organize your liked movies, screening watchlist, and excluded titles.
          </p>
        </div>

        {/* Quick action: Edit Onboarding Picks */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsOnboardingOpen(true)}
            className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-all flex items-center gap-2 shadow-lg cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Edit your picks</span>
          </button>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 p-1 rounded-xl bg-[#14151a] border border-white/10">
          <button
            onClick={() => setActiveTab('liked')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'liked'
                ? 'bg-amber-500 text-black font-bold shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Heart className="w-3.5 h-3.5" />
            <span>Liked ({validLikedIds.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('watchlist')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'watchlist'
                ? 'bg-amber-500 text-black font-bold shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Bookmark className="w-3.5 h-3.5" />
            <span>Watchlist ({validWatchlistIds.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('disliked')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'disliked'
                ? 'bg-amber-500 text-black font-bold shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <EyeOff className="w-3.5 h-3.5" />
            <span>Not interested ({validDislikedIds.length})</span>
          </button>
        </div>

        {/* Tab Context Action: Clear Tab */}
        {activeIds.length > 0 && (
          <button
            onClick={() => setConfirmClearTab(activeTab)}
            className="px-3.5 py-1.5 rounded-lg border border-red-500/20 bg-red-500/5 hover:bg-red-500/15 text-red-400 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear all</span>
          </button>
        )}
      </div>

      {/* Tab Explanations */}
      {activeTab === 'liked' && (
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            These are your picks that power the <strong className="text-amber-400 font-semibold">"Picked for you"</strong> personalized feed on the Home page.
          </p>

          {/* Genre Distribution Bar Summary (Optional quick feature) */}
          {genreSummary.length > 0 && (
            <div className="p-4 rounded-xl bg-[#14151a] border border-white/10 space-y-3">
              <div className="flex items-center justify-between text-xs font-mono text-slate-300 font-semibold">
                <span>Your picks by genre</span>
                <span className="text-[11px] text-slate-500">Real genre frequencies from liked titles</span>
              </div>
              <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden flex gap-0.5">
                {genreSummary.map((g, idx) => {
                  const colors = [
                    'bg-amber-500',
                    'bg-sky-500',
                    'bg-indigo-500',
                    'bg-emerald-500',
                    'bg-rose-500',
                    'bg-purple-500',
                  ];
                  return (
                    <div
                      key={g.name}
                      style={{ width: `${g.pct}%` }}
                      className={`${colors[idx % colors.length]} h-full transition-all`}
                      title={`${g.name}: ${g.count} titles (${g.pct}%)`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-3 pt-1">
                {genreSummary.map((g) => (
                  <span key={g.name} className="text-[11px] text-slate-400 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span>{g.name}</span>
                    <span className="font-mono text-slate-500">({g.count})</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'watchlist' && (
        <p className="text-xs text-slate-400">
          Movies you saved to watch later. You can move them to your Liked picks once you've seen them.
        </p>
      )}

      {activeTab === 'disliked' && (
        <p className="text-xs text-slate-400">
          Titles you marked as Not interested are strictly excluded from recommendation rows. You can undo or remove them at any time.
        </p>
      )}

      {/* Items List or Empty State */}
      {activeIds.length === 0 ? (
        <div className="p-12 rounded-2xl bg-[#14151a] border border-white/10 text-center space-y-5 my-8">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto text-amber-500">
            {activeTab === 'liked' ? (
              <Heart className="w-6 h-6" />
            ) : activeTab === 'watchlist' ? (
              <Bookmark className="w-6 h-6" />
            ) : (
              <EyeOff className="w-6 h-6" />
            )}
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="font-serif text-xl font-bold text-white">
              {activeTab === 'liked'
                ? 'No liked movies yet'
                : activeTab === 'watchlist'
                ? 'Your watchlist is empty'
                : 'No titles marked Not interested'}
            </h3>
            <p className="text-xs text-slate-400">
              {activeTab === 'liked'
                ? 'Pick movies you love to calibrate your collaborative filtering recommendations.'
                : activeTab === 'watchlist'
                ? 'Save interesting films while exploring to find them easily in one place.'
                : 'Disliked movies will never be recommended to your profile.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            {activeTab === 'liked' ? (
              <>
                <button
                  onClick={() => setIsOnboardingOpen(true)}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Pick movies you love</span>
                </button>
                <Link
                  to="/explore"
                  className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-medium transition-all flex items-center gap-1.5"
                >
                  <Compass className="w-3.5 h-3.5 text-amber-400" />
                  <span>Browse Explore</span>
                </Link>
              </>
            ) : (
              <Link
                to="/explore"
                className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-all flex items-center gap-1.5"
              >
                <Compass className="w-4 h-4" />
                <span>Browse Explore Catalog</span>
              </Link>
            )}
          </div>
        </div>
      ) : loading && Object.keys(movieMeta).length === 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <MovieCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {activeIds.map((id) => {
            const movie = movieMeta[id];
            if (!movie) {
              return (
                <div
                  key={id}
                  className="p-4 rounded-xl bg-[#14151a] border border-white/10 animate-pulse flex items-center justify-between"
                >
                  <span className="text-xs font-mono text-slate-500">Loading movie #{id}...</span>
                  <button
                    onClick={() => {
                      if (activeTab === 'liked') removeLike(id);
                      else if (activeTab === 'watchlist') removeWatchlist(id);
                      else removeDislike(id);
                    }}
                    className="text-xs text-red-400 hover:underline"
                  >
                    Remove
                  </button>
                </div>
              );
            }

            return (
              <div
                key={movie.movie_id}
                className="p-3.5 rounded-xl bg-[#14151a] border border-white/10 hover:border-white/20 transition-all flex gap-3.5 group"
              >
                {/* Poster */}
                <Link
                  to={`/movie/${movie.movie_id}`}
                  className="w-16 h-24 rounded-lg bg-[#1f2028] overflow-hidden shrink-0 relative block"
                >
                  {movie.poster_url ? (
                    <img
                      src={movie.poster_url}
                      alt={movie.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-600">
                      <Film className="w-5 h-5" />
                    </div>
                  )}
                </Link>

                {/* Details & Actions */}
                <div className="flex-1 min-w-0 flex flex-col justify-between">
                  <div className="space-y-1">
                    <Link
                      to={`/movie/${movie.movie_id}`}
                      className="block font-serif text-sm font-semibold text-white hover:text-amber-400 transition-colors truncate"
                      title={movie.title}
                    >
                      {movie.title}
                    </Link>
                    <div className="text-[11px] font-mono text-slate-400">
                      {movie.year || 'Unknown year'}
                    </div>
                    {movie.genres && movie.genres.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-0.5">
                        {movie.genres.slice(0, 2).map((g) => (
                          <span
                            key={g}
                            className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-white/5 text-slate-400 border border-white/5"
                          >
                            {g}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Actions Bar */}
                  <div className="flex items-center justify-between pt-2 border-t border-white/5 mt-2">
                    <div className="flex items-center gap-1.5">
                      {/* Move action */}
                      {activeTab === 'watchlist' && (
                        <button
                          onClick={() => moveToList(movie.movie_id, 'liked')}
                          className="px-2 py-1 rounded-md bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-[10px] font-medium flex items-center gap-1 cursor-pointer transition-colors"
                          title="Move to Liked"
                        >
                          <Heart className="w-3 h-3" />
                          <span>Like</span>
                        </button>
                      )}

                      {activeTab === 'liked' && (
                        <button
                          onClick={() => moveToList(movie.movie_id, 'watchlist')}
                          className="px-2 py-1 rounded-md bg-white/5 hover:bg-white/10 text-slate-300 text-[10px] font-medium flex items-center gap-1 cursor-pointer transition-colors"
                          title="Move to Watchlist"
                        >
                          <Bookmark className="w-3 h-3" />
                          <span>Watchlist</span>
                        </button>
                      )}

                      {activeTab === 'disliked' && (
                        <button
                          onClick={() => moveToList(movie.movie_id, 'liked')}
                          className="px-2 py-1 rounded-md bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-[10px] font-medium flex items-center gap-1 cursor-pointer transition-colors"
                          title="Undo and add to Liked"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Undo</span>
                        </button>
                      )}
                    </div>

                    {/* Remove button */}
                    <button
                      onClick={() => {
                        if (activeTab === 'liked') removeLike(movie.movie_id);
                        else if (activeTab === 'watchlist') removeWatchlist(movie.movie_id);
                        else removeDislike(movie.movie_id);
                      }}
                      className="p-1 text-slate-500 hover:text-red-400 transition-colors cursor-pointer"
                      title="Remove from list"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Clear Confirmation Modal */}
      {confirmClearTab && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setConfirmClearTab(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-[#14151a] border border-white/10 p-6 space-y-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="font-serif text-lg font-bold text-white">
                  Clear all {confirmClearTab === 'liked' ? 'Liked picks' : confirmClearTab === 'watchlist' ? 'Watchlist items' : 'Not interested titles'}?
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Are you sure you want to delete all stored items in this list? This operation is saved only in this browser and cannot be undone.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setConfirmClearTab(null)}
                className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleClearConfirm}
                className="px-4 py-2 rounded-xl bg-red-500 hover:bg-red-600 text-white text-xs font-bold transition-colors cursor-pointer shadow-lg shadow-red-500/20"
              >
                Confirm Clear
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
