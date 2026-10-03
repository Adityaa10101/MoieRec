import React from 'react';

export const MovieCardSkeleton: React.FC = () => {
  return (
    <div
      className="flex-shrink-0 w-60 rounded-xl bg-[#16171d] border border-white/5 overflow-hidden animate-shimmer"
      aria-hidden="true"
    >
      {/* Exact 2:3 aspect ratio */}
      <div className="aspect-[2/3] w-full bg-[#1c1d24]" />
      <div className="p-4 space-y-2.5">
        <div className="h-3 w-24 bg-white/10 rounded" />
        <div className="h-4 w-36 bg-white/15 rounded" />
        <div className="h-3 w-48 bg-white/5 rounded" />
        <div className="pt-2 flex justify-between border-t border-white/5">
          <div className="h-2.5 w-16 bg-white/10 rounded" />
          <div className="h-2.5 w-8 bg-white/10 rounded" />
        </div>
      </div>
    </div>
  );
};
