import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Film, ArrowRight } from 'lucide-react';
import { ALL_MOCK_MOVIES } from '../../data/mockMovies';
import { useRouter } from '../../router/Router';

interface SearchPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SearchPalette: React.FC<SearchPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const { navigate } = useRouter();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const handleClose = React.useCallback(() => {
    setQuery('');
    onClose();
  }, [onClose]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          handleClose();
        } else {
          // Open search modal
          const searchBtn = document.getElementById('navbar-search-btn');
          searchBtn?.click();
        }
      }
      if (e.key === 'Escape' && isOpen) {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleClose]);

  if (!isOpen) return null;

  const filteredMovies = query.trim()
    ? ALL_MOCK_MOVIES.filter(
        (m) =>
          m.title.toLowerCase().includes(query.toLowerCase()) ||
          m.director.toLowerCase().includes(query.toLowerCase()) ||
          m.genres.some((g) => g.toLowerCase().includes(query.toLowerCase())) ||
          m.tags.some((t) => t.toLowerCase().includes(query.toLowerCase()))
      )
    : ALL_MOCK_MOVIES.slice(0, 5);

  const handleSelectMovie = (id: string) => {
    handleClose();
    navigate(`/movie/${id}`);
  };

  return (
    <div
      onClick={handleClose}
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/80 backdrop-blur-md"
    >
      <div
        className="w-full max-w-2xl rounded-2xl bg-[#1a1b20] border border-amber-500/30 shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-white/10 gap-3 bg-[#23252b]">
          <Search className="w-5 h-5 text-amber-500 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search titles, directors, tropes, or cinematography..."
            className="flex-1 bg-transparent border-none text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-mono bg-white/5 border border-white/10 text-slate-400">
            ESC
          </kbd>
        </div>

        {/* Results list */}
        <div className="overflow-y-auto p-3 space-y-1.5 flex-1 divide-y divide-white/5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 px-3 py-1.5 flex items-center justify-between">
            <span>{query ? 'Matching Curated Film Nodes' : 'Curatorial Recommendations For You'}</span>
            <span className="text-amber-500/80">{filteredMovies.length} results</span>
          </div>

          {filteredMovies.map((movie) => (
            <div
              key={movie.id}
              onClick={() => handleSelectMovie(movie.id)}
              className="flex items-center gap-3.5 p-2.5 rounded-xl hover:bg-white/5 transition-all cursor-pointer group"
            >
              <img
                src={movie.poster}
                alt={movie.title}
                className="w-10 h-14 object-cover rounded-md border border-white/10 shrink-0 group-hover:border-amber-500/50 transition-colors"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-white group-hover:text-amber-400 transition-colors truncate">
                    {movie.title}
                  </h4>
                  <span className="text-xs text-slate-500">{movie.year}</span>
                </div>
                <p className="text-xs text-slate-400 truncate">
                  {movie.director} • {movie.genres.join(', ')}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <div className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-mono font-bold">
                  {movie.matchScore}%
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>
          ))}

          {filteredMovies.length === 0 && (
            <div className="p-8 text-center text-slate-400 text-sm space-y-2">
              <Film className="w-8 h-8 text-slate-600 mx-auto" />
              <p>No titles match this exact intersection of mood and keywords.</p>
              <p className="text-xs text-slate-500">Try searching for Denis Villeneuve, Nolan, or Sci-Fi.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
