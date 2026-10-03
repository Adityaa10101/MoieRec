import React from 'react';

interface BadgeProps {
  label: string;
  variant?: 'amber' | 'emerald' | 'blue' | 'slate';
}

export const Badge: React.FC<BadgeProps> = ({ label, variant = 'slate' }) => {
  const variantStyles = {
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    slate: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${variantStyles[variant]}`}
    >
      {label}
    </span>
  );
};
