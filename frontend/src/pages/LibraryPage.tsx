import React, { useState, useEffect, useMemo } from 'react';
import { Link, useRouter } from '../router/Router';
import {
  Heart,
  Bookmark,
  Play,
  Check,
  XCircle,
  EyeOff,
  Trash2,
  Sparkles,
  Compass,
  Film,
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { useUserTaste, type WatchStatus } from '../context/UserTasteContext';
import { fetchMoviesBatch } from '../api/client';
import type { ApiMovie } from '../api/types';
import { MovieCardSkeleton } from '../components/common/MovieCardSkeleton';
import { WatchStatusControl } from '../components/movie/WatchStatusControl';

type LibraryTab = 'plan' | 'watching' | 'watched' | 'dropped' | 'liked' | 'disliked';

const TAB_CONFIG: Record<
  LibraryTab,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    description: string;
    emptyTitle: string;
    emptyDesc: string;
  }
> = {
  plan: {
    label: 'Plan to watch',
    icon: Bookmark,
    description: 'Movies you saved to watch later. You can update their watch status at any time as you view them.',
    emptyTitle: 'No movies in Plan to watch',
    emptyDesc: 'Save interesting films while exploring to find them easily in one place.',
  },
  watching: {
    label: 'Watching',
    icon: Play,
    description: 'Movies you are currently in the middle of watching.',
    emptyTitle: 'No movies currently watching',
    emptyDesc: 'Mark titles as watching to keep track of your active viewing list.',
  },
  watched: {
    label: 'Watched',
    icon: Check,
    description: 'Movies you have completed watching. These are hidden from Home and Explore recommendation rows.',
    emptyTitle: 'No watched movies yet',
    emptyDesc: 'Keep a record of movies you have already seen.',
  },
  dropped: {
    label: 'Dropped',
    icon: XCircle,
    description: 'Movies you decided not to finish. These are hidden from Home and Explore recommendation rows.',
    emptyTitle: 'No dropped movies',
    emptyDesc: 'Titles you stopped watching will be collected here.',
  },
  liked: {
    label: 'Liked',
    icon: Heart,
    description: 'These are your picks that power the "Picked for you" personalized feed on the Home page.',
    emptyTitle: 'No liked movies yet',
    emptyDesc: 'Pick movies you love to calibrate your collaborative filtering recommendations.',
  },
  disliked: {
    label: 'Not interested',
    icon: EyeOff,
    description: 'Titles you marked as Not interested are strictly excluded from recommendation rows. You can undo or remove them at any time.',
    emptyTitle: 'No titles marked Not interested',
    emptyDesc: 'Disliked movies will never be recommended to your profile.',
  },
};

