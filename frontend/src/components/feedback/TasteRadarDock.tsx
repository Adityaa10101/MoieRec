import React from 'react';
import { Bookmark } from 'lucide-react';
import { Link } from '../../router/Router';
import { useUserTaste } from '../../context/UserTasteContext';

export const TasteRadarDock: React.FC = () => {
  const { validWatchlistIds, validLikedIds } = useUserTaste();

  const watchlistCount = validWatchlistIds.length;
  const likedCount = validLikedIds.length;

  return (
    <aside className="fixed bottom-6 left-8 z-40 hidden xl:flex items-center">
      <Link
        to="/library"
        className="flex items-center gap-4 bg-[#1a1b20]/90 hover:bg-[#202128]/95 backdrop-blur-xl border border-white/10 hover:border-amber-500/40 p-3.5 rounded-2xl shadow-2xl transition-all duration-200 group cursor-pointer"
        title="Open your library"
      >
        <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-500 group-hover:scale-105 transition-transform shrink-0">
          <Bookmark className="w-5 h-5" />
        </div>
        <div className="space-y-0.5 pr-2 text-left">
          <div className="font-mono text-[10px] text-amber-400 tracking-widest uppercase font-semibold">
            My Library
          </div>
          <div className="font-serif text-sm font-semibold text-white">
            {watchlistCount} saved · {likedCount} liked
          </div>
          <div className="font-sans text-[11px] text-slate-400 group-hover:text-slate-300 transition-colors">
            Open your library
          </div>
        </div>
      </Link>
    </aside>
  );
};
