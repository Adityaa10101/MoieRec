import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Movie } from '../types/movie';
import type { ApiMovie } from '../api/types';
import { useToast } from './ToastContext';

export type WatchStatus = 'plan' | 'watching' | 'watched' | 'dropped';

export interface MovieStatusItem {
  movie_id: number;
  status: WatchStatus;
  updated_at: string;
}

export interface StoredMovieItem {
  movie_id: number;
  added_at: string;
}

interface UserTasteContextType {
  watchlist: Set<string>;
  liked: Set<string>;
  disliked: Set<string>;
  watchlistItems: StoredMovieItem[];
  likedItems: StoredMovieItem[];
  dislikedItems: StoredMovieItem[];
  validLikedIds: number[];
  validWatchlistIds: number[];
  validDislikedIds: number[];
  isOnboardingOpen: boolean;
  onboardingDismissed: boolean;
  setIsOnboardingOpen: (open: boolean) => void;
  dismissOnboarding: () => void;
  isInWatchlist: (movieId: string | number) => boolean;
  isLiked: (movieId: string | number) => boolean;
  isDisliked: (movieId: string | number) => boolean;
  toggleWatchlist: (movie: Movie | ApiMovie) => void;
  toggleLike: (movie: Movie | ApiMovie) => void;
  toggleDislike: (movie: Movie | ApiMovie) => void;
  removeWatchlist: (movieId: string | number) => void;
  removeLike: (movieId: string | number) => void;
  removeDislike: (movieId: string | number) => void;
  moveToList: (movieId: number, toList: 'liked' | 'watchlist' | 'disliked') => void;
  clearWatchlist: () => void;
  clearLiked: () => void;
  clearDisliked: () => void;
  clearAllPicks: () => void;
  clearAllData: () => void;
  cleanLegacyIds: (validIds: Set<number>) => void;
  avoidedGenres: string[];
  toggleAvoidedGenre: (genre: string) => void;
  setAvoidedGenres: (genres: string[]) => void;
  clearAvoidedGenres: () => void;
  isGenreAvoided: (genre: string) => boolean;
  // Per-movie watch status
  statusItems: MovieStatusItem[];
  getWatchStatus: (movieId: string | number) => WatchStatus | null;
  setWatchStatus: (movie: Movie | ApiMovie | number, status: WatchStatus | null) => void;
  planMovieIds: number[];
  watchingMovieIds: number[];
  watchedMovieIds: number[];
  droppedMovieIds: number[];
  watchedAndDroppedIds: number[];
  savedMovieCount: number;
  isWatchedOrDropped: (movieId: string | number) => boolean;
  clearStatusTab: (status: WatchStatus) => void;
  dismissWatchedNudge: (movieId: number) => void;
  isNudgeDismissed: (movieId: number) => boolean;
}

const UserTasteContext = createContext<UserTasteContextType | undefined>(undefined);

function parseAvoidedGenres(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((g) => typeof g === 'string' && g.trim().length > 0);
  } catch {
    return [];
  }
}

function parseStoredItems(raw: string | null): StoredMovieItem[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const items: StoredMovieItem[] = [];
    const seen = new Set<number>();
    for (const entry of parsed) {
      let mid: number | null = null;
      let addedAt = new Date().toISOString();
      if (typeof entry === 'number' && Number.isInteger(entry) && entry > 0) {
        mid = entry;
      } else if (typeof entry === 'string' && /^\d+$/.test(entry)) {
        mid = Number(entry);
      } else if (entry && typeof entry === 'object' && entry.movie_id) {
        const idNum = Number(entry.movie_id);
        if (Number.isInteger(idNum) && idNum > 0) {
          mid = idNum;
          if (entry.added_at && typeof entry.added_at === 'string') {
            addedAt = entry.added_at;
          }
        }
      }
      if (mid != null && !seen.has(mid)) {
        seen.add(mid);
        items.push({ movie_id: mid, added_at: addedAt });
      }
    }
    return items;
  } catch {
    return [];
  }
}

