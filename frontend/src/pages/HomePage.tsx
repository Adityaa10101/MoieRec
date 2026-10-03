import React from 'react';
import { motion } from 'framer-motion';
import { Layers, Server, BrainCircuit, Database, CheckCircle } from 'lucide-react';
import { ApiHealthCard } from '../components/status/ApiHealthCard';
import { Badge } from '../components/common/Badge';
import { PROJECT_METADATA } from '../data/placeholder';

export const HomePage: React.FC = () => {
  const modules = [
    {
      icon: Layers,
      title: 'Frontend Client',
      stack: 'React 19 · Vite · TypeScript · Tailwind CSS · Framer Motion',
      status: 'Ready',
      detail: 'Modular structure with separation of UI, services, and hooks.',
    },
    {
      icon: Server,
      title: 'Backend API',
      stack: 'FastAPI · Pydantic · Uvicorn · CORS Middleware',
      status: 'Ready',
      detail: 'Decoupled API routers with environment configuration and health checks.',
    },
    {
      icon: BrainCircuit,
      title: 'ML Recommender Package',
      stack: 'Python · Scikit-Learn · Matrix Factorization · Hybrid Ranker',
      status: 'Structured',
      detail: 'Decoupled content-based, collaborative, and hybrid explanation modules.',
    },
    {
      icon: Database,
      title: 'Data Architecture',
      stack: 'MovieLens 100k/1M · TMDB API · MongoDB Driver',
      status: 'Partitioned',
      detail: 'Separated raw, processed, and external dataset directories.',
    },
  ];

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Hero Banner */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center space-y-3 pt-4"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          Foundation Architecture Online
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
          {PROJECT_METADATA.name}
        </h1>
        <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto">
          {PROJECT_METADATA.tagline}. Full-stack ML architecture ready for incremental feature integration.
        </p>
      </motion.div>

      {/* Backend Health Check Card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <ApiHealthCard />
      </motion.div>

      {/* Architecture Modules Grid */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="space-y-4"
      >
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Architecture Modules
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {modules.map((mod) => {
            const Icon = mod.icon;
            return (
              <div
                key={mod.title}
                className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/40 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-800 text-amber-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="font-medium text-white text-sm">{mod.title}</span>
                  </div>
                  <Badge label={mod.status} variant="amber" />
                </div>
                <p className="text-xs text-slate-300 font-mono mb-2">{mod.stack}</p>
                <p className="text-xs text-slate-500">{mod.detail}</p>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Verification Summary */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="p-4 rounded-xl border border-emerald-900/30 bg-emerald-950/20 text-xs text-emerald-300 flex items-center gap-3"
      >
        <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
        <span>
          Phase 1 Foundation complete: React & Vite running with TypeScript, Tailwind CSS, clean separation of concerns, and verified FastAPI health endpoint connectivity.
        </span>
      </motion.div>
    </div>
  );
};
