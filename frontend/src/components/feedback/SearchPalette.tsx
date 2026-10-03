import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, Film, ArrowRight } from 'lucide-react';
import { fetchSearch } from '../../api/client';
import type { ApiMovie } from '../../api/types';
import { ALL_MOCK_MOVIES } from '../../data/mockMovies';
import { useRouter } from '../../router/Router';

interface SearchPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

// Build a minimal fallback from mock data for offline use
const MOCK_SEARCH_RESULTS = ALL_MOCK_MOVIES;

export const SearchPalette: React.FC<SearchPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ApiMovie[]>([]);
  const [loading, setLoading] = useState(false);
  const [usingFallback, setUsingFallback] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { navigate } = useRouter();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setResults([]);
    }
  }, [isOpen]);

  const handleClose = useCallback(() => {
    setQuery('');
    setResults([]);
    onClose();
  }, [onClose]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          handleClose();
        } else {
          document.getElementById('navbar-search-btn')?.click();
        }
      }
      if (e.key === 'Escape' && isOpen) handleClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleClose]);

  // Debounced API search (~250ms)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (abortRef.current) abortRef.current.abort();

    if (!query.trim() || query.trim().length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      try {
        const data = await fetchSearch(query, 10, controller.signal);
        setResults(data);
        setUsingFallback(false);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        // API unreachable — fall back to mock search
        setUsingFallback(true);
        const q = query.toLowerCase();
        const fallback = MOCK_SEARCH_RESULTS.filter(
          (m) =>
            m.title.toLowerCase().includes(q) ||
            m.director.toLowerCase().includes(q)
        ).slice(0, 10);
        // Convert mock to ApiMovie shape
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setResults(fallback as any);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const handleSelectMovie = (movie: ApiMovie) => {
    handleClose();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const id = (movie as any).movie_id ?? (movie as any).id;
    navigate(`/movie/${id}`);
  };

  if (!isOpen) return null;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getMovieId = (m: any) => m.movie_id ?? m.id ?? '';
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getMoviePoster = (m: any) => m.poster_url ?? m.poster ?? null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getMovieYear = (m: any) => m.year ?? '';
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getMovieDirector = (m: any) => m.directors?.[0] ?? m.director ?? '';
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getMovieGenres = (m: any): string[] => m.genres ?? [];

  return (
    <div
      onClick={handleClose}
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/80 backdrop-blur-md"
    >
      <div
        className="w-full max-w-2xl rounded-2xl bg-[#1a1b20] border border-amber-500/30 shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-white/10 gap-3 bg-[#23252b]">
          <Search className="w-5 h-5 text-amber-500 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title..."
            className="flex-1 bg-transparent border-none text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />
          {query && (
            <button onClick={() => setQuery('')} className="text-slate-400 hover:text-white transition-colors">
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-mono bg-white/5 border border-white/10 text-slate-400">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="overflow-y-auto p-3 space-y-1.5 flex-1 divide-y divide-white/5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 px-3 py-1.5 flex items-center justify-between">
            <span>
              {usingFallback ? '⚠ Demo results (backend offline)' : query.length >= 2 ? 'Search results' : 'Type to search'}
            </span>
            {results.length > 0 && (
              <span className="text-amber-500/80">{results.length} results</span>
            )}
          </div>

          {loading && (
            <div className="p-4 text-center text-slate-400 text-sm">Searching…</div>
          )}

          {!loading && results.map((movie) => (
            <div
              key={getMovieId(movie)}
              onClick={() => handleSelectMovie(movie)}
              className="flex items-center gap-3.5 p-2.5 rounded-xl hover:bg-white/5 transition-all cursor-pointer group"
            >
              {/* Poster thumbnail */}
              <div className="w-10 h-14 rounded-md border border-white/10 shrink-0 overflow-hidden bg-[#121317] group-hover:border-amber-500/50 transition-colors">
                {getMoviePoster(movie) ? (
                  <img
                    src={getMoviePoster(movie)}
                    alt={movie.title}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-600">
                    <Film className="w-4 h-4" />
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-white group-hover:text-amber-400 transition-colors truncate">
                    {movie.title}
                  </h4>
                  <span className="text-xs text-slate-500 shrink-0">{getMovieYear(movie)}</span>
                </div>
                <p className="text-xs text-slate-400 truncate">
                  {[getMovieDirector(movie), getMovieGenres(movie).slice(0, 2).join(', ')].filter(Boolean).join(' • ')}
                </p>
              </div>

              {/* No fake match% badge */}
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          ))}

          {!loading && query.trim().length >= 2 && results.length === 0 && (
            <div className="p-8 text-center text-slate-400 text-sm space-y-2">
              <Film className="w-8 h-8 text-slate-600 mx-auto" />
              <p>No titles found for "{query}".</p>
              <p className="text-xs text-slate-500">Try a different title.</p>
            </div>
          )}

          {!loading && query.trim().length < 2 && (
            <div className="p-6 text-center text-slate-500 text-xs">
              Start typing to search {usingFallback ? 'demo' : 'real'} movie titles
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
