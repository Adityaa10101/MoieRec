import React from 'react';
import { Link } from '../router/Router';
import { Sparkles, ArrowLeft, Radar, CheckCircle2 } from 'lucide-react';
import { useUserTaste } from '../context/UserTasteContext';
import { ALL_MOCK_MOVIES } from '../data/mockMovies';

export const MyTastePage: React.FC = () => {
  const { watchlist, liked } = useUserTaste();

  const watchlistMovies = ALL_MOCK_MOVIES.filter((m) => watchlist.has(m.id));
  const likedMovies = ALL_MOCK_MOVIES.filter((m) => liked.has(m.id));

  return (
    <div className="min-h-screen pt-28 pb-20 max-w-5xl mx-auto px-6 space-y-8">
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-amber-400 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Return to Curated Feed</span>
      </Link>

      <div className="p-8 sm:p-12 rounded-2xl bg-[#1a1b20] border border-white/10 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-amber-400 uppercase tracking-widest">
              <Radar className="w-4 h-4" />
              <span>Taste DNA Calibrator</span>
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-white font-bold">
              Your Curatorial Profile
            </h1>
          </div>
          <div className="px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-mono font-semibold self-start sm:self-auto">
            Cinephile Tier • Sci-Fi & Neo-Noir 92%
          </div>
        </div>

        {/* Live user interactions summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-xl bg-[#23252b]/60 border border-white/10 space-y-3">
            <h3 className="font-serif text-lg text-white font-semibold flex items-center justify-between">
              <span>Screening Watchlist</span>
              <span className="text-xs font-mono text-amber-400">{watchlistMovies.length} Titles</span>
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {watchlistMovies.length > 0 ? (
                watchlistMovies.map((m) => (
                  <div key={m.id} className="flex items-center justify-between text-xs text-slate-300 py-1 border-b border-white/5">
                    <span>{m.title}</span>
                    <span className="text-slate-500">{m.year}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500">Your watchlist is currently empty.</p>
              )}
            </div>
          </div>

          <div className="p-6 rounded-xl bg-[#23252b]/60 border border-white/10 space-y-3">
            <h3 className="font-serif text-lg text-white font-semibold flex items-center justify-between">
              <span>Calibrated Affinities</span>
              <span className="text-xs font-mono text-amber-400">{likedMovies.length} Liked</span>
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {likedMovies.length > 0 ? (
                likedMovies.map((m) => (
                  <div key={m.id} className="flex items-center justify-between text-xs text-slate-300 py-1 border-b border-white/5">
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-amber-400" />
                      {m.title}
                    </span>
                    <span className="text-amber-500 font-mono">{m.matchScore}%</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500">No affinities calibrated yet.</p>
              )}
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300 flex items-center gap-3">
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Interactive taste cluster reconfiguration and algorithmic vector weights scheduled for Phase 3.</span>
        </div>
      </div>
    </div>
  );
};
