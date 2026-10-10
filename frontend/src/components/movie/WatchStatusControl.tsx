import React, { useState, useRef, useEffect, useLayoutEffect, useCallback, useId } from 'react';
import { createPortal } from 'react-dom';
import {
  Bookmark,
  Play,
  Check,
  XCircle,
  Plus,
  ChevronDown,
  Trash2,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import type { Movie } from '../../types/movie';
import type { ApiMovie } from '../../api/types';
import { useUserTaste, type WatchStatus } from '../../context/UserTasteContext';

interface WatchStatusControlProps {
  movie: Movie | ApiMovie;
  variant?: 'detail' | 'hero' | 'card' | 'inline';
  className?: string;
}

const STATUS_CONFIG: Record<
  WatchStatus,
  {
    label: string;
    shortLabel: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  plan: {
    label: 'Plan to watch',
    shortLabel: 'Plan',
    icon: Bookmark,
  },
  watching: {
    label: 'Watching',
    shortLabel: 'Watching',
    icon: Play,
  },
  watched: {
    label: 'Watched',
    shortLabel: 'Watched',
    icon: Check,
  },
  dropped: {
    label: 'Dropped',
    shortLabel: 'Dropped',
    icon: XCircle,
  },
};

export const WatchStatusControl: React.FC<WatchStatusControlProps> = ({
  movie,
  variant = 'detail',
  className = '',
}) => {
  const {
    getWatchStatus,
    setWatchStatus,
    isLiked,
    isDisliked,
    toggleLike,
    toggleDislike,
    dismissWatchedNudge,
    isNudgeDismissed,
  } = useUserTaste();

  const [isOpen, setIsOpen] = useState(false);
  const [showNudge, setShowNudge] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const nudgeRef = useRef<HTMLDivElement>(null);

  const uniqueId = useId();
  const menuId = `watch-status-menu-${uniqueId.replace(/:/g, '')}`;

  const rawId = 'movie_id' in movie ? movie.movie_id : ('id' in movie ? (movie as any).id : null);
  const mid = Number(rawId);
  const title = movie.title || `Movie #${mid}`;

  const currentStatus = mid ? getWatchStatus(mid) : null;
  const isRated = mid ? isLiked(mid) || isDisliked(mid) : false;

  const [menuCoords, setMenuCoords] = useState<{
    top: number;
    left: number;
    placement: 'bottom' | 'top';
  }>({
    top: 0,
    left: 0,
    placement: 'bottom',
  });

  const [nudgeCoords, setNudgeCoords] = useState<{
    top: number;
    left: number;
    placement: 'bottom' | 'top';
  }>({
    top: 0,
    left: 0,
    placement: 'bottom',
  });

  // Calculate position for the portaled menu
  const updateMenuPosition = useCallback(() => {
    if (!triggerRef.current) return;
    const triggerRect = triggerRef.current.getBoundingClientRect();
    const menuEl = menuRef.current;

    const isCompact = variant === 'card' || variant === 'inline';
    const menuWidth = menuEl ? menuEl.offsetWidth : (isCompact ? 176 : 224);
    const menuHeight = menuEl ? menuEl.offsetHeight : (currentStatus ? 218 : 178);

    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const padding = 8;
    const offset = 6;

    const spaceBelow = viewportHeight - triggerRect.bottom;
    const spaceAbove = triggerRect.top;

    // Open above if insufficient room below and more space above
    const shouldOpenAbove = spaceBelow < menuHeight + offset + padding && spaceAbove > spaceBelow;

    let top = shouldOpenAbove
      ? triggerRect.top - menuHeight - offset
      : triggerRect.bottom + offset;

    // Clamp top to viewport
    if (top < padding) top = padding;
    if (top + menuHeight > viewportHeight - padding) {
      top = Math.max(padding, viewportHeight - menuHeight - padding);
    }

    // Horizontal positioning: align right for card variant, left for others
    let left = variant === 'card'
      ? triggerRect.right - menuWidth
      : triggerRect.left;

    // Clamp horizontally to stay inside viewport
    if (left + menuWidth > viewportWidth - padding) {
      left = viewportWidth - menuWidth - padding;
    }
    if (left < padding) {
      left = padding;
    }

    setMenuCoords({
      top: Math.round(top),
      left: Math.round(left),
      placement: shouldOpenAbove ? 'top' : 'bottom',
    });
  }, [variant, currentStatus]);

  // Calculate position for the portaled nudge prompt
  const updateNudgePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const triggerRect = triggerRef.current.getBoundingClientRect();
    const nudgeEl = nudgeRef.current;

    const isCompact = variant === 'card' || variant === 'inline';
    const nudgeWidth = nudgeEl ? nudgeEl.offsetWidth : (isCompact ? 208 : 256);
    const nudgeHeight = nudgeEl ? nudgeEl.offsetHeight : 80;

    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const padding = 8;
    const offset = 6;

    const spaceBelow = viewportHeight - triggerRect.bottom;
    const spaceAbove = triggerRect.top;

    const shouldOpenAbove = spaceBelow < nudgeHeight + offset + padding && spaceAbove > spaceBelow;

    let top = shouldOpenAbove
      ? triggerRect.top - nudgeHeight - offset
      : triggerRect.bottom + offset;

    if (top < padding) top = padding;
    if (top + nudgeHeight > viewportHeight - padding) {
      top = Math.max(padding, viewportHeight - nudgeHeight - padding);
    }

    let left = variant === 'card'
      ? triggerRect.right - nudgeWidth
      : triggerRect.left;

    if (left + nudgeWidth > viewportWidth - padding) {
      left = viewportWidth - nudgeWidth - padding;
    }
    if (left < padding) {
      left = padding;
    }

    setNudgeCoords({
      top: Math.round(top),
      left: Math.round(left),
      placement: shouldOpenAbove ? 'top' : 'bottom',
    });
  }, [variant]);

  // Synchronous initial placement to avoid flash
  useLayoutEffect(() => {
    if (isOpen) {
      updateMenuPosition();
    }
  }, [isOpen, updateMenuPosition]);

  useLayoutEffect(() => {
    if (showNudge) {
      updateNudgePosition();
    }
  }, [showNudge, updateNudgePosition]);

  // Reposition on scroll, resize, and handle outside click / Escape for Menu
  useEffect(() => {
    if (!isOpen) return;

    // Update with true measured dimensions after render
    const frameId = requestAnimationFrame(updateMenuPosition);

    const handleScrollOrResize = () => {
      updateMenuPosition();
    };

    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as Node;
      const insideTrigger = triggerRef.current?.contains(target);
      const insideMenu = menuRef.current?.contains(target);

      if (!insideTrigger && !insideMenu) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener('mousedown', handleOutsideClick, true);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', handleScrollOrResize, { passive: true, capture: true });
    window.addEventListener('resize', handleScrollOrResize);

    return () => {
      cancelAnimationFrame(frameId);
      document.removeEventListener('mousedown', handleOutsideClick, true);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', handleScrollOrResize, { capture: true });
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [isOpen, updateMenuPosition]);

  // Reposition & outside click for Nudge
  useEffect(() => {
    if (!showNudge) return;

    const frameId = requestAnimationFrame(updateNudgePosition);

    const handleScrollOrResize = () => {
      updateNudgePosition();
    };

    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as Node;
      const insideTrigger = triggerRef.current?.contains(target);
      const insideNudge = nudgeRef.current?.contains(target);

      if (!insideTrigger && !insideNudge) {
        setShowNudge(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick, true);
    window.addEventListener('scroll', handleScrollOrResize, { passive: true, capture: true });
    window.addEventListener('resize', handleScrollOrResize);

    return () => {
      cancelAnimationFrame(frameId);
      document.removeEventListener('mousedown', handleOutsideClick, true);
      window.removeEventListener('scroll', handleScrollOrResize, { capture: true });
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [showNudge, updateNudgePosition]);

  const handleSelectStatus = (status: WatchStatus | null) => {
    setIsOpen(false);
    triggerRef.current?.focus();
    setWatchStatus(movie, status);

    // If marked watched, unrated, and nudge not dismissed, prompt inline
    if (status === 'watched' && mid && !isRated && !isNudgeDismissed(mid)) {
      setShowNudge(true);
    } else {
      setShowNudge(false);
    }
  };

  const handleNudgeDismiss = () => {
    if (mid) dismissWatchedNudge(mid);
    setShowNudge(false);
    triggerRef.current?.focus();
  };

  const handleNudgeLike = () => {
    toggleLike(movie);
    setShowNudge(false);
    triggerRef.current?.focus();
  };

  const handleNudgeDislike = () => {
    toggleDislike(movie);
    setShowNudge(false);
    triggerRef.current?.focus();
  };

  // Keyboard navigation on trigger button
  const handleTriggerKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        setTimeout(() => {
          if (!menuRef.current) return;
          const items = Array.from(
            menuRef.current.querySelectorAll<HTMLButtonElement>('button[role="menuitem"]')
          );
          if (items.length > 0) {
            const selectedItem = items.find((el) => el.getAttribute('aria-checked') === 'true');
            (selectedItem || items[0]).focus();
          }
        }, 30);
      }
    }
  };

  // Keyboard navigation inside portaled menu (ArrowDown, ArrowUp, Home, End, Escape, Tab)
  const handleMenuKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
      return;
    }
    if (e.key === 'Tab') {
      setIsOpen(false);
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!menuRef.current) return;
      const items = Array.from(
        menuRef.current.querySelectorAll<HTMLButtonElement>('button[role="menuitem"]')
      );
      if (items.length === 0) return;
      const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement);
      let nextIndex = 0;
      if (e.key === 'ArrowDown') {
        nextIndex = currentIndex >= 0 && currentIndex < items.length - 1 ? currentIndex + 1 : 0;
      } else if (e.key === 'ArrowUp') {
        nextIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
      }
      items[nextIndex]?.focus();
    } else if (e.key === 'Home') {
      e.preventDefault();
      const first = menuRef.current?.querySelector<HTMLButtonElement>('button[role="menuitem"]');
      first?.focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      const items = menuRef.current?.querySelectorAll<HTMLButtonElement>('button[role="menuitem"]');
      if (items && items.length > 0) {
        items[items.length - 1]?.focus();
      }
    }
  };

  const isCompact = variant === 'card' || variant === 'inline';

  // Render Portaled Dropdown Menu
  const renderPortaledMenu = () => {
    if (typeof document === 'undefined' || !isOpen) return null;

    return createPortal(
      <div
        ref={menuRef}
        id={menuId}
        role="menu"
        aria-label={`Watch status for ${title}`}
        onKeyDown={handleMenuKeyDown}
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'fixed',
          top: `${menuCoords.top}px`,
          left: `${menuCoords.left}px`,
          zIndex: 9999,
        }}
        className={`${
          isCompact ? 'w-44 text-xs p-1.5' : 'w-56 text-sm p-1.5'
        } rounded-xl bg-[#14151a]/95 backdrop-blur-xl border border-white/15 shadow-2xl animate-in fade-in zoom-in-95 duration-150 space-y-0.5 select-none`}
      >
        {(Object.keys(STATUS_CONFIG) as WatchStatus[]).map((st) => {
          const cfg = STATUS_CONFIG[st];
          const Icon = cfg.icon;
          const isSelected = currentStatus === st;
          return (
            <button
              key={st}
              type="button"
              role="menuitem"
              aria-checked={isSelected}
              onClick={() => handleSelectStatus(st)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-colors cursor-pointer focus:outline-none focus-visible:ring-1 focus-visible:ring-amber-500 ${
                isSelected
                  ? 'bg-amber-500/20 text-amber-400 font-semibold border border-amber-500/30'
                  : 'text-slate-300 hover:text-white hover:bg-white/10'
              }`}
            >
              <Icon
                className={`${isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4'} ${
                  isSelected ? 'text-amber-400' : 'text-slate-400'
                }`}
              />
              <span className="flex-1 truncate">{cfg.label}</span>
              {isSelected && <span className="text-amber-400 text-xs font-bold">✓</span>}
            </button>
          );
        })}

        {currentStatus && (
          <div className="pt-1 mt-1 border-t border-white/10">
            <button
              type="button"
              role="menuitem"
              onClick={() => handleSelectStatus(null)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer focus:outline-none focus-visible:ring-1 focus-visible:ring-amber-500 ${
                isCompact ? 'text-xs' : 'text-sm'
              }`}
            >
              <Trash2 className={isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
              <span>Remove from list</span>
            </button>
          </div>
        )}
      </div>,
      document.body
    );
  };

  // Render Portaled "Did you like it?" Nudge
  const renderPortaledNudge = () => {
    if (typeof document === 'undefined' || !showNudge) return null;

    return createPortal(
      <div
        ref={nudgeRef}
        role="dialog"
        aria-label="Rating prompt"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'fixed',
          top: `${nudgeCoords.top}px`,
          left: `${nudgeCoords.left}px`,
          zIndex: 9999,
        }}
        className={`${
          isCompact ? 'w-52 p-2.5 text-xs' : 'w-64 p-3 text-sm'
        } rounded-xl bg-[#14151a]/95 backdrop-blur-xl border border-amber-500/40 shadow-2xl animate-in fade-in duration-200 space-y-2 select-none`}
      >
        <div className="font-medium text-slate-200 text-xs sm:text-sm">
          Marked as watched! Did you like it?
        </div>
        <div className="flex items-center justify-between gap-2 pt-1 border-t border-white/10">
          <div className="flex items-center gap-1.5 sm:gap-2">
            <button
              type="button"
              onClick={handleNudgeLike}
              aria-label={`Like ${title}`}
              className="px-2.5 py-1 rounded-md bg-amber-500/15 hover:bg-amber-500/30 border border-amber-500/40 text-amber-400 flex items-center gap-1 text-xs font-medium transition-colors cursor-pointer"
            >
              <ThumbsUp className="w-3.5 h-3.5" />
              <span>Like</span>
            </button>
            <button
              type="button"
              onClick={handleNudgeDislike}
              aria-label={`Dislike ${title}`}
              className="px-2.5 py-1 rounded-md bg-white/5 hover:bg-white/15 border border-white/10 text-slate-300 flex items-center gap-1 text-xs font-medium transition-colors cursor-pointer"
            >
              <ThumbsDown className="w-3.5 h-3.5" />
              <span>Dislike</span>
            </button>
          </div>
          <button
            type="button"
            onClick={handleNudgeDismiss}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      </div>,
      document.body
    );
  };

  // 1. Render Card Variant (top-right overlay icon on movie poster)
  if (variant === 'card') {
    const ActiveIcon = currentStatus ? STATUS_CONFIG[currentStatus].icon : Bookmark;

    return (
      <div
        ref={containerRef}
        className={`relative z-20 ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          ref={triggerRef}
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsOpen((prev) => !prev);
          }}
          onKeyDown={handleTriggerKeyDown}
          aria-haspopup="menu"
          aria-expanded={isOpen}
          aria-controls={isOpen ? menuId : undefined}
          aria-label={
            currentStatus
              ? `Status: ${STATUS_CONFIG[currentStatus].label}. Click to change.`
              : `Add ${title} to list`
          }
          className={`w-7 h-7 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 shadow-md ${
            currentStatus
              ? 'bg-amber-500 text-black font-semibold'
              : 'bg-black/60 text-slate-300 hover:text-white hover:bg-black/80'
          }`}
          title={currentStatus ? STATUS_CONFIG[currentStatus].label : '+ Add to list'}
        >
          {currentStatus ? (
            <ActiveIcon className="w-3.5 h-3.5 stroke-[2.5]" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
        </button>

        {renderPortaledMenu()}
        {renderPortaledNudge()}
      </div>
    );
  }

  // 2. Render Inline Variant (used inside library cards or compact rows)
  if (variant === 'inline') {
    const ActiveIcon = currentStatus ? STATUS_CONFIG[currentStatus].icon : Bookmark;

    return (
      <div ref={containerRef} className={`relative inline-block ${className}`}>
        <button
          ref={triggerRef}
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsOpen((prev) => !prev);
          }}
          onKeyDown={handleTriggerKeyDown}
          aria-haspopup="menu"
          aria-expanded={isOpen}
          aria-controls={isOpen ? menuId : undefined}
          aria-label={
            currentStatus
              ? `Status: ${STATUS_CONFIG[currentStatus].label}. Click to change.`
              : `Add ${title} to list`
          }
          className={`px-2.5 py-1.5 rounded-md border flex items-center gap-1.5 text-xs font-medium transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
            currentStatus
              ? 'bg-amber-500/20 border-amber-500 text-amber-400'
              : 'bg-white/5 border-transparent text-slate-300 hover:text-white hover:bg-white/10'
          }`}
          title={currentStatus ? STATUS_CONFIG[currentStatus].label : '+ Add to list'}
        >
          <ActiveIcon className="w-3.5 h-3.5" />
          <span>{currentStatus ? STATUS_CONFIG[currentStatus].shortLabel : '+ List'}</span>
          <ChevronDown className="w-3 h-3 opacity-60" />
        </button>

        {renderPortaledMenu()}
        {renderPortaledNudge()}
      </div>
    );
  }

  // 3. Render Full Variant: 'detail' or 'hero'
  const ActiveIcon = currentStatus ? STATUS_CONFIG[currentStatus].icon : Bookmark;
  const isHero = variant === 'hero';

  return (
    <div ref={containerRef} className={`relative inline-block ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsOpen((prev) => !prev);
        }}
        onKeyDown={handleTriggerKeyDown}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={isOpen ? menuId : undefined}
        aria-label={
          currentStatus
            ? `Status: ${STATUS_CONFIG[currentStatus].label}. Click to change status.`
            : `Add ${title} to list`
        }
        className={`px-5 py-3 rounded-lg border font-medium text-sm sm:text-base flex items-center gap-2 transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
          currentStatus
            ? 'bg-amber-500/20 text-amber-400 border-amber-500/60 shadow-md'
            : isHero
            ? 'bg-[#1f1f24]/80 hover:bg-[#23252b] border-white/20 hover:border-amber-500/50 text-white'
            : 'bg-white/10 hover:bg-white/20 text-white border border-white/20'
        }`}
      >
        <ActiveIcon
          className={`w-4 h-4 ${currentStatus === 'plan' ? 'fill-amber-400' : ''}`}
        />
        <span>{currentStatus ? STATUS_CONFIG[currentStatus].label : '+ Add to list'}</span>
        <ChevronDown className="w-4 h-4 opacity-70 ml-0.5" />
      </button>

      {renderPortaledMenu()}
      {renderPortaledNudge()}
    </div>
  );
};
