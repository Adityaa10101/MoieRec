import React, { useState, useEffect } from 'react';
import { Film, MousePointer2 } from 'lucide-react';
import { usePopcornCursor } from '../../context/PopcornCursorContext';
import { Link } from '../../router/Router';

const CURRENT_YEAR = 2025;

export const Footer: React.FC = () => {
  const { isCursorEnabled, toggleCursor } = usePopcornCursor();
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (totalScroll > 0) {
        const currentProgress = Math.min(Math.max(window.scrollY / totalScroll, 0), 1);
        setScrollProgress(Math.round(currentProgress * 100));
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <footer className="w-full border-t border-white/10 bg-[#0d0e12] relative z-20">
      {/* Scroll Progress Easter Egg Bar */}
      <div className="max-w-7xl mx-auto px-6 md:px-12 pt-10 pb-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-[#1a1b20] border border-white/10">
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500 shrink-0">
              <span className="text-lg">🍿</span>
              <div
                className="absolute bottom-0 left-0 right-0 bg-amber-500/20 rounded-b-lg transition-all duration-300"
                style={{ height: `${scrollProgress}%` }}
              />
            </div>
            <div>
              <div className="text-xs font-mono font-semibold text-white flex items-center gap-2">
                <span>Feed Traversal</span>
                <span className="text-amber-400 font-bold">{scrollProgress}% Complete</span>
              </div>
              <p className="text-[11px] text-slate-400">
                {scrollProgress >= 95
                  ? 'End of the popular feed. 🍿'
                  : 'Browsing most-liked films on MovieLens...'}
              </p>
            </div>
          </div>

          {/* Cinematic Popcorn Cursor Toggle */}
          <button
            onClick={toggleCursor}
            className={`px-3.5 py-1.5 rounded-lg border text-xs font-mono flex items-center gap-2 transition-all cursor-pointer ${
              isCursorEnabled
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-400 hover:bg-amber-500/25'
                : 'bg-white/5 border-white/10 text-slate-400 hover:text-white hover:bg-white/10'
            }`}
            title="Toggle custom cinema popcorn pointer"
          >
            <MousePointer2 className="w-3.5 h-3.5" />
            <span>Cinematic Cursor: {isCursorEnabled ? 'Active 🍿' : 'System Native'}</span>
          </button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row justify-between items-center py-10 px-6 md:px-12 max-w-7xl mx-auto w-full gap-6">
        {/* Brand Logo & Copyright */}
        <div className="flex flex-col gap-2 items-center md:items-start text-center md:text-left">
          <div className="flex items-center gap-2.5">
            <Link to="/" className="flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-[#23252b] border border-white/10 flex items-center justify-center text-amber-500">
                <Film className="w-3.5 h-3.5 text-amber-500" />
              </span>
              <span className="font-serif text-xl tracking-tight text-white font-semibold">
                MoieRec
              </span>
            </Link>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/15 text-amber-400 border border-amber-500/30 font-medium">
              Popularity-Based Discovery
            </span>
          </div>
          <p className="text-xs text-slate-500">
            © {CURRENT_YEAR} MoieRec. All rights reserved.
          </p>
        </div>

        {/* Footer Navigation + Attribution */}
        <div className="flex flex-col items-center md:items-end gap-3">
          <nav className="flex flex-wrap justify-center items-center gap-5 text-xs text-slate-400">
            <Link to="/library" className="hover:text-amber-400 transition-colors">
              My Library
            </Link>
            <Link to="/about" className="hover:text-amber-400 transition-colors">
              How it works
            </Link>
            <a
              href="https://movielens.org"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-amber-400 transition-colors"
            >
              MovieLens
            </a>
            <a
              href="https://www.themoviedb.org"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-amber-400 transition-colors"
            >
              TMDB
            </a>
          </nav>

          <p className="text-[11px] text-slate-500 font-mono text-center md:text-right">
            Guest mode: your picks are saved only in this browser.
          </p>

          {/* Required TMDB attribution + GroupLens/MovieLens credit */}
          <p className="text-[10px] text-slate-600 text-center md:text-right max-w-xs leading-relaxed">
            This product uses the TMDB API but is not endorsed or certified by TMDB.
            Movie metadata from{' '}
            <a
              href="https://www.themoviedb.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-500 hover:text-amber-400 transition-colors"
            >
              The Movie Database (TMDB)
            </a>
            . Ratings &amp; popularity data from{' '}
            <a
              href="https://grouplens.org/datasets/movielens/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-500 hover:text-amber-400 transition-colors"
            >
              GroupLens / MovieLens
            </a>
            .
          </p>
        </div>
      </div>
    </footer>
  );
};
