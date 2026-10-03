import React from 'react';
import { Bookmark } from 'lucide-react';
import { useUserTaste } from '../../context/UserTasteContext';

/**
 * TasteRadarDock — Phase 2E.2 version
 *
 * Decision: The dock NO LONGER claims a taste vector exists.
 * It shows only the user's real local state (watchlist count, liked count)
 * which are available without any ML personalization.
 * The "Inspect Weights" / WhyThis trigger is removed entirely since there
 * is no taste vector, no explanation, and no match_percent in this phase.
 *
 * This is kept compact and honest. Once personalization ships (Phase 3+),
 * the dock can be upgraded to show real taste signals.
 */
export const TasteRadarDock: React.FC = () => {
  const { watchlist, liked } = useUserTaste();

  const watchlistCount = watchlist?.size ?? 0;
  const likedCount = liked?.size ?? 0;

  return (
    <aside className="fixed bottom-6 left-8 z-40 hidden xl:flex items-center gap-4 bg-[#1a1b20]/90 backdrop-blur-xl border border-white/10 p-3.5 rounded-2xl shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-500 shrink-0">
        <Bookmark className="w-5 h-5" />
      </div>
      <div className="space-y-0.5 pr-2">
        <div className="font-mono text-[10px] text-amber-400 tracking-widest uppercase font-semibold">
          My Library
        </div>
        <div className="font-serif text-sm font-semibold text-white">
          {watchlistCount} saved · {likedCount} liked
        </div>
        <div className="font-sans text-[11px] text-slate-400">
          Personalized recommendations coming soon
        </div>
      </div>
    </aside>
  );
};