function parseStoredStatuses(): MovieStatusItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const rawStatuses = localStorage.getItem('moierec_movie_statuses');
    if (rawStatuses) {
      const parsed = JSON.parse(rawStatuses);
      if (Array.isArray(parsed)) {
        const items: MovieStatusItem[] = [];
        const seen = new Set<number>();
        for (const it of parsed) {
          if (
            it &&
            typeof it === 'object' &&
            Number.isInteger(Number(it.movie_id)) &&
            Number(it.movie_id) > 0 &&
            ['plan', 'watching', 'watched', 'dropped'].includes(it.status)
          ) {
            const mid = Number(it.movie_id);
            if (!seen.has(mid)) {
              seen.add(mid);
              items.push({
                movie_id: mid,
                status: it.status,
                updated_at: it.updated_at || new Date().toISOString(),
              });
            }
          }
        }
        return items;
      }
    }

    // Safe one-time migration from existing moierec_watchlist to 'plan'
    const rawWatchlist = localStorage.getItem('moierec_watchlist');
    if (rawWatchlist) {
      const oldItems = parseStoredItems(rawWatchlist);
      if (oldItems.length > 0) {
        const migrated: MovieStatusItem[] = oldItems.map((item) => ({
          movie_id: item.movie_id,
          status: 'plan' as WatchStatus,
          updated_at: item.added_at || new Date().toISOString(),
        }));
        try {
          localStorage.setItem('moierec_movie_statuses', JSON.stringify(migrated));
        } catch {
          // ignore
        }
        return migrated;
      }
    }
    return [];
  } catch {
    return [];
  }
}

function parseDismissedNudges(): Set<number> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem('moierec_dismissed_watched_nudges');
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.map(Number).filter((n) => Number.isInteger(n) && n > 0));
  } catch {
    return new Set();
  }
}

