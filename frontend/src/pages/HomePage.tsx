import React, { useState } from 'react';
import { HERO_MOVIE, MOCK_RECOMMENDATION_ROWS } from '../data/mockMovies';
import { HeroSpotlight } from '../components/movie/HeroSpotlight';
import { RecommendationRow } from '../components/recommendations/RecommendationRow';
import { WhyThisModal } from '../components/feedback/WhyThisModal';
import { TasteRadarDock } from '../components/feedback/TasteRadarDock';
import type { Movie } from '../types/movie';

export const HomePage: React.FC = () => {
  const [selectedMovieForWhyThis, setSelectedMovieForWhyThis] = useState<Movie | null>(null);

  const handleOpenWhyThis = (movie: Movie) => {
    setSelectedMovieForWhyThis(movie);
  };

  const handleCloseWhyThis = () => {
    setSelectedMovieForWhyThis(null);
  };

  return (
    <div className="relative min-h-screen">
      {/* HERO SPOTLIGHT */}
      <HeroSpotlight movie={HERO_MOVIE} onOpenWhyThis={handleOpenWhyThis} />

      {/* CURATED RECOMMENDATION ROWS CONTAINER */}
      <main className="relative z-20 space-y-16 pb-28 max-w-7xl mx-auto px-6 sm:px-12">
        {MOCK_RECOMMENDATION_ROWS.map((row) => (
          <RecommendationRow key={row.id} rowData={row} />
        ))}
      </main>

      {/* TASTE VECTOR RADAR FLYOUT DOCK (DESKTOP) */}
      <TasteRadarDock onInspect={() => handleOpenWhyThis(HERO_MOVIE)} />

      {/* WHY THIS TELEMETRY MODAL */}
      {selectedMovieForWhyThis && (
        <WhyThisModal
          isOpen={!!selectedMovieForWhyThis}
          movie={selectedMovieForWhyThis}
          onClose={handleCloseWhyThis}
        />
      )}
    </div>
  );
};
