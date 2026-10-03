import React from 'react';
import { Film, Sparkles } from 'lucide-react';
import { APP_NAME } from '../../utils/constants';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-slate-800 bg-slate-950/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-amber-600 to-amber-400 flex items-center justify-center text-slate-950 shadow-lg shadow-amber-500/20">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
              {APP_NAME}
              <span className="text-amber-400 text-xs px-2 py-0.5 rounded bg-amber-400/10 border border-amber-400/20 font-mono">
                Phase 1
              </span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span>Foundation Ready</span>
        </div>
      </div>
    </header>
  );
};
