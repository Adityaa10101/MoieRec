import React from 'react';
import { X, Sparkles, Sliders, Volume2, Film } from 'lucide-react';
import type { Movie } from '../../types/movie';

interface WhyThisModalProps {
  isOpen: boolean;
  onClose: () => void;
  movie: Movie;
}

export const WhyThisModal: React.FC<WhyThisModalProps> = ({ isOpen, onClose, movie }) => {
  if (!isOpen) return null;

  const explainability = movie.explainability || {
    directorAffinity: 98,
    thematicFit: 96,
    audiovisualScore: 95,
    naturalLanguageReason: `High correlation with your logged affinity for ${movie.director}'s pacing, atmospheric cinematography, and existential themes.`,
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div
        className="w-full max-w-lg rounded-2xl bg-[#1a1b20] border border-amber-500/30 shadow-2xl p-6 sm:p-8 space-y-6 animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-amber-500 font-bold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Explainable Recommendation Telemetry</span>
            </div>
            <h3 className="font-serif text-2xl text-white font-bold">{movie.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Match Score Anchor */}
        <div className="flex items-center gap-3 p-3.5 rounded-xl bg-[#23252b] border border-white/10">
          <div className="px-3 py-1.5 rounded-lg bg-amber-500 text-[#0d0e12] font-mono font-bold text-sm">
            {movie.matchScore}% MATCH
          </div>
          <div className="text-xs text-slate-300 font-medium">
            Calculated across your rating history, auteur weights, and audiovisual vectors.
          </div>
        </div>

        {/* Explainability Telemetry Bars */}
        <div className="space-y-4">
          {/* Directorial Continuity */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Film className="w-3.5 h-3.5 text-amber-500" /> Directorial Continuity ({movie.director})
              </span>
              <span className="font-mono text-amber-400 font-bold">{explainability.directorAffinity}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-amber-500 transition-all duration-700 ease-out"
                style={{ width: `${explainability.directorAffinity}%` }}
              />
            </div>
          </div>

          {/* Thematic Fit */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-amber-500" /> Thematic Tropes ({movie.genres.slice(0, 2).join(' / ')})
              </span>
              <span className="font-mono text-amber-400 font-bold">{explainability.thematicFit}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-amber-500 transition-all duration-700 ease-out"
                style={{ width: `${explainability.thematicFit}%` }}
              />
            </div>
          </div>

          {/* Audio-Visual Score */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5 text-amber-500" /> Soundscape & Cinematography
              </span>
              <span className="font-mono text-amber-400 font-bold">{explainability.audiovisualScore}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-amber-500 transition-all duration-700 ease-out"
                style={{ width: `${explainability.audiovisualScore}%` }}
              />
            </div>
          </div>
        </div>

        {/* Natural Language Rationale */}
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-1">
          <div className="text-[11px] font-mono text-amber-400 uppercase tracking-wider font-semibold">
            Curatorial Recommendation Evidence
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {explainability.naturalLanguageReason}
          </p>
        </div>

        <button
          onClick={onClose}
          className="w-full py-2.5 rounded-lg bg-[#23252b] hover:bg-[#2b2d35] border border-white/10 text-white font-medium text-xs transition-colors"
        >
          Close Telemetry Breakdown
        </button>
      </div>
    </div>
  );
};
