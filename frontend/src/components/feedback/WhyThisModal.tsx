import React from 'react';
import { X, Sparkles, Film, Tag, BarChart3, CheckCircle2 } from 'lucide-react';
import type { Movie } from '../../types/movie';
import type { SharedFeatureExplanation } from '../../api/types';

interface WhyThisModalProps {
  isOpen: boolean;
  onClose: () => void;
  movie: Movie;
}

export const WhyThisModal: React.FC<WhyThisModalProps> = ({ isOpen, onClose, movie }) => {
  if (!isOpen) return null;

  const explanation = movie.explanation;
  if (!explanation) return null;

  const nearestPick = explanation.nearest_pick;
  const sharedFeatures = explanation.top_shared_features || [];
  const components = explanation.components || { content: 0, popularity: 0 };
  const matchPercent = explanation.match_percent ?? 50;
  const alphaUsed = explanation.alpha ?? 0.5;

  // Top N% pick: N = max(1, 100 - match_percent)
  const topPercent = Math.max(1, 100 - matchPercent);

  // Component percentages relative to their sum for the bar visualization
  const totalComponents = components.content + components.popularity;
  const contentPct = totalComponents > 0 ? (components.content / totalComponents) * 100 : 50;
  const popPct = totalComponents > 0 ? (components.popularity / totalComponents) * 100 : 50;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl bg-[#14151a] border border-amber-500/30 shadow-2xl p-6 sm:p-7 space-y-6 overflow-hidden max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-amber-500 font-bold">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Hybrid Recommendation Evidence</span>
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

        {/* Top N% Rank Anchor */}
        <div className="flex items-center gap-3.5 p-3.5 rounded-xl bg-[#1d1f27] border border-white/10">
          <div className="px-3 py-1.5 rounded-lg bg-amber-500 text-black font-mono font-bold text-sm tracking-tight whitespace-nowrap">
            Top {topPercent}% pick
          </div>
          <div className="text-xs text-slate-300 font-medium">
            Top {topPercent}% pick for your profile{' '}
            <span className="text-slate-400 block text-[11px] mt-0.5">
              Relative rank among candidates for your picks, not a probability.
            </span>
          </div>
        </div>

        {/* Nearest Pick Card */}
        {nearestPick && nearestPick.title && (
          <div className="p-4 rounded-xl bg-[#191a22] border border-white/10 space-y-2">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Film className="w-3.5 h-3.5 text-amber-500" />
              <span>Closest Movie in Your Picks</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-semibold text-white">{nearestPick.title}</div>
              <div className="text-xs font-mono text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 whitespace-nowrap">
                cosine {nearestPick.similarity.toFixed(3)}
              </div>
            </div>
          </div>
        )}

        {/* Real Content vs Popularity Component Breakdown + Alpha Used */}
        <div className="space-y-3 p-4 rounded-xl bg-[#191a22] border border-white/10">
          <div className="flex items-center justify-between text-xs">
            <span className="font-mono text-slate-300 uppercase tracking-wider text-[11px] font-semibold flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5 text-amber-500" />
              <span>Scoring Blend Components</span>
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono bg-amber-500/15 border border-amber-500/30 text-amber-300 px-2 py-0.5 rounded font-bold">
                α = {alphaUsed.toFixed(2)}
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Total: {(components.content + components.popularity).toFixed(3)}
              </span>
            </div>
          </div>

          {/* Visual Bar */}
          <div className="w-full h-3 rounded-full bg-white/5 overflow-hidden flex">
            <div
              className="h-full bg-amber-500 transition-all duration-500"
              style={{ width: `${contentPct}%` }}
              title={`Content Component: ${components.content.toFixed(3)} (α=${alphaUsed.toFixed(2)})`}
            />
            <div
              className="h-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${popPct}%` }}
              title={`Popularity Component: ${components.popularity.toFixed(3)} (1-α=${(1 - alphaUsed).toFixed(2)})`}
            />
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5 text-amber-400 font-medium">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>Content Component</span>
              </div>
              <div className="font-mono text-xs text-white font-bold pl-3.5">
                {components.content.toFixed(3)}{' '}
                <span className="text-slate-500 font-normal text-[10px]">({contentPct.toFixed(0)}%)</span>
              </div>
            </div>

            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5 text-indigo-400 font-medium">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                <span>Popularity Component</span>
              </div>
              <div className="font-mono text-xs text-white font-bold pl-3.5">
                {components.popularity.toFixed(3)}{' '}
                <span className="text-slate-500 font-normal text-[10px]">({popPct.toFixed(0)}%)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Top Shared Feature Contributions */}
        {sharedFeatures.length > 0 && (
          <div className="space-y-2.5 p-4 rounded-xl bg-[#191a22] border border-white/10">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-amber-500" />
              <span>Top Positively Contributing Features</span>
            </div>
            <div className="space-y-2">
              {sharedFeatures.map((feat: SharedFeatureExplanation, idx: number) => (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <span className="text-slate-300 font-medium capitalize">
                    <span className="text-slate-500 text-[10px] mr-1.5 font-mono uppercase">
                      [{feat.feature_type}]
                    </span>
                    {feat.feature}
                  </span>
                  <span className="font-mono text-emerald-400 font-semibold">
                    +{feat.contribution.toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Reason Codes & Honest Labels (C1) */}
        {movie.reason_codes && movie.reason_codes.length > 0 && (
          <div className="space-y-2 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <div className="text-[11px] font-mono text-amber-400 uppercase tracking-wider font-semibold">
              Verified Recommendation Reasons
            </div>
            <div className="flex flex-wrap gap-1.5">
              {movie.reason_codes.map((code: string) => {
                let label = explanation.reason_labels?.[code];
                if (!label) {
                  if (code === 'SIMILAR_TO_PICK') {
                    label = nearestPick?.title ? `Similar to ${nearestPick.title}` : 'Similar to your pick';
                  } else if (code === 'SHARED_GENRES') {
                    const genres = sharedFeatures.filter((f) => f.feature_type === 'genre').map((f) => f.feature);
                    label = genres.length > 0 ? `Shared genres: ${genres.join(', ')}` : 'Shared genres';
                  } else if (code === 'SHARED_TAGS') {
                    const tags = sharedFeatures
                      .filter((f) => f.feature_type === 'tag' || f.feature_type === 'genome_tag')
                      .map((f) => f.feature);
                    label = tags.length > 0 ? `Shared tags: ${tags.join(', ')}` : 'Shared tags';
                  } else if (code === 'POPULAR_WITH_VIEWERS') {
                    label = 'Popular with MovieLens viewers';
                  } else {
                    label = code;
                  }
                }

                return (
                  <span
                    key={code}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-500/15 text-amber-300 text-[11px] font-medium border border-amber-500/30"
                  >
                    <CheckCircle2 className="w-3 h-3 text-amber-400" />
                    {label}
                  </span>
                );
              })}
            </div>
          </div>
        )}

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