export const LibraryPage: React.FC = () => {
  const {
    validLikedIds,
    validDislikedIds,
    planMovieIds,
    watchingMovieIds,
    watchedMovieIds,
    droppedMovieIds,
    setWatchStatus,
    clearStatusTab,
    isLiked,
    isDisliked,
    toggleLike,
    toggleDislike,
    removeLike,
    removeDislike,
    clearLiked,
    clearDisliked,
    setIsOnboardingOpen,
    cleanLegacyIds,
  } = useUserTaste();

  const { path } = useRouter();

  // Tab state (support ?tab=plan, ?tab=watchlist legacy alias, etc.)
  const [activeTab, setActiveTab] = useState<LibraryTab>('plan');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const tabParam = urlParams.get('tab') as LibraryTab | 'watchlist' | null;
      if (tabParam === 'watchlist') {
        setActiveTab('plan');
      } else if (tabParam && ['plan', 'watching', 'watched', 'dropped', 'liked', 'disliked'].includes(tabParam)) {
        setActiveTab(tabParam as LibraryTab);
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
    switch (activeTab) {
      case 'plan':
        return planMovieIds;
      case 'watching':
        return watchingMovieIds;
      case 'watched':
        return watchedMovieIds;
      case 'dropped':
        return droppedMovieIds;
      case 'liked':
        return validLikedIds;
      case 'disliked':
        return validDislikedIds;
      default:
        return planMovieIds;
    }
  }, [activeTab, planMovieIds, watchingMovieIds, watchedMovieIds, droppedMovieIds, validLikedIds, validDislikedIds]);

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
    if (!confirmClearTab) return;
    if (confirmClearTab === 'liked') {
      clearLiked();
    } else if (confirmClearTab === 'disliked') {
      clearDisliked();
    } else {
      clearStatusTab(confirmClearTab as WatchStatus);
    }
    setConfirmClearTab(null);
  };

  const getTabCount = (tab: LibraryTab) => {
    switch (tab) {
      case 'plan':
        return planMovieIds.length;
      case 'watching':
        return watchingMovieIds.length;
      case 'watched':
        return watchedMovieIds.length;
      case 'dropped':
        return droppedMovieIds.length;
      case 'liked':
        return validLikedIds.length;
      case 'disliked':
        return validDislikedIds.length;
    }
  };

  const currentTabCfg = TAB_CONFIG[activeTab];
  const CurrentEmptyIcon = currentTabCfg.icon;

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
              Guest mode: your lists and picks are saved only in this browser.
            </span>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl text-white font-bold tracking-tight">
            My Library
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl">
            Track your watch progress, organize your screening lists, and curate liked recommendations.
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
        <div className="flex flex-wrap items-center gap-1.5 p-1 rounded-xl bg-[#14151a] border border-white/10">
          {(Object.keys(TAB_CONFIG) as LibraryTab[]).map((tab) => {
            const cfg = TAB_CONFIG[tab];
            const Icon = cfg.icon;
            const count = getTabCount(tab);
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  isActive
                    ? 'bg-amber-500 text-black font-bold shadow-md'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>
                  {cfg.label} ({count})
                </span>
              </button>
            );
          })}
        </div>

        {/* Tab Context Action: Clear Tab */}
        {activeIds.length > 0 && (
          <button
            onClick={() => setConfirmClearTab(activeTab)}
            className="px-3.5 py-1.5 rounded-lg border border-red-500/20 bg-red-500/5 hover:bg-red-500/15 text-red-400 text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear tab</span>
          </button>
        )}
      </div>

      {/* Tab Explanations */}
      <div className="space-y-4">
        <p className="text-xs text-slate-400">{currentTabCfg.description}</p>

        {/* Genre Distribution Bar Summary for Liked Tab */}
        {activeTab === 'liked' && genreSummary.length > 0 && (
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

      {/* Items List or Empty State */}
      {activeIds.length === 0 ? (
        <div className="p-12 rounded-2xl bg-[#14151a] border border-white/10 text-center space-y-5 my-8">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto text-amber-500">
            <CurrentEmptyIcon className="w-6 h-6" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="font-serif text-xl font-bold text-white">
              {currentTabCfg.emptyTitle}
            </h3>
            <p className="text-xs text-slate-400">
              {currentTabCfg.emptyDesc}
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
                      else if (activeTab === 'disliked') removeDislike(id);
                      else setWatchStatus(id, null);
                    }}
                    className="text-xs text-red-400 hover:underline cursor-pointer"
                  >
                    Remove
                  </button>
                </div>
              );
            }

            const itemLiked = isLiked(movie.movie_id);
            const itemDisliked = isDisliked(movie.movie_id);

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

                  {/* Actions Bar: Status control + Thumbs buttons + Remove */}
                  <div className="flex items-center justify-between pt-2 border-t border-white/5 mt-2">
                    <div className="flex items-center gap-1.5">
                      {/* Thumbs up */}
                      <button
                        type="button"
                        onClick={() => toggleLike(movie)}
                        aria-label={`Like ${movie.title}`}
                        className={`p-1.5 rounded-md border flex items-center justify-center transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
                          itemLiked
                            ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                            : 'bg-white/5 border-transparent text-slate-400 hover:text-amber-400 hover:border-amber-500/40'
                        }`}
                        title={itemLiked ? `Unlike ${movie.title}` : `Like ${movie.title}`}
                      >
                        <ThumbsUp className={`w-3.5 h-3.5 ${itemLiked ? 'fill-amber-400' : ''}`} />
                      </button>

                      {/* Thumbs down */}
                      <button
                        type="button"
                        onClick={() => toggleDislike(movie)}
                        aria-label={`Dislike ${movie.title}`}
                        className={`p-1.5 rounded-md border flex items-center justify-center transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
                          itemDisliked
                            ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                            : 'bg-white/5 border-transparent text-slate-400 hover:text-amber-400 hover:border-amber-500/40'
                        }`}
                        title={itemDisliked ? `Undo dislike for ${movie.title}` : `Dislike ${movie.title}`}
                      >
                        <ThumbsDown className={`w-3.5 h-3.5 ${itemDisliked ? 'fill-amber-400' : ''}`} />
                      </button>

                      {/* Watch status dropdown */}
                      <WatchStatusControl movie={movie} variant="inline" />
                    </div>

                    {/* Remove button */}
                    <button
                      type="button"
                      onClick={() => {
                        if (activeTab === 'liked') removeLike(movie.movie_id);
                        else if (activeTab === 'disliked') removeDislike(movie.movie_id);
                        else setWatchStatus(movie.movie_id, null);
                      }}
                      className="p-1.5 text-slate-500 hover:text-red-400 transition-colors cursor-pointer rounded-md hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
                      title={`Remove from ${currentTabCfg.label}`}
                      aria-label={`Remove ${movie.title} from ${currentTabCfg.label}`}
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
                  Clear all {TAB_CONFIG[confirmClearTab].label} entries?
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Are you sure you want to delete all stored items in {TAB_CONFIG[confirmClearTab].label}? This operation is saved only in this browser and cannot be undone.
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
