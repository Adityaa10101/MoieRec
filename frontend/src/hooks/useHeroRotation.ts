import { useState, useEffect, useCallback, useRef } from 'react';

export interface UseHeroRotationOptions {
  count: number;
  intervalMs?: number;
  isTextHovered?: boolean;
  onRotate?: (targetIndex: number) => number | void;
}

export function useHeroRotation({
  count,
  intervalMs = 10000,
  isTextHovered = false,
  onRotate,
}: UseHeroRotationOptions) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [rotationKey, setRotationKey] = useState(0);

  // Store onRotate in a ref so changes in onRotate's identity never trigger the timeout effect
  const onRotateRef = useRef(onRotate);
  useEffect(() => {
    onRotateRef.current = onRotate;
  });

  // prefers-reduced-motion
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Pause only when document.hidden is true (not window blur or focus loss)
  const [isDocumentHidden, setIsDocumentHidden] = useState<boolean>(() => {
    if (typeof document === 'undefined') return false;
    return document.hidden;
  });

  useEffect(() => {
    if (typeof document === 'undefined') return;

    const handleVisibilityChange = () => {
      const hidden = document.hidden;
      setIsDocumentHidden((prev) => {
        // When resuming from hidden to visible, bump rotationKey so timer & progress bar restart fresh in sync
        if (prev && !hidden) {
          setRotationKey((k) => k + 1);
        }
        return hidden;
      });
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  // Pause only when document is hidden, text block hovered, reduced motion, or < 2 movies
  const isPaused = isDocumentHidden || isTextHovered || prefersReducedMotion || count < 2;

  // Keep index within bounds if count shrinks
  useEffect(() => {
    if (count > 0 && currentIndex >= count) {
      setCurrentIndex(0);
    }
  }, [count, currentIndex]);

  // Unified goTo for manual navigation (dots, arrows, swipe) and rotation
  const goTo = useCallback(
    (targetIndex: number) => {
      if (count < 1) return;
      const safeIndex = ((targetIndex % count) + count) % count;
      setRotationKey((k) => k + 1);
      let resolved = safeIndex;
      if (onRotateRef.current) {
        const ret = onRotateRef.current(safeIndex);
        if (typeof ret === 'number') {
          resolved = ret;
        }
      }
      setCurrentIndex(resolved);
    },
    [count],
  );

  const nextSlide = useCallback(() => {
    goTo(currentIndex + 1);
  }, [goTo, currentIndex]);

  const prevSlide = useCallback(() => {
    goTo(currentIndex - 1);
  }, [goTo, currentIndex]);

  // Timeout effect depends ONLY on primitives:
  // [currentIndex, count, isPaused, rotationKey, intervalMs]
  // A re-render alone (like/dislike/cursor/state change) will NEVER restart the timer.
  useEffect(() => {
    if (isPaused || count < 2) return;

    const timer = setTimeout(() => {
      const nextIndex = (currentIndex + 1) % count;
      setRotationKey((k) => k + 1);
      let resolved = nextIndex;
      if (onRotateRef.current) {
        const ret = onRotateRef.current(nextIndex);
        if (typeof ret === 'number') {
          resolved = ret;
        }
      }
      setCurrentIndex(resolved);
    }, intervalMs);

    return () => {
      clearTimeout(timer);
    };
  }, [currentIndex, count, isPaused, rotationKey, intervalMs]);

  return {
    currentIndex,
    setCurrentIndex,
    rotationKey,
    goTo,
    nextSlide,
    prevSlide,
    isPaused,
    prefersReducedMotion,
  };
}
