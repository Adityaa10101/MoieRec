import React, { useState } from 'react';
import { Navbar } from '../components/navigation/Navbar';
import { Footer } from '../components/navigation/Footer';
import { SearchPalette } from '../components/feedback/SearchPalette';
import { PopcornCursor } from '../components/common/PopcornCursor';

interface RootLayoutProps {
  children: React.ReactNode;
}

export const RootLayout: React.FC<RootLayoutProps> = ({ children }) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#0d0e12] text-[#f8fafc] font-sans relative selection:bg-amber-500/30 selection:text-amber-200">
      {/* Film grain noise overlay for cinematic texture */}
      <div className="pointer-events-none fixed inset-0 film-grain z-10 opacity-45" aria-hidden="true" />

      {/* Popcorn custom cursor accessory */}
      <PopcornCursor />

      {/* Global Navigation */}
      <Navbar onOpenSearch={() => setIsSearchOpen(true)} />

      {/* Main page content - Native Document-Level Vertical Scrolling */}
      <div className="relative z-10 w-full min-h-screen">{children}</div>

      {/* Global Footer */}
      <Footer />

      {/* Search Palette Command Flyout (Cmd+K) */}
      <SearchPalette isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </div>
  );
};
