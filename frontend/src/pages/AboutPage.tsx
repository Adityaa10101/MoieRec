import React from 'react';
import { Link } from '../router/Router';
import {
  BarChart2,
  AlertTriangle,
  ArrowLeft,
  Database,
  Cpu,
} from 'lucide-react';

export const AboutPage: React.FC = () => {
  return (
    <div className="min-h-screen pt-28 pb-24 max-w-4xl mx-auto px-6 space-y-10">
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-amber-400 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Return to Home</span>
      </Link>

      {/* Header */}
      <div className="space-y-3 border-b border-white/10 pb-8">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
            System Architecture
          </span>
          <span className="text-xs text-slate-400">
            Full transparency &amp; verified evaluation numbers
          </span>
        </div>
        <h1 className="font-serif text-3xl sm:text-5xl text-white font-bold tracking-tight">
          How It Works
        </h1>
        <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
          An honest, production-calibrated recommendation system trained on MovieLens 25M and powered by item-based collaborative filtering scored from onboarding picks.
        </p>
      </div>

      {/* Pipeline Description */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-[#14151a] border border-white/10 space-y-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Database className="w-5 h-5" />
          </div>
          <h3 className="font-serif text-lg font-bold text-white">MovieLens 25M &amp; TMDB Catalog</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            The core catalog comprises 18,259 canonical titles with verified TMDB metadata, posters, and cast backdrops. Interaction signals originate from the 25-million rating MovieLens dataset.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-[#14151a] border border-white/10 space-y-3">
          <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
            <Cpu className="w-5 h-5" />
          </div>
          <h3 className="font-serif text-lg font-bold text-white">Item-kNN Collaborative Filtering</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Recommendations are scored directly from user onboarding picks using a high-precision item-item cosine similarity matrix ($k=200$, $\alpha=0.5$). For $K \le 14$ onboarding picks, pure collaborative filtering is served; at $K \ge 15$, a 90% CF / 10% content blend is utilized.
          </p>
        </div>
      </div>

      {/* Verified Results Box */}
      <div className="p-7 sm:p-8 rounded-2xl bg-[#14151a] border border-amber-500/30 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-amber-500" />
            <h2 className="font-serif text-xl sm:text-2xl font-bold text-white">
              Offline Benchmark Results
            </h2>
          </div>
          <span className="text-[11px] font-mono text-amber-400 font-semibold bg-amber-500/10 px-2.5 py-1 rounded border border-amber-500/20 self-start sm:self-auto">
            Bit-identical metrics
          </span>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          The numbers below are exact evaluations extracted directly from the frozen results files:
        </p>

        <div className="space-y-6">
          {/* Warm Test Table */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-white font-semibold">
                1. Warm Test Protocol (<code className="text-amber-400 font-normal">recommender/results/final/final_test_warm.json</code>)
              </span>
              <span className="text-slate-400">Metric: NDCG@10</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-white/10 rounded-xl overflow-hidden">
                <thead className="bg-[#1f2028] text-slate-300 font-mono">
                  <tr>
                    <th className="p-3">Model</th>
                    <th className="p-3">NDCG@10</th>
                    <th className="p-3">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono text-slate-300">
                  <tr className="hover:bg-white/5">
                    <td className="p-3 font-semibold text-white">Popularity (Most Liked)</td>
                    <td className="p-3 text-amber-400 font-bold">0.0523 (0.052278)</td>
                    <td className="p-3 text-slate-400 text-[11px] font-sans">Model 0 frequency baseline</td>
                  </tr>
                  <tr className="hover:bg-white/5">
                    <td className="p-3 font-semibold text-white">Content Tier 2 (Snapshot)</td>
                    <td className="p-3 text-amber-400 font-bold">0.0673 (0.067308)</td>
                    <td className="p-3 text-slate-400 text-[11px] font-sans">Genres, tags &amp; genome profile cosine</td>
                  </tr>
                  <tr className="hover:bg-white/5">
                    <td className="p-3 font-semibold text-white">Item-kNN Collaborative Filtering</td>
                    <td className="p-3 text-emerald-400 font-bold">0.0818 (0.081848)</td>
                    <td className="p-3 text-slate-400 text-[11px] font-sans">Item co-occurrence nearest neighbors</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Cold Final Table */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-white font-semibold">
                2. Cold-Start Final Protocol — Long-Tail K=5 (<code className="text-amber-400 font-normal">recommender/results/final/final_cold_final.json</code>)
              </span>
              <span className="text-slate-400">Metric: NDCG@10</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-white/10 rounded-xl overflow-hidden">
                <thead className="bg-[#1f2028] text-slate-300 font-mono">
                  <tr>
                    <th className="p-3">Model</th>
                    <th className="p-3">NDCG@10</th>
                    <th className="p-3">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono text-slate-300">
                  <tr className="hover:bg-white/5">
                    <td className="p-3 font-semibold text-white">Popularity (Most Liked)</td>
                    <td className="p-3 text-amber-400 font-bold">0.0402 (0.040214)</td>
                    <td className="p-3 text-slate-400 text-[11px] font-sans">Non-personalized fallback baseline</td>
                  </tr>
                  <tr className="hover:bg-white/5">
                    <td className="p-3 font-semibold text-white">Collaborative Filtering (Served Model)</td>
                    <td className="p-3 text-emerald-400 font-bold">0.1051 (0.105068)</td>
                    <td className="p-3 text-slate-400 text-[11px] font-sans">+161% relative lift over popularity on long-tail items</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Limitations */}
      <div className="p-7 sm:p-8 rounded-2xl bg-[#14151a] border border-white/10 space-y-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h2 className="font-serif text-xl sm:text-2xl font-bold text-white">
            Protocol Limitations &amp; Disclaimers
          </h2>
        </div>

        <ul className="space-y-3 text-xs sm:text-sm text-slate-300 leading-relaxed list-disc list-inside">
          <li>
            <strong className="text-white">2019 dataset cutoff:</strong> Ratings and catalog metadata terminate in November 2019. Modern releases after this date are not included in the collaborative filtering index.
          </li>
          <li>
            <strong className="text-white">Tag features leak in evaluation:</strong> User tags and tag genome scores represent whole-catalog aggregations up to November 2019. Because they encapsulate future post-release history, content-based Tier 2 features leak semantic signal across chronological splits.
          </li>
          <li>
            <strong className="text-white">Onboarding protocol approximation:</strong> Evaluation approximates true interactive cold-start onboarding by taking a user's first $K$ positive ratings chronologically, which serves as a realistic offline proxy for user picks.
          </li>
          <li>
            <strong className="text-white">Neighborhood CF architecture:</strong> The serving engine implements sparse item-kNN co-occurrence filtering. While fast and transparent, it does not learn continuous latent factors or temporal interaction dynamics.
          </li>
        </ul>
      </div>

      {/* Attribution */}
      <div className="p-6 rounded-2xl bg-[#14151a] border border-white/10 space-y-3 text-xs text-slate-400 leading-relaxed">
        <h3 className="font-serif text-base font-bold text-white">Attribution &amp; Datasets</h3>
        <p>
          Movie metadata and poster artwork courtesy of{' '}
          <a
            href="https://www.themoviedb.org"
            target="_blank"
            rel="noopener noreferrer"
            className="text-amber-400 hover:underline"
          >
            The Movie Database (TMDB)
          </a>
          . This product uses the TMDB API but is not endorsed or certified by TMDB.
        </p>
        <p>
          Rating interactions and movie tag genome provided by{' '}
          <a
            href="https://grouplens.org/datasets/movielens/25m/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-amber-400 hover:underline"
          >
            GroupLens Research / MovieLens 25M
          </a>
          .
        </p>
      </div>
    </div>
  );
};
