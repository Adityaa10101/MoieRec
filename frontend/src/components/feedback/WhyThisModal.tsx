import React from 'react';
import { X, Sparkles, Film, Tag, BarChart3, CheckCircle2, Users } from 'lucide-react';
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
  const weights = explanation.weights;
  const cfPick = explanation.cf_pick;

  // Actual weights used
  const w_c = weights?.w_c ?? (explanation.alpha ?? 0);
  const w_f = weights?.w_f ?? (components.cf != null ? 1 : 0);
  const w_p = weights?.w_p ?? 0;

  // Top N% pick: N = max(1, 100 - match_percent)
  const topPercent = Math.max(1, 100 - matchPercent);

  // Component values
  const cContent = components.content || 0;
  const cCf = components.cf || 0;
  const cPop = components.popularity || 0;

  // Calculate sum of active components
  let totalActiveScore = 0;
  if (w_c > 0) totalActiveScore += cContent;
  if (w_f > 0) totalActiveScore += cCf;
  if (w_p > 0) totalActiveScore += cPop;

  const contentPct = totalActiveScore > 0 && w_c > 0 ? (cContent / totalActiveScore) * 100 : 0;
  const cfPct = totalActiveScore > 0 && w_f > 0 ? (cCf / totalActiveScore) * 100 : 0;
  const popPct = totalActiveScore > 0 && w_p > 0 ? (cPop / totalActiveScore) * 100 : 0;

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
              <span>
                {w_c > 0
                  ? 'Collaborative Filtering + Content Evidence'
                  : 'Collaborative Filtering Recommendation Evidence'}
              </span>
            </div>
            <h3 className="font-serif text-2xl text-white font-bold">{movie.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
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

        {/* Collaborative Filtering Evidence Line (when w_f > 0 and cfPick exists) */}
        {w_f > 0 && cfPick && cfPick.title && (
          <div className="p-4 rounded-xl bg-[#191a22] border border-sky-500/30 space-y-2">
            <div className="text-[11px] font-mono text-sky-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-sky-400" />
              <span>Collaborative Filtering Evidence</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-semibold text-white">{cfPick.title}</div>
              <div className="text-xs font-mono text-sky-300 font-bold bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20 whitespace-nowrap">
                sim {cfPick.similarity.toFixed(3)}
              </div>
            </div>
            <div className="text-xs text-slate-300 pt-0.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
              <span>
                <strong className="text-sky-300 font-mono font-semibold">
                  {cfPick.cooccurrence.toLocaleString()}
                </strong>{' '}
                MovieLens viewers who liked{' '}
                <em className="text-white not-italic font-medium">{cfPick.title}</em> also liked this
              </span>
            </div>
          </div>
        )}

        {/* Nearest Content Pick Card (ONLY when w_c > 0) */}
        {w_c > 0 && nearestPick && nearestPick.title && (
          <div className="p-4 rounded-xl bg-[#191a22] border border-white/10 space-y-2">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Film className="w-3.5 h-3.5 text-amber-500" />
              <span>Closest Movie in Your Picks (Content Match)</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-semibold text-white">{nearestPick.title}</div>
              <div className="text-xs font-mono text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 whitespace-nowrap">
                cosine {nearestPick.similarity.toFixed(3)}
              </div>
            </div>
          </div>
        )}

        {/* Component Breakdown — lists ONLY components with weight > 0 */}
        <div className="space-y-3 p-4 rounded-xl bg-[#191a22] border border-white/10">
          <div className="flex items-center justify-between text-xs">
            <span className="font-mono text-slate-300 uppercase tracking-wider text-[11px] font-semibold flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5 text-amber-500" />
              <span>Active Model Components (Weight &gt; 0)</span>
            </span>
            <div className="flex items-center gap-2">
              {weights ? (
                <span className="text-[11px] font-mono bg-amber-500/15 border border-amber-500/30 text-amber-300 px-2 py-0.5 rounded font-bold">
                  w = [{weights.w_c.toFixed(1)}, {weights.w_f.toFixed(1)}, {weights.w_p.toFixed(1)}]
                </span>
              ) : null}
              <span className="text-[11px] font-mono text-slate-400">
                Score: {totalActiveScore.toFixed(3)}
              </span>
            </div>
          </div>

          {/* Visual Bar — shows active components only */}
          <div className="w-full h-3 rounded-full bg-white/5 overflow-hidden flex">
            {w_f > 0 && cfPct > 0 && (
              <div
                className="h-full bg-sky-500 transition-all duration-500"
                style={{ width: `${cfPct}%` }}
                title={`Collaborative Filtering: ${cCf.toFixed(3)}`}
              />
            )}
            {w_c > 0 && contentPct > 0 && (
              <div
                className="h-full bg-amber-500 transition-all duration-500"
                style={{ width: `${contentPct}%` }}
                title={`Content Match: ${cContent.toFixed(3)}`}
              />
            )}
            {w_p > 0 && popPct > 0 && (
              <div
                className="h-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${popPct}%` }}
                title={`Popularity: ${cPop.toFixed(3)}`}
              />
            )}
          </div>

          {/* Component metric tiles for weights > 0 */}
          <div className="flex flex-wrap gap-4 text-xs pt-1">
            {w_f > 0 && (
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5 text-sky-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-sky-500" />
                  <span>Collaborative Filtering (w = {w_f.toFixed(1)})</span>
                </div>
                <div className="font-mono text-xs text-white font-bold pl-3.5">
                  {cCf.toFixed(3)}{' '}
                  <span className="text-slate-500 font-normal text-[10px]">
                    ({cfPct.toFixed(0)}%)
                  </span>
                </div>
              </div>
            )}

            {w_c > 0 && (
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5 text-amber-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>Content Similarity (w = {w_c.toFixed(1)})</span>
                </div>
                <div className="font-mono text-xs text-white font-bold pl-3.5">
                  {cContent.toFixed(3)}{' '}
                  <span className="text-slate-500 font-normal text-[10px]">
                    ({contentPct.toFixed(0)}%)
                  </span>
                </div>
              </div>
            )}

            {w_p > 0 && (
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5 text-indigo-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-indigo-500" />
                  <span>Popularity (w = {w_p.toFixed(1)})</span>
                </div>
                <div className="font-mono text-xs text-white font-bold pl-3.5">
                  {cPop.toFixed(3)}{' '}
                  <span className="text-slate-500 font-normal text-[10px]">
                    ({popPct.toFixed(0)}%)
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Top Shared Feature Contributions (ONLY when w_c > 0) */}
        {w_c > 0 && sharedFeatures.length > 0 && (
          <div className="space-y-2.5 p-4 rounded-xl bg-[#191a22] border border-white/10">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-amber-500" />
              <span>Top Contributing Content Features</span>
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

        {/* Reason Codes & Honest Labels */}
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
                  } else if (code === 'CO_LIKED_BY_USERS') {
                    label = cfPick?.title
                      ? `${cfPick.cooccurrence.toLocaleString()} MovieLens viewers who liked ${cfPick.title} also liked this`
                      : 'Co-liked by MovieLens viewers';
                  } else if (code === 'SHARED_GENRES') {
                    const g = sharedFeatures.filter((f) => f.feature_type === 'genre').map((f) => f.feature);
                    label = g.length > 0 ? `Shared genres: ${g.join(', ')}` : 'Shared genres';
                  } else if (code === 'SHARED_TAGS') {
                    const t = sharedFeatures.filter((f) => f.feature_type === 'tag' || f.feature_type === 'genome_tag').map((f) => f.feature);
                    label = t.length > 0 ? `Shared tags: ${t.join(', ')}` : 'Shared tags';
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
          className="w-full py-2.5 rounded-lg bg-[#23252b] hover:bg-[#2b2d35] border border-white/10 text-white font-medium text-xs transition-colors cursor-pointer"
        >
          Close Breakdown
        </button>
      </div>
    </div>
  );
};
