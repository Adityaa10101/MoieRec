import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Movie } from '../types/movie';
import { useToast } from './ToastContext';

interface UserTasteContextType {
  watchlist: Set<string>;
  liked: Set<string>;
  disliked: Set<string>;
  isInWatchlist: (movieId: string) => boolean;
  isLiked: (movieId: string) => boolean;
  isDisliked: (movieId: string) => boolean;
  toggleWatchlist: (movie: Movie) => void;
  toggleLike: (movie: Movie) => void;
  toggleDislike: (movie: Movie) => void;
}

const UserTasteContext = createContext<UserTasteContextType | undefined>(undefined);

export const UserTasteProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { showToast } = useToast();

  const [watchlist, setWatchlist] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('moierec_watchlist');
      return saved ? new Set(JSON.parse(saved)) : new Set(['blade-runner-2049']);
    } catch {
      return new Set(['blade-runner-2049']);
    }
  });

  const [liked, setLiked] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('moierec_liked');
      return saved ? new Set(JSON.parse(saved)) : new Set(['arrival', 'oppenheimer']);
    } catch {
      return new Set(['arrival', 'oppenheimer']);
    }
  });

  const [disliked, setDisliked] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('moierec_disliked');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

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

  const isInWatchlist = (movieId: string) => watchlist.has(movieId);
  const isLiked = (movieId: string) => liked.has(movieId);
  const isDisliked = (movieId: string) => disliked.has(movieId);

  const toggleWatchlist = (movie: Movie) => {
    setWatchlist((prev) => {
      const next = new Set(prev);
      if (next.has(movie.id)) {
        next.delete(movie.id);
        showToast(`Removed "${movie.title}" from watchlist`, { icon: 'info' });
      } else {
        next.add(movie.id);
        showToast(`"${movie.title}" added to your screening watchlist`, { icon: 'bookmark' });
      }
      return next;
    });
  };

  const toggleLike = (movie: Movie) => {
    setLiked((prev) => {
      const next = new Set(prev);
      if (next.has(movie.id)) {
        next.delete(movie.id);
        showToast(`Removed like for "${movie.title}"`, { icon: 'info' });
      } else {
        next.add(movie.id);
        setDisliked((d) => {
          const nd = new Set(d);
          nd.delete(movie.id);
          return nd;
        });
        showToast(`"${movie.title}" added to liked`, { icon: 'heart' });
      }
      return next;
    });
  };

  const toggleDislike = (movie: Movie) => {
    setDisliked((prev) => {
      const next = new Set(prev);
      if (next.has(movie.id)) {
        next.delete(movie.id);
      } else {
        next.add(movie.id);
        setLiked((l) => {
          const nl = new Set(l);
          nl.delete(movie.id);
          return nl;
        });
        showToast(`Preferences adjusted: less titles like "${movie.title}"`, { icon: 'info' });
      }
      return next;
    });
  };

  return (
    <UserTasteContext.Provider
      value={{
        watchlist,
        liked,
        disliked,
        isInWatchlist,
        isLiked,
        isDisliked,
        toggleWatchlist,
        toggleLike,
        toggleDislike,
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
