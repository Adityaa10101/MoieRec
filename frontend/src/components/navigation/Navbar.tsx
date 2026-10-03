import React, { useState, useEffect } from 'react';
import { useRouter, Link } from '../../router/Router';
import { Film, Search, Radar, Bell, Menu, X, Check } from 'lucide-react';
import { useToast } from '../../context/ToastContext';

interface NavbarProps {
  onOpenSearch: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenSearch }) => {
  const { path } = useRouter();
  const { showToast } = useToast();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      // 40px threshold as specified in section 3.1
      if (window.scrollY > 40) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'Home', to: '/' },
    { label: 'Explore', to: '/explore' },
    { label: 'My Taste', to: '/my-taste', hasPulse: true },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 w-full transition-all duration-300 ease-out ${
        isScrolled
          ? 'h-[72px] bg-[#0d0e12]/92 backdrop-blur-md border-b border-white/10 shadow-[0_12px_32px_rgba(0,0,0,0.70)]'
          : 'h-20 bg-[#121317]/40 backdrop-blur-sm border-b border-transparent'
      }`}
    >
      <div className="flex justify-between items-center h-full px-6 md:px-12 max-w-7xl mx-auto w-full">
        {/* Brand & Global Nav Links */}
        <div className="flex items-center gap-8 lg:gap-10">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <span className="w-8 h-8 rounded-lg bg-[#23252b] border border-white/10 flex items-center justify-center text-amber-500 group-hover:border-amber-500/80 transition-colors">
              <Film className="w-4 h-4 text-amber-500" />
            </span>
            <span className="font-serif text-2xl tracking-tight text-white group-hover:text-amber-400 transition-colors font-semibold">
              MoieRec
            </span>
          </Link>

          {/* Desktop Navigation Items */}
          <nav className="hidden md:flex items-center gap-7">
            {navLinks.map((link) => {
              const isActive = path === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`relative text-sm transition-colors py-1 flex items-center gap-2 font-medium ${
                    isActive
                      ? 'text-amber-500 font-semibold'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-white/5 px-2 rounded-md'
                  }`}
                >
                  {link.label}
                  {link.hasPulse && (
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  )}
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
              className="text-slate-400 hover:text-slate-100 transition-colors text-sm flex items-center gap-2 hover:bg-white/5 px-2.5 py-1 rounded-md cursor-pointer"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search</span>
              <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-[#1f1f24] rounded border border-white/10">
                ⌘K
              </kbd>
            </button>
          </nav>
        </div>

        {/* Right Trailing Profile & Curatorial Status */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Curated Taste Indicator Pill */}
          <Link
            to="/my-taste"
            className="hidden lg:flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-[#1f1f24] border border-white/10 text-slate-300 hover:border-amber-500/40 hover:bg-[#23252b] transition-all group"
          >
            <Radar className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-[11px] font-mono tracking-wider text-slate-200 uppercase font-medium">
              Cinephile Tier
            </span>
            <span className="text-slate-600">•</span>
            <span className="text-[11px] font-mono text-amber-400 font-semibold group-hover:underline">
              Sci-Fi & Neo-Noir 92%
            </span>
          </Link>

          {/* Trailing action: Curator Radar Engine */}
          <button
            onClick={() => showToast('Taste affinity engine calibrated with 8,420 nodes', { icon: 'sparkles' })}
            className="w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-amber-400 hover:bg-white/5 transition-all"
            title="Curator Radar Engine"
          >
            <Radar className="w-4 h-4" />
          </button>

          {/* Trailing action: Notifications */}
          <button
            onClick={() => showToast('New 4K Criterion remaster of Stalker added to your feed', { icon: 'info' })}
            className="relative w-9 h-9 rounded-full flex items-center justify-center text-slate-400 hover:text-amber-400 hover:bg-white/5 transition-all"
            title="Curator Alerts"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-amber-500" />
          </button>

          {/* Curator Avatar */}
          <div className="relative pl-2 border-l border-white/10">
            <Link
              to="/my-taste"
              className="relative block rounded-full p-0.5 border border-amber-500/80 transition-transform active:scale-95"
              title="Curator Profile"
            >
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA3pZwnHtgh_beyzUuDoTZmnCuPVwUuktxeVul1UUA53VXidazd-EFGzmtyxa4xE2U6s8H6QaI3UESMRTgGXHI53dWMC7YRe8itoaFfBlD_G7IaQyXpzJkZI6FRLVfVAj9eD1CIZGt1HZaj6Esqq34lrY5DrryMdf4BzeQQnFWccYS78VocppcLHlvijQZJTxKgRkBKQqUhVrqcNBN6FBvtYakrIZ-ktSy-n_2SigWk_5_3nkveCPiV"
                alt="Curator Elena"
                className="w-8 h-8 rounded-full object-cover"
              />
              <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-amber-500 rounded-full border-2 border-[#121317] flex items-center justify-center">
                <Check className="w-2 h-2 text-[#121317] stroke-[3]" />
              </span>
            </Link>
          </div>

          {/* Mobile hamburger menu toggle */}
          <button
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="md:hidden w-9 h-9 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/5 transition-colors ml-1"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#121317] border-b border-white/10 px-6 py-4 space-y-3 animate-in slide-in-from-top-2 duration-200">
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
            <span>Search Cinema</span>
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-white/5 rounded border border-white/10">
              ⌘K
            </kbd>
          </button>
          <div className="pt-2 border-t border-white/10">
            <Link
              to="/my-taste"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-between py-2 text-xs font-mono text-amber-400"
            >
              <span>Taste DNA Profile</span>
              <span>Sci-Fi & Neo-Noir 92%</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
