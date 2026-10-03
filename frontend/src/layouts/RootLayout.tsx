import React from 'react';
import { Header } from '../components/common/Header';

interface RootLayoutProps {
  children: React.ReactNode;
}

export const RootLayout: React.FC<RootLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans selection:bg-amber-500/30 selection:text-amber-200">
      <Header />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10">{children}</main>
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        MoieRec · College Mini-Project · Phase 1: Foundation
      </footer>
    </div>
  );
};
