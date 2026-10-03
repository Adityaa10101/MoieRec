import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import type { Movie } from '../types/movie';

interface AmbientBackdropContextType {
  activeBackdrop: string | null;
  setHoveredMovie: (movie: Movie | null) => void;
}

const AmbientBackdropContext = createContext<AmbientBackdropContextType | undefined>(undefined);

export const AmbientBackdropProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeBackdrop, setActiveBackdrop] = useState<string | null>(null);
  const timeoutRef = useRef<number | null>(null);

  const setHoveredMovie = (movie: Movie | null) => {
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (movie) {
      const backdropUrl = movie.backdrop || movie.poster || null;
      setActiveBackdrop(backdropUrl);
    } else {
      // 400ms graceful fadeout back to neutral dark background as specified in design system
      timeoutRef.current = window.setTimeout(() => {
        setActiveBackdrop(null);
      }, 400);
    }
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <AmbientBackdropContext.Provider value={{ activeBackdrop, setHoveredMovie }}>
      {/* Ambient Lighting & Backdrop Layer */}
      <div
        className="pointer-events-none fixed inset-0 z-0 overflow-hidden transition-opacity duration-700 ease-out"
        aria-hidden="true"
      >
        {activeBackdrop ? (
          <div
            className="absolute inset-0 bg-cover bg-center transition-all duration-700 ease-out scale-105 filter blur-[90px] opacity-20 brightness-75 saturate-150"
            style={{ backgroundImage: `url(${activeBackdrop})` }}
          />
        ) : (
          /* Subtle ambient warm gold light glow at the top when neutral */
          <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[650px] bg-amber-500/5 rounded-full blur-[140px] transition-all duration-1000 ease-out" />
        )}
      </div>

      {children}
    </AmbientBackdropContext.Provider>
  );
};

export const useAmbientBackdrop = (): AmbientBackdropContextType => {
  const context = useContext(AmbientBackdropContext);
  if (!context) {
    throw new Error('useAmbientBackdrop must be used within an AmbientBackdropProvider');
  }
  return context;
};
