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

  // Derive pageActive directly from document.hidden and document.hasFocus()
  // Active only when tab is visible AND window has focus
  const [isPageActive, setIsPageActive] = useState<boolean>(() => {
    if (typeof document === 'undefined') return true;
    return !document.hidden && document.hasFocus();
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const updateActive = () => {
      const active = !document.hidden && document.hasFocus();
      setIsPageActive((prev) => {
        // When resuming after inactive (alt-tab back or tab switch back),
        // restart a full 10s and bump rotationKey so the progress bar animation restarts in sync
        if (!prev && active) {
          setRotationKey((k) => k + 1);
        }
        return active;
      });
    };

    window.addEventListener('focus', updateActive);
    window.addEventListener('blur', updateActive);
    document.addEventListener('visibilitychange', updateActive);

    return () => {
      window.removeEventListener('focus', updateActive);
      window.removeEventListener('blur', updateActive);
      document.removeEventListener('visibilitychange', updateActive);
    };
  }, []);

  // Pause only when page is inactive, text/buttons block is hovered, reduced-motion is set, or < 2 movies
  const isPaused = !isPageActive || isTextHovered || prefersReducedMotion || count < 2;

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
