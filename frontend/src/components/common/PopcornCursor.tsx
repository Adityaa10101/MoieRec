import React, { useEffect, useState, useRef } from 'react';
import { usePopcornCursor } from '../../context/PopcornCursorContext';

interface Particle {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export const PopcornCursor: React.FC = () => {
  const { isCursorEnabled, isCardHovered } = usePopcornCursor();
  const cursorRef = useRef<HTMLDivElement>(null);
  const posRef = useRef<{ x: number; y: number }>({ x: -100, y: -100 });
  const isVisibleRef = useRef<boolean>(false);
  const [isOverClickable, setIsOverClickable] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });
  const nextParticleId = useRef(0);

  // Monitor prefers-reduced-motion dynamically
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mq.addEventListener('change', handleChange);
    return () => mq.removeEventListener('change', handleChange);
  }, []);

  // Suppress native cursor ONLY when the custom cursor is actively mounted, enabled, and visible
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const isTouchOnly =
      window.matchMedia('(pointer: coarse)').matches &&
      !window.matchMedia('(pointer: fine)').matches &&
      !window.matchMedia('(any-pointer: fine)').matches;

    if (!isCursorEnabled || isTouchOnly) {
      document.documentElement.classList.remove('custom-cursor-active');
      return;
    }

    if (isVisible) {
      document.documentElement.classList.add('custom-cursor-active');
    } else {
      document.documentElement.classList.remove('custom-cursor-active');
    }

    return () => {
      document.documentElement.classList.remove('custom-cursor-active');
    };
  }, [isCursorEnabled, isVisible]);

  // Pointer tracking & click burst
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const isTouchOnly =
      window.matchMedia('(pointer: coarse)').matches &&
      !window.matchMedia('(pointer: fine)').matches &&
      !window.matchMedia('(any-pointer: fine)').matches;

    if (!isCursorEnabled || isTouchOnly) {
      return;
    }

    const handleMouseMove = (e: MouseEvent) => {
      posRef.current.x = e.clientX;
      posRef.current.y = e.clientY;

      if (cursorRef.current) {
        cursorRef.current.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
      }

      if (!isVisibleRef.current) {
        isVisibleRef.current = true;
        setIsVisible(true);
      }

      const target = e.target as HTMLElement | null;
      if (target) {
        const isClickable = !!target.closest(
          'button, a, input, select, textarea, [role="button"], label, [onclick]'
        );
        setIsOverClickable((prev) => (prev !== isClickable ? isClickable : prev));
      }
    };

    const handleMouseLeave = () => {
      isVisibleRef.current = false;
      setIsVisible(false);
    };

    const handleWindowBlur = () => {
      isVisibleRef.current = false;
      setIsVisible(false);
    };

    const handleClick = (e: MouseEvent) => {
      // If reduced motion is on, disable particles completely
      if (prefersReducedMotion) return;

      const newParticles: Particle[] = [
        {
          id: nextParticleId.current++,
          x: e.clientX,
          y: e.clientY,
          vx: (Math.random() - 0.5) * 5,
          vy: -Math.random() * 5 - 2,
        },
        {
          id: nextParticleId.current++,
          x: e.clientX,
          y: e.clientY,
          vx: (Math.random() - 0.5) * 5,
          vy: -Math.random() * 5 - 2,
        },
        {
          id: nextParticleId.current++,
          x: e.clientX,
          y: e.clientY,
          vx: (Math.random() - 0.5) * 5,
          vy: -Math.random() * 5 - 2,
        },
      ];

      setParticles((prev) => [...prev, ...newParticles]);

      setTimeout(() => {
        setParticles((prev) => prev.filter((p) => !newParticles.some((np) => np.id === p.id)));
      }, 200);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('blur', handleWindowBlur);
    window.addEventListener('click', handleClick);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('blur', handleWindowBlur);
      window.removeEventListener('click', handleClick);
    };
  }, [isCursorEnabled, prefersReducedMotion]);

  // If disabled or not yet active in window, do not render custom elements
  if (!isCursorEnabled || !isVisible) {
    return null;
  }

  return (
    <div
      className="pointer-events-none fixed inset-0 z-[999999] overflow-hidden"
      aria-hidden="true"
      id="moierec-popcorn-cursor-root"
    >
      {/* Exactly ONE custom cursor visual element following the pointer */}
      <div
        ref={cursorRef}
        id="moierec-custom-cursor"
        className="fixed top-0 left-0 pointer-events-none -translate-x-1/2 -translate-y-1/2 will-change-transform"
        style={{
          transform: `translate3d(${posRef.current.x}px, ${posRef.current.y}px, 0)`,
        }}
      >
        {isOverClickable ? (
          // Switches into a single precision target ring over buttons and clickable controls
          <div
            id="moierec-cursor-target"
            className={`w-3.5 h-3.5 rounded-full border-2 border-amber-400 bg-amber-400/20 shadow-[0_0_10px_rgba(245,158,11,0.9)] ${
              prefersReducedMotion ? '' : 'transition-transform duration-100 ease-out'
            }`}
          />
        ) : (
          // Single tiny ~14px gold popcorn kernel with subtle scale/glow on movie cards
          <div
            id="moierec-cursor-kernel"
            className={`will-change-transform ${
              prefersReducedMotion ? '' : 'transition-transform duration-150 ease-out'
            } ${
              isCardHovered
                ? 'scale-125 filter drop-shadow-[0_0_10px_rgba(245,158,11,0.75)]'
                : 'scale-100 filter drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]'
            }`}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              className="text-amber-400 block"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 3C9.5 3 8 5 8 7C6 7 4 8.5 4 11C4 13.5 6 15 8 15C8 17 9.5 19 12 19C14.5 19 16 17 16 15C18 15 20 13.5 20 11C20 8.5 18 7 16 7C16 5 14.5 3 12 3Z"
                fill="currentColor"
                fillOpacity="0.95"
              />
              <circle cx="12" cy="11" r="2.5" fill="#fef3c7" />
            </svg>
          </div>
        )}
      </div>

      {/* Temporary click spark burst (only if not reduced motion) */}
      {!prefersReducedMotion &&
        particles.map((p) => (
          <div
            key={p.id}
            className="absolute w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(245,158,11,0.9)] animate-ping pointer-events-none -translate-x-1/2 -translate-y-1/2"
            style={{
              left: `${p.x + p.vx * 3}px`,
              top: `${p.y + p.vy * 3}px`,
            }}
          />
        ))}
    </div>
  );
};
