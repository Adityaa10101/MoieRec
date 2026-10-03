import React, { createContext, useContext, useState, useEffect } from 'react';

interface PopcornCursorContextType {
  isCursorEnabled: boolean;
  toggleCursor: () => void;
  isCardHovered: boolean;
  setIsCardHovered: (val: boolean) => void;
}

const PopcornCursorContext = createContext<PopcornCursorContextType | undefined>(undefined);

export const PopcornCursorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isCursorEnabled, setIsCursorEnabled] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('moierec_popcorn_cursor');
      if (saved !== null) {
        return saved === 'true';
      }
      // Enabled by default on fine-pointer devices (not strictly touch-only)
      const isTouchOnly =
        typeof window !== 'undefined' &&
        window.matchMedia('(pointer: coarse)').matches &&
        !window.matchMedia('(pointer: fine)').matches &&
        !window.matchMedia('(any-pointer: fine)').matches;
      return !isTouchOnly;
    } catch {
      return true;
    }
  });

  const [isCardHovered, setIsCardHovered] = useState<boolean>(false);

  useEffect(() => {
    try {
      localStorage.setItem('moierec_popcorn_cursor', String(isCursorEnabled));
    } catch {
      // storage unavailable
    }
  }, [isCursorEnabled]);

  const toggleCursor = () => {
    setIsCursorEnabled((prev) => !prev);
  };

  return (
    <PopcornCursorContext.Provider
      value={{
        isCursorEnabled,
        toggleCursor,
        isCardHovered,
        setIsCardHovered,
      }}
    >
      {children}
    </PopcornCursorContext.Provider>
  );
};

export const usePopcornCursor = (): PopcornCursorContextType => {
  const context = useContext(PopcornCursorContext);
  if (!context) {
    throw new Error('usePopcornCursor must be used within a PopcornCursorProvider');
  }
  return context;
};
