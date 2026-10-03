import React from 'react';
import { Link } from '../router/Router';
import { Compass, ArrowLeft, Sliders } from 'lucide-react';

export const ExplorePage: React.FC = () => {
  return (
    <div className="min-h-screen pt-28 pb-20 max-w-5xl mx-auto px-6 space-y-8">
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-amber-400 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Return to Curated Feed</span>
      </Link>

      <div className="p-8 sm:p-12 rounded-2xl bg-[#1a1b20] border border-white/10 text-center space-y-6">
        <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-500">
          <Compass className="w-7 h-7" />
        </div>
        <div className="space-y-2">
          <span className="text-xs uppercase tracking-widest text-amber-400 font-mono">
            Curatorial Exploration Matrix
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl text-white font-bold">
            Explore Atmospheric Masterpieces
          </h1>
          <p className="text-slate-400 text-sm max-w-lg mx-auto leading-relaxed">
            Multi-vector exploration across eras, directorial styles, cinematography palettes, and runtime constraints.
          </p>
        </div>

        <div className="inline-flex items-center gap-3 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-slate-400">
          <Sliders className="w-4 h-4 text-amber-400" />
          <span>Multi-dimensional sliders and interactive cluster maps scheduled for subsequent phases.</span>
        </div>

        <div className="pt-4">
          <Link
            to="/"
            className="px-6 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-[#0d0e12] font-semibold text-sm transition-all"
          >
            Explore Home Recommendations
          </Link>
        </div>
      </div>
    </div>
  );
};
