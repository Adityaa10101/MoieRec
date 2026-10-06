import React from 'react';
import { Link } from '../router/Router';
import { Clapperboard, ArrowLeft } from 'lucide-react';

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
          <h1 className="font-serif text-2xl text-white font-bold">Sign In</h1>
          <p className="text-slate-400 text-xs">Guest mode is active — accounts are not required</p>
        </div>

        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 leading-relaxed text-center">
          Guest mode: your picks and watchlist are saved locally in your browser. Authentication is not required.
        </div>

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
