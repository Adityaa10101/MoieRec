import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Movie } from '../types/movie';
import { useToast } from './ToastContext';

interface UserTasteContextType {
  watchlist: Set<string>;
  liked: Set<string>;
  disliked: Set<string>;
  validLikedIds: number[];
  validDislikedIds: number[];
  isOnboardingOpen: boolean;
  onboardingDismissed: boolean;
  setIsOnboardingOpen: (open: boolean) => void;
  dismissOnboarding: () => void;
  isInWatchlist: (movieId: string | number) => boolean;
  isLiked: (movieId: string | number) => boolean;
  isDisliked: (movieId: string | number) => boolean;
  toggleWatchlist: (movie: Movie) => void;
  toggleLike: (movie: Movie) => void;
  toggleDislike: (movie: Movie) => void;
  removeLike: (movieId: string | number) => void;
  removeDislike: (movieId: string | number) => void;
  clearAllPicks: () => void;
}

const UserTasteContext = createContext<UserTasteContextType | undefined>(undefined);

// Helper to test if ID is numeric (MovieLens ID)
const isNumericId = (id: string | number) => /^\d+$/.test(String(id));

export const UserTasteProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { showToast } = useToast();

  const [watchlist, setWatchlist] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('moierec_watchlist');
      if (!saved) return new Set();
      const parsed: string[] = JSON.parse(saved);
      return new Set(parsed.filter(isNumericId));
    } catch {
      return new Set();
    }
  });

  const [liked, setLiked] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('moierec_liked');
      if (!saved) return new Set();
      const parsed: string[] = JSON.parse(saved);
      // Filter out invalid legacy string slugs (like 'arrival', 'oppenheimer')
      return new Set(parsed.filter(isNumericId));
    } catch {
      return new Set();
    }
  });

  const [disliked, setDisliked] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('moierec_disliked');
      if (!saved) return new Set();
      const parsed: string[] = JSON.parse(saved);
      return new Set(parsed.filter(isNumericId));
    } catch {
      return new Set();
    }
  });

  const [onboardingDismissed, setOnboardingDismissed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('moierec_onboarding_dismissed') === 'true';
    } catch {
      return false;
    }
  });

  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(false);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_watchlist', JSON.stringify(Array.from(watchlist)));
    } catch {
      // storage unavailable
    }
  }, [watchlist]);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_liked', JSON.stringify(Array.from(liked)));
    } catch {
      // storage unavailable
    }
  }, [liked]);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_disliked', JSON.stringify(Array.from(disliked)));
    } catch {
      // storage unavailable
    }
  }, [disliked]);

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

  const validLikedIds = Array.from(liked)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n > 0);

  const validDislikedIds = Array.from(disliked)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n > 0);

  const isInWatchlist = (movieId: string | number) => watchlist.has(String(movieId));
  const isLiked = (movieId: string | number) => liked.has(String(movieId));
  const isDisliked = (movieId: string | number) => disliked.has(String(movieId));

  const toggleWatchlist = (movie: Movie) => {
    const idStr = String(movie.movie_id || movie.id);
    const wasIn = watchlist.has(idStr);
    setWatchlist((prev) => {
      const next = new Set(prev);
      if (wasIn) next.delete(idStr);
      else next.add(idStr);
      return next;
    });
    if (wasIn) {
      showToast(`Removed "${movie.title}" from watchlist`, { icon: 'info' });
    } else {
      showToast(`"${movie.title}" added to your screening watchlist`, { icon: 'bookmark' });
    }
  };

  const toggleLike = (movie: Movie) => {
    const idStr = String(movie.movie_id || movie.id);
    const wasLiked = liked.has(idStr);
    setLiked((prev) => {
      const next = new Set(prev);
      if (wasLiked) next.delete(idStr);
      else next.add(idStr);
      return next;
    });
    if (wasLiked) {
      showToast(`Removed like for "${movie.title}"`, { icon: 'info' });
    } else {
      setDisliked((d) => {
        const nd = new Set(d);
        nd.delete(idStr);
        return nd;
      });
      showToast(`"${movie.title}" added to liked`, { icon: 'heart' });
    }
  };

  const toggleDislike = (movie: Movie) => {
    const idStr = String(movie.movie_id || movie.id);
    const wasDisliked = disliked.has(idStr);
    setDisliked((prev) => {
      const next = new Set(prev);
      if (wasDisliked) next.delete(idStr);
      else next.add(idStr);
      return next;
    });
    if (!wasDisliked) {
      setLiked((l) => {
        const nl = new Set(l);
        nl.delete(idStr);
        return nl;
      });
      showToast(`Preferences adjusted: less titles like "${movie.title}"`, { icon: 'info' });
    }
  };

  const removeLike = (movieId: string | number) => {
    const idStr = String(movieId);
    setLiked((prev) => {
      const next = new Set(prev);
      next.delete(idStr);
      return next;
    });
  };

  const removeDislike = (movieId: string | number) => {
    const idStr = String(movieId);
    setDisliked((prev) => {
      const next = new Set(prev);
      next.delete(idStr);
      return next;
    });
  };

  const clearAllPicks = () => {
    setLiked(new Set());
    setDisliked(new Set());
    showToast('Cleared all taste picks', { icon: 'info' });
  };

  return (
    <UserTasteContext.Provider
      value={{
        watchlist,
        liked,
        disliked,
        validLikedIds,
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
        removeLike,
        removeDislike,
        clearAllPicks,
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
