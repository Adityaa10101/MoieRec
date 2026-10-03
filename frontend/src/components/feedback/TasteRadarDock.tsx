import React from 'react';
import { Activity } from 'lucide-react';

interface TasteRadarDockProps {
  onInspect: () => void;
}

export const TasteRadarDock: React.FC<TasteRadarDockProps> = ({ onInspect }) => {
  return (
    <aside className="fixed bottom-6 left-8 z-40 hidden xl:flex items-center gap-4 bg-[#1a1b20]/90 backdrop-blur-xl border border-white/10 p-3.5 rounded-2xl shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-500 shrink-0">
        <Activity className="w-5 h-5" />
      </div>
      <div className="space-y-0.5 pr-2">
        <div className="font-mono text-[10px] text-amber-400 tracking-widest uppercase font-semibold">
          Taste Vector Active
        </div>
        <div className="font-serif text-sm font-semibold text-white">Cosmic Existentialism</div>
        <div className="font-sans text-[11px] text-slate-400">
          Matched against 8,420 curated film nodes
        </div>
      </div>
      <button
        onClick={onInspect}
        className="px-3 py-1.5 rounded-lg bg-[#23252b] hover:bg-[#2b2d35] border border-white/10 hover:border-amber-500/40 text-[11px] font-mono text-slate-200 hover:text-white transition-colors cursor-pointer"
      >
        Inspect Weights
      </button>
    </aside>
  );
};
