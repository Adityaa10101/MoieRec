import React from 'react';
import { Link } from '../router/Router';
import { Clapperboard, ArrowLeft, Lock, Mail } from 'lucide-react';

export const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen pt-28 pb-20 flex items-center justify-center px-6">
      <div className="w-full max-w-md p-8 rounded-2xl bg-[#1a1b20] border border-white/10 shadow-2xl space-y-6">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-amber-400 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Home</span>
        </Link>

        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-500">
            <Clapperboard className="w-6 h-6" />
          </div>
          <h1 className="font-serif text-2xl text-white font-bold">Curator Access</h1>
          <p className="text-slate-400 text-xs">Sign in to sync your personalized taste vector across devices</p>
        </div>

        <form onSubmit={(e) => e.preventDefault()} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-mono text-slate-400 block uppercase tracking-wider">Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                disabled
                placeholder="curator@moierec.cinema"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#121317] border border-white/10 text-slate-400 text-sm cursor-not-allowed"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-mono text-slate-400 block uppercase tracking-wider">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                disabled
                placeholder="••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#121317] border border-white/10 text-slate-400 text-sm cursor-not-allowed"
              />
            </div>
          </div>

          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400">
            Authentication backend integration scheduled for future phase.
          </div>

          <button
            type="button"
            disabled
            className="w-full py-3 rounded-lg bg-amber-500/50 text-[#0d0e12] font-semibold text-sm cursor-not-allowed"
          >
            Sign In to Screening Room
          </button>
        </form>

        <div className="text-center text-xs text-slate-400">
          Need an account?{' '}
          <Link to="/register" className="text-amber-400 hover:underline">
            Register here
          </Link>
        </div>
      </div>
    </div>
  );
};
