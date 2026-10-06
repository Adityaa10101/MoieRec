import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Movie } from '../types/movie';
import type { ApiMovie } from '../api/types';
import { useToast } from './ToastContext';

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
}

const UserTasteContext = createContext<UserTasteContextType | undefined>(undefined);

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

export const UserTasteProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { showToast } = useToast();

  const [watchlistItems, setWatchlistItems] = useState<StoredMovieItem[]>(() =>
    parseStoredItems(localStorage.getItem('moierec_watchlist'))
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

  // Sync state to localStorage with only movie_id and added_at
  useEffect(() => {
    try {
      localStorage.setItem('moierec_watchlist', JSON.stringify(watchlistItems));
    } catch {
      // storage unavailable
    }
  }, [watchlistItems]);

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

  const dismissOnboarding = () => {
    setOnboardingDismissed(true);
    setIsOnboardingOpen(false);
  };

  const validLikedIds = likedItems.map((item) => item.movie_id);
  const validWatchlistIds = watchlistItems.map((item) => item.movie_id);
  const validDislikedIds = dislikedItems.map((item) => item.movie_id);

  const watchlist = new Set(validWatchlistIds.map(String));
  const liked = new Set(validLikedIds.map(String));
  const disliked = new Set(validDislikedIds.map(String));

  const isInWatchlist = (movieId: string | number) => watchlist.has(String(movieId));
  const isLiked = (movieId: string | number) => liked.has(String(movieId));
  const isDisliked = (movieId: string | number) => disliked.has(String(movieId));

  const getMovieId = (movie: Movie | ApiMovie): number | null => {
    const raw = 'movie_id' in movie ? movie.movie_id : ('id' in movie ? (movie as any).id : null);
    const n = Number(raw);
    return Number.isInteger(n) && n > 0 ? n : null;
  };

  const toggleWatchlist = (movie: Movie | ApiMovie) => {
    const mid = getMovieId(movie);
    if (!mid) return;
    const wasIn = watchlist.has(String(mid));
    if (wasIn) {
      setWatchlistItems((prev) => prev.filter((it) => it.movie_id !== mid));
      showToast(`Removed "${movie.title}" from watchlist`, { icon: 'info' });
    } else {
      setWatchlistItems((prev) => [
        { movie_id: mid, added_at: new Date().toISOString() },
        ...prev.filter((it) => it.movie_id !== mid),
      ]);
      showToast(`"${movie.title}" added to your watchlist`, { icon: 'bookmark' });
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
    const mid = Number(movieId);
    setWatchlistItems((prev) => prev.filter((it) => it.movie_id !== mid));
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
    const now = new Date().toISOString();
    if (toList === 'liked') {
      setLikedItems((prev) => [{ movie_id: movieId, added_at: now }, ...prev.filter((it) => it.movie_id !== movieId)]);
      setWatchlistItems((prev) => prev.filter((it) => it.movie_id !== movieId));
      setDislikedItems((prev) => prev.filter((it) => it.movie_id !== movieId));
      showToast('Moved to Liked picks', { icon: 'heart' });
    } else if (toList === 'watchlist') {
      setWatchlistItems((prev) => [{ movie_id: movieId, added_at: now }, ...prev.filter((it) => it.movie_id !== movieId)]);
      setLikedItems((prev) => prev.filter((it) => it.movie_id !== movieId));
      setDislikedItems((prev) => prev.filter((it) => it.movie_id !== movieId));
      showToast('Moved to Watchlist', { icon: 'bookmark' });
    } else if (toList === 'disliked') {
      setDislikedItems((prev) => [{ movie_id: movieId, added_at: now }, ...prev.filter((it) => it.movie_id !== movieId)]);
      setLikedItems((prev) => prev.filter((it) => it.movie_id !== movieId));
      setWatchlistItems((prev) => prev.filter((it) => it.movie_id !== movieId));
      showToast('Moved to Not interested', { icon: 'info' });
    }
  };

  const clearWatchlist = () => {
    setWatchlistItems([]);
    showToast('Cleared watchlist', { icon: 'info' });
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
    setWatchlistItems([]);
    setLikedItems([]);
    setDislikedItems([]);
    setOnboardingDismissed(false);
    try {
      localStorage.removeItem('moierec_watchlist');
      localStorage.removeItem('moierec_liked');
      localStorage.removeItem('moierec_disliked');
      localStorage.removeItem('moierec_onboarding_dismissed');
    } catch {
      // ignore
    }
    showToast('All browser library data cleared', { icon: 'info' });
  };

  const cleanLegacyIds = (validIds: Set<number>) => {
    setWatchlistItems((prev) => prev.filter((it) => validIds.has(it.movie_id)));
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
