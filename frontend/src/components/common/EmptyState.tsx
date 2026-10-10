import React from 'react';
import { Film, Sliders, AlertCircle, Compass } from 'lucide-react';
import { Link } from '../../router/Router';

interface EmptyStateProps {
  type: 'plan' | 'watchlist' | 'discovery' | 'error';
  title?: string;
  description?: string;
  actionText?: string;
  actionHref?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  type,
  title,
  description,
  actionText,
  actionHref,
  onAction,
}) => {
  const getIcon = () => {
    switch (type) {
      case 'plan':
      case 'watchlist':
        return <Film className="w-8 h-8 text-amber-500" />;
      case 'discovery':
        return <Sliders className="w-8 h-8 text-amber-500" />;
      case 'error':
        return <AlertCircle className="w-8 h-8 text-amber-500" />;
      default:
        return <Compass className="w-8 h-8 text-amber-500" />;
    }
  };

  const defaultTitle =
    type === 'plan' || type === 'watchlist'
      ? 'No movies in Plan to watch.'
      : type === 'discovery'
      ? 'No movies match these filters.'
      : 'Connection momentarily disrupted.';

  const defaultDescription =
    type === 'plan' || type === 'watchlist'
      ? 'Add movies from Explore or your recommendations to build your list.'
      : type === 'discovery'
      ? 'Try selecting different genres or decades to find movies.'
      : 'Your picks are safely preserved in browser storage.';

  const defaultActionText =
    type === 'watchlist'
      ? 'Browse Explore'
      : type === 'discovery'
      ? 'Reset Filters'
      : 'Try Again';

  return (
    <div className="p-8 sm:p-12 rounded-2xl bg-[#1a1b20] border border-white/10 text-center space-y-4 max-w-xl mx-auto my-8">
      <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto">
        {getIcon()}
      </div>
      <div className="space-y-1">
        <h3 className="font-serif text-xl sm:text-2xl text-white font-semibold">{title || defaultTitle}</h3>
        <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
          {description || defaultDescription}
        </p>
      </div>

      <div className="pt-2">
        {actionHref ? (
          <Link
            to={actionHref}
            className="inline-flex px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-[#0d0e12] font-semibold text-xs transition-colors"
          >
            {actionText || defaultActionText}
          </Link>
        ) : (
          <button
            onClick={onAction}
            className="px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-[#0d0e12] font-semibold text-xs transition-colors cursor-pointer"
          >
            {actionText || defaultActionText}
          </button>
        )}
      </div>
    </div>
  );
};
