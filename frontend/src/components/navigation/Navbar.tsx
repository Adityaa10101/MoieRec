import React, { useState, useEffect, useRef } from 'react';
import { useRouter, Link } from '../../router/Router';
import {
  Film,
  Search,
  Menu,
  X,
  Sparkles,
  User,
  Heart,
  Bookmark,
  HelpCircle,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { useUserTaste } from '../../context/UserTasteContext';

interface NavbarProps {
  onOpenSearch: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenSearch }) => {
  const { path, navigate } = useRouter();
  const {
    setIsOnboardingOpen,
    validLikedIds,
    planMovieIds,
    savedMovieCount,
    clearAllData,
  } = useUserTaste();

  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const avatarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 40);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close avatar menu on outside click or Escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) {
        setAvatarMenuOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setAvatarMenuOpen(false);
        setMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const navLinks = [
    { label: 'Home', to: '/' },
    { label: 'Explore', to: '/explore' },
    { label: 'My Library', to: '/library' },
  ];

  const totalLibraryCount = validLikedIds.length + savedMovieCount;

  const handleClearDataConfirmed = () => {
    clearAllData();
    setShowClearConfirm(false);
    setAvatarMenuOpen(false);
    setMobileMenuOpen(false);
  };

  const isHome = path === '/';

  return (
    <>
      <header
        className={`fixed top-0 left-0 right-0 z-50 w-full transition-all duration-300 ease-out ${
          isScrolled
            ? 'h-[72px] bg-[#0d0e12]/92 backdrop-blur-md border-b border-white/10 shadow-[0_12px_32px_rgba(0,0,0,0.70)]'
            : isHome
              ? 'h-20 bg-gradient-to-b from-black/50 via-black/15 to-transparent border-b border-transparent'
              : 'h-20 bg-[#121317]/40 backdrop-blur-sm border-b border-transparent'
        }`}
      >
        <div className="flex justify-between items-center h-full px-6 md:px-12 max-w-7xl mx-auto w-full">
          {/* Brand & Global Nav Links */}
          <div className="flex items-center gap-6 lg:gap-10 shrink-0">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group shrink-0">
              <span className="w-8 h-8 rounded-lg bg-[#23252b] border border-white/10 flex items-center justify-center text-amber-500 group-hover:border-amber-500/80 transition-colors">
                <Film className="w-4 h-4 text-amber-500" />
              </span>
              <span className="font-serif text-2xl tracking-tight text-white group-hover:text-amber-400 transition-colors font-semibold">
                MoieRec
              </span>
            </Link>

            {/* Desktop Navigation Items (nowrap to prevent 2-line wraps) */}
            <nav className="hidden md:flex items-center gap-6 lg:gap-7 whitespace-nowrap">
              {navLinks.map((link) => {
                const isActive = path === link.to;
                return (
                  <Link
                    key={link.to}
                    to={link.to}
                    className={`relative text-sm transition-colors py-1 px-1 font-medium whitespace-nowrap ${
                      isActive
                        ? 'text-amber-500 font-semibold'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-white/5 rounded-md'
                    }`}
                  >
                    {link.label}
                    {isActive && (
                      <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-amber-500 rounded-full" />
                    )}
                  </Link>
                );
              })}

              {/* Quick Search Action */}
              <button
                id="navbar-search-btn"
                onClick={onOpenSearch}
                className="text-slate-400 hover:text-slate-100 transition-colors text-sm flex items-center gap-2 hover:bg-white/5 px-2.5 py-1 rounded-md cursor-pointer whitespace-nowrap"
              >
                <Search className="w-3.5 h-3.5" />
                <span>Search</span>
                <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-[#1f1f24] rounded border border-white/10">
                  ⌘K
                </kbd>
              </button>
            </nav>
          </div>

          {/* Right Trailing Action Buttons */}
          <div className="flex items-center gap-3 sm:gap-4 shrink-0">
            {/* Edit your picks action button (nowrap, collapses gracefully on narrow desktop widths) */}
            <button
              onClick={() => setIsOnboardingOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 text-xs font-medium transition-colors cursor-pointer whitespace-nowrap shrink-0"
              title="Edit your onboarding movie picks"
            >
              <Sparkles className="w-3.5 h-3.5 shrink-0" />
              <span className="hidden sm:inline">Edit your picks</span>
              <span className="sm:hidden">Picks</span>
              {validLikedIds.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-amber-500 text-black font-mono text-[10px] font-bold">
                  {validLikedIds.length}
                </span>
              )}
            </button>

            {/* Neutral Guest Avatar Dropdown Trigger */}
            <div className="relative pl-1 sm:pl-2 border-l border-white/10" ref={avatarRef}>
              <button
                onClick={() => setAvatarMenuOpen((prev) => !prev)}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                  avatarMenuOpen
                    ? 'bg-amber-500 text-black ring-2 ring-amber-500/50'
                    : 'bg-[#1f2028] border border-white/10 text-slate-300 hover:text-white hover:border-amber-500/60'
                }`}
                title="Account menu (Guest mode)"
                aria-haspopup="true"
                aria-expanded={avatarMenuOpen}
              >
                <User className="w-4 h-4" />
              </button>

              {/* Accessible Dropdown Menu */}
              {avatarMenuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 mt-3 w-64 rounded-2xl bg-[#14151a] border border-white/10 shadow-2xl p-2 space-y-1 z-50 animate-in fade-in slide-in-from-top-2 duration-150 text-left"
                >
                  <div className="px-3 py-2 border-b border-white/5 space-y-0.5">
                    <div className="text-xs font-semibold text-white flex items-center justify-between">
                      <span>Guest Mode</span>
                      <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                        Browser local
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 leading-tight">
                      Your picks are saved only in this browser.
                    </p>
                  </div>

                  <div className="py-1">
                    <button
                      role="menuitem"
                      onClick={() => {
                        navigate('/library');
                        setAvatarMenuOpen(false);
                      }}
                      className="w-full px-3 py-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-white/5 flex items-center justify-between transition-colors cursor-pointer text-left"
                    >
                      <span className="flex items-center gap-2">
                        <Film className="w-3.5 h-3.5 text-amber-400" />
                        <span>My Library</span>
                      </span>
                      {totalLibraryCount > 0 && (
                        <span className="font-mono text-[10px] text-slate-400 font-bold">
                          {totalLibraryCount}
                        </span>
                      )}
                    </button>

                    <button
                      role="menuitem"
                      onClick={() => {
                        navigate('/library?tab=liked');
                        setAvatarMenuOpen(false);
                      }}
                      className="w-full px-3 py-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-white/5 flex items-center justify-between transition-colors cursor-pointer text-left"
                    >
                      <span className="flex items-center gap-2">
                        <Heart className="w-3.5 h-3.5 text-rose-400" />
                        <span>Liked movies</span>
                      </span>
                      <span className="font-mono text-[10px] text-slate-400 font-bold">
                        {validLikedIds.length}
                      </span>
                    </button>

                    <button
                      role="menuitem"
                      onClick={() => {
                        navigate('/library?tab=plan');
                        setAvatarMenuOpen(false);
                      }}
                      className="w-full px-3 py-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-white/5 flex items-center justify-between transition-colors cursor-pointer text-left"
                    >
                      <span className="flex items-center gap-2">
                        <Bookmark className="w-3.5 h-3.5 text-amber-400" />
                        <span>Plan to watch</span>
                      </span>
                      <span className="font-mono text-[10px] text-slate-400 font-bold">
                        {planMovieIds.length}
                      </span>
                    </button>

                    <button
                      role="menuitem"
                      onClick={() => {
                        setIsOnboardingOpen(true);
                        setAvatarMenuOpen(false);
                      }}
                      className="w-full px-3 py-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-white/5 flex items-center gap-2 transition-colors cursor-pointer text-left"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                      <span>Edit your picks</span>
                    </button>

                    <button
                      role="menuitem"
                      onClick={() => {
                        navigate('/about');
                        setAvatarMenuOpen(false);
                      }}
                      className="w-full px-3 py-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-white/5 flex items-center gap-2 transition-colors cursor-pointer text-left"
                    >
                      <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                      <span>How it works</span>
                    </button>
                  </div>

                  <div className="pt-1 border-t border-white/5">
                    <button
                      role="menuitem"
                      onClick={() => {
                        setShowClearConfirm(true);
                        setAvatarMenuOpen(false);
                      }}
                      className="w-full px-3 py-2 rounded-lg text-xs text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors cursor-pointer text-left"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Clear my data</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Mobile hamburger menu toggle */}
            <button
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="md:hidden w-9 h-9 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/5 transition-colors ml-1 cursor-pointer"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Drawer Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[#121317] border-b border-white/10 px-6 py-5 space-y-3 animate-in slide-in-from-top-2 duration-200">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileMenuOpen(false)}
                className={`block py-2 text-sm font-medium ${
                  path === link.to ? 'text-amber-500 font-semibold' : 'text-slate-300'
                }`}
              >
                {link.label}
              </Link>
            ))}

            <button
              onClick={() => {
                setMobileMenuOpen(false);
                onOpenSearch();
              }}
              className="w-full text-left py-2 text-sm font-medium text-slate-300 flex items-center justify-between"
            >
              <span className="flex items-center gap-2">
                <Search className="w-4 h-4 text-slate-400" />
                <span>Search Cinema</span>
              </span>
              <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-white/5 rounded border border-white/10">
                ⌘K
              </kbd>
            </button>

            <div className="pt-3 border-t border-white/10 space-y-1">
              <Link
                to="/library?tab=liked"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-between py-2 text-xs text-slate-300"
              >
                <span className="flex items-center gap-2">
                  <Heart className="w-3.5 h-3.5 text-rose-400" />
                  <span>Liked movies</span>
                </span>
                <span className="font-mono text-amber-400 font-bold">{validLikedIds.length}</span>
              </Link>

              <Link
                to="/library?tab=plan"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-between py-2 text-xs text-slate-300"
              >
                <span className="flex items-center gap-2">
                  <Bookmark className="w-3.5 h-3.5 text-amber-400" />
                  <span>Plan to watch</span>
                </span>
                <span className="font-mono text-amber-400 font-bold">{planMovieIds.length}</span>
              </Link>

              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  setIsOnboardingOpen(true);
                }}
                className="w-full text-left flex items-center gap-2 py-2 text-xs text-slate-300"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>Edit your picks</span>
              </button>

              <Link
                to="/about"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 py-2 text-xs text-slate-300"
              >
                <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                <span>How it works</span>
              </Link>

              <button
                onClick={() => {
                  setShowClearConfirm(true);
                  setMobileMenuOpen(false);
                }}
                className="w-full text-left flex items-center gap-2 py-2 text-xs text-red-400"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear my data</span>
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Global Clear My Data Confirmation Modal */}
      {showClearConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setShowClearConfirm(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-[#14151a] border border-white/10 p-6 sm:p-7 space-y-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-red-500/15 border border-red-500/30 flex items-center justify-center text-red-400 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="font-serif text-lg font-bold text-white">
                  Clear all data stored in this browser?
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  This will delete all of your onboarding picks, liked movies, and watchlist stored in this browser. Recommendations will return to default popularity until you pick movies again.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleClearDataConfirmed}
                className="px-4 py-2 rounded-xl bg-red-500 hover:bg-red-600 text-white text-xs font-bold transition-colors cursor-pointer shadow-lg shadow-red-500/20"
              >
                Confirm Delete All Data
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