export const UserTasteProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { showToast } = useToast();

  const [statusItems, setStatusItems] = useState<MovieStatusItem[]>(() =>
    parseStoredStatuses()
  );

  const [dismissedNudges, setDismissedNudges] = useState<Set<number>>(() =>
    parseDismissedNudges()
  );

  const [likedItems, setLikedItems] = useState<StoredMovieItem[]>(() =>
    parseStoredItems(localStorage.getItem('moierec_liked'))
  );

  const [dislikedItems, setDislikedItems] = useState<StoredMovieItem[]>(() =>
    parseStoredItems(localStorage.getItem('moierec_disliked'))
  );

  const [onboardingDismissed, setOnboardingDismissed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('moierec_onboarding_dismissed') === 'true';
    } catch {
      return false;
    }
  });

  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(false);

  const [avoidedGenres, setAvoidedGenresState] = useState<string[]>(() =>
    parseAvoidedGenres(localStorage.getItem('moierec_avoided_genres'))
  );

  // Sync statuses to localStorage and keep moierec_watchlist mirror for backward compatibility
  useEffect(() => {
    try {
      localStorage.setItem('moierec_movie_statuses', JSON.stringify(statusItems));
      const planItems = statusItems
        .filter((it) => it.status === 'plan')
        .map((it) => ({ movie_id: it.movie_id, added_at: it.updated_at }));
      localStorage.setItem('moierec_watchlist', JSON.stringify(planItems));
    } catch {
      // storage unavailable
    }
  }, [statusItems]);

  useEffect(() => {
    try {
      localStorage.setItem(
        'moierec_dismissed_watched_nudges',
        JSON.stringify(Array.from(dismissedNudges)),
      );
    } catch {
      // storage unavailable
    }
  }, [dismissedNudges]);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_liked', JSON.stringify(likedItems));
    } catch {
      // storage unavailable
    }
  }, [likedItems]);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_disliked', JSON.stringify(dislikedItems));
    } catch {
      // storage unavailable
    }
  }, [dislikedItems]);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_onboarding_dismissed', String(onboardingDismissed));
    } catch {
      // storage unavailable
    }
  }, [onboardingDismissed]);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_avoided_genres', JSON.stringify(avoidedGenres));
    } catch {
      // storage unavailable
    }
  }, [avoidedGenres]);

  const dismissOnboarding = () => {
    setOnboardingDismissed(true);
    setIsOnboardingOpen(false);
  };

  const getMovieId = (movie: Movie | ApiMovie | number): number | null => {
    if (typeof movie === 'number') {
      return Number.isInteger(movie) && movie > 0 ? movie : null;
    }
    const raw = 'movie_id' in movie ? movie.movie_id : ('id' in movie ? (movie as any).id : null);
    const n = Number(raw);
    return Number.isInteger(n) && n > 0 ? n : null;
  };

  const statusMap = new Map<number, WatchStatus>();
  for (const it of statusItems) {
    statusMap.set(it.movie_id, it.status);
  }

  const getWatchStatus = (movieId: string | number): WatchStatus | null => {
    const n = Number(movieId);
    return statusMap.get(n) || null;
  };

  const setWatchStatus = (
    movie: Movie | ApiMovie | number,
    status: WatchStatus | null,
  ) => {
    const mid = getMovieId(movie);
    if (!mid) return;
    const title =
      typeof movie === 'object' && movie && 'title' in movie
        ? movie.title
        : `Movie #${mid}`;

    setStatusItems((prev) => {
      const existing = prev.find((it) => it.movie_id === mid);
      if (existing?.status === status) return prev;

      const filtered = prev.filter((it) => it.movie_id !== mid);
      if (!status) {
        showToast(`Removed "${title}" from your lists`, { icon: 'info' });
        return filtered;
      }

      const updated = [
        { movie_id: mid, status, updated_at: new Date().toISOString() },
        ...filtered,
      ];

      const statusLabels: Record<WatchStatus, string> = {
        plan: 'Plan to watch',
        watching: 'Watching',
        watched: 'Watched',
        dropped: 'Dropped',
      };
      showToast(`Marked "${title}" as ${statusLabels[status]}`, { icon: 'info' });
      return updated;
    });
  };

  const planMovieIds = statusItems
    .filter((it) => it.status === 'plan')
    .map((it) => it.movie_id);

  const watchingMovieIds = statusItems
    .filter((it) => it.status === 'watching')
    .map((it) => it.movie_id);

  const watchedMovieIds = statusItems
    .filter((it) => it.status === 'watched')
    .map((it) => it.movie_id);

  const droppedMovieIds = statusItems
    .filter((it) => it.status === 'dropped')
    .map((it) => it.movie_id);

  const watchedAndDroppedIds = statusItems
    .filter((it) => it.status === 'watched' || it.status === 'dropped')
    .map((it) => it.movie_id);

  const isWatchedOrDropped = (movieId: string | number): boolean => {
    const st = getWatchStatus(movieId);
    return st === 'watched' || st === 'dropped';
  };

  const savedMovieCount = statusItems.length;

  const dismissWatchedNudge = (movieId: number) => {
    setDismissedNudges((prev) => {
      const next = new Set(prev);
      next.add(movieId);
      return next;
    });
  };

  const isNudgeDismissed = (movieId: number): boolean => dismissedNudges.has(movieId);

  const clearStatusTab = (status: WatchStatus) => {
    setStatusItems((prev) => prev.filter((it) => it.status !== status));
    const labels: Record<WatchStatus, string> = {
      plan: 'Plan to watch',
      watching: 'Watching',
      watched: 'Watched',
      dropped: 'Dropped',
    };
    showToast(`Cleared ${labels[status]} list`, { icon: 'info' });
  };

  const validLikedIds = likedItems.map((item) => item.movie_id);
  const validWatchlistIds = planMovieIds;
  const validDislikedIds = dislikedItems.map((item) => item.movie_id);

  const watchlistItems: StoredMovieItem[] = statusItems
    .filter((it) => it.status === 'plan')
    .map((it) => ({ movie_id: it.movie_id, added_at: it.updated_at }));

  const watchlist = new Set(validWatchlistIds.map(String));
  const liked = new Set(validLikedIds.map(String));
  const disliked = new Set(validDislikedIds.map(String));

  const isInWatchlist = (movieId: string | number) => getWatchStatus(movieId) === 'plan';
  const isLiked = (movieId: string | number) => liked.has(String(movieId));
  const isDisliked = (movieId: string | number) => disliked.has(String(movieId));

  const toggleWatchlist = (movie: Movie | ApiMovie) => {
    const mid = getMovieId(movie);
    if (!mid) return;
    const current = getWatchStatus(mid);
    if (current === 'plan') {
      setWatchStatus(movie, null);
    } else {
      setWatchStatus(movie, 'plan');
    }
  };

  const toggleLike = (movie: Movie | ApiMovie) => {
    const mid = getMovieId(movie);
    if (!mid) return;
    const wasLiked = liked.has(String(mid));
    if (wasLiked) {
      setLikedItems((prev) => prev.filter((it) => it.movie_id !== mid));
      showToast(`Removed like for "${movie.title}"`, { icon: 'info' });
    } else {
      // Add to liked, remove from disliked
      setLikedItems((prev) => [
        { movie_id: mid, added_at: new Date().toISOString() },
        ...prev.filter((it) => it.movie_id !== mid),
      ]);
      setDislikedItems((prev) => prev.filter((it) => it.movie_id !== mid));
      showToast(`"${movie.title}" added to liked`, { icon: 'heart' });
    }
  };

  const toggleDislike = (movie: Movie | ApiMovie) => {
    const mid = getMovieId(movie);
    if (!mid) return;
    const wasDisliked = disliked.has(String(mid));
    if (wasDisliked) {
      setDislikedItems((prev) => prev.filter((it) => it.movie_id !== mid));
      showToast(`Undid dislike for "${movie.title}"`, { icon: 'info' });
    } else {
      // Add to disliked, remove from liked
      setDislikedItems((prev) => [
        { movie_id: mid, added_at: new Date().toISOString() },
        ...prev.filter((it) => it.movie_id !== mid),
      ]);
      setLikedItems((prev) => prev.filter((it) => it.movie_id !== mid));
      showToast(`Marked "${movie.title}" as Not interested`, { icon: 'info' });
    }
  };

  const removeWatchlist = (movieId: string | number) => {
    setWatchStatus(Number(movieId), null);
  };

  const removeLike = (movieId: string | number) => {
    const mid = Number(movieId);
    setLikedItems((prev) => prev.filter((it) => it.movie_id !== mid));
  };

  const removeDislike = (movieId: string | number) => {
    const mid = Number(movieId);
    setDislikedItems((prev) => prev.filter((it) => it.movie_id !== mid));
  };

  const moveToList = (movieId: number, toList: 'liked' | 'watchlist' | 'disliked') => {
    if (toList === 'liked') {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      toggleLike({ movie_id: movieId, title: `Movie #${movieId}` } as any);
    } else if (toList === 'watchlist') {
      setWatchStatus(movieId, 'plan');
    } else if (toList === 'disliked') {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      toggleDislike({ movie_id: movieId, title: `Movie #${movieId}` } as any);
    }
  };

  const clearWatchlist = () => {
    clearStatusTab('plan');
  };

  const clearLiked = () => {
    setLikedItems([]);
    showToast('Cleared liked picks', { icon: 'info' });
  };

  const clearDisliked = () => {
    setDislikedItems([]);
    showToast('Cleared not interested list', { icon: 'info' });
  };

  const clearAllPicks = () => {
    setLikedItems([]);
    setDislikedItems([]);
    showToast('Cleared movie picks', { icon: 'info' });
  };

  const clearAllData = () => {
    setStatusItems([]);
    setDismissedNudges(new Set());
    setLikedItems([]);
    setDislikedItems([]);
    setOnboardingDismissed(false);
    setAvoidedGenresState([]);
    try {
      localStorage.removeItem('moierec_movie_statuses');
      localStorage.removeItem('moierec_dismissed_watched_nudges');
      localStorage.removeItem('moierec_watchlist');
      localStorage.removeItem('moierec_liked');
      localStorage.removeItem('moierec_disliked');
      localStorage.removeItem('moierec_onboarding_dismissed');
      localStorage.removeItem('moierec_avoided_genres');
    } catch {
      // ignore
    }
    showToast('All browser library data cleared', { icon: 'info' });
  };

  const toggleAvoidedGenre = (genre: string) => {
    const trimmed = genre.trim();
    if (!trimmed) return;
    setAvoidedGenresState((prev) => {
      const exists = prev.some((g) => g.toLowerCase() === trimmed.toLowerCase());
      if (exists) {
        showToast(`Removed "${trimmed}" from avoided genres`, { icon: 'info' });
        return prev.filter((g) => g.toLowerCase() !== trimmed.toLowerCase());
      } else {
        showToast(`Hiding "${trimmed}" titles from feeds`, { icon: 'info' });
        return [...prev, trimmed];
      }
    });
  };

  const setAvoidedGenres = (genres: string[]) => {
    const cleaned = Array.from(new Set(genres.map((g) => g.trim()).filter(Boolean)));
    setAvoidedGenresState(cleaned);
  };

  const clearAvoidedGenres = () => {
    setAvoidedGenresState([]);
    showToast('Cleared avoided genres', { icon: 'info' });
  };

  const isGenreAvoided = (genre: string) => {
    const gLower = genre.trim().toLowerCase();
    return avoidedGenres.some((g) => g.toLowerCase() === gLower);
  };

  const cleanLegacyIds = (validIds: Set<number>) => {
    setStatusItems((prev) => prev.filter((it) => validIds.has(it.movie_id)));
    setLikedItems((prev) => prev.filter((it) => validIds.has(it.movie_id)));
    setDislikedItems((prev) => prev.filter((it) => validIds.has(it.movie_id)));
  };

  return (
    <UserTasteContext.Provider
      value={{
        watchlist,
        liked,
        disliked,
        watchlistItems,
        likedItems,
        dislikedItems,
        validLikedIds,
        validWatchlistIds,
        validDislikedIds,
        isOnboardingOpen,
        onboardingDismissed,
        setIsOnboardingOpen,
        dismissOnboarding,
        isInWatchlist,
        isLiked,
        isDisliked,
        toggleWatchlist,
        toggleLike,
        toggleDislike,
        removeWatchlist,
        removeLike,
        removeDislike,
        moveToList,
        clearWatchlist,
        clearLiked,
        clearDisliked,
        clearAllPicks,
        clearAllData,
        cleanLegacyIds,
        avoidedGenres,
        toggleAvoidedGenre,
        setAvoidedGenres,
        clearAvoidedGenres,
        isGenreAvoided,
        statusItems,
        getWatchStatus,
        setWatchStatus,
        planMovieIds,
        watchingMovieIds,
        watchedMovieIds,
        droppedMovieIds,
        watchedAndDroppedIds,
        savedMovieCount,
        isWatchedOrDropped,
        clearStatusTab,
        dismissWatchedNudge,
        isNudgeDismissed,
      }}
    >
      {children}
    </UserTasteContext.Provider>
  );
};

export const useUserTaste = (): UserTasteContextType => {
  const context = useContext(UserTasteContext);
  if (!context) {
    throw new Error('useUserTaste must be used within a UserTasteProvider');
  }
  return context;
};
