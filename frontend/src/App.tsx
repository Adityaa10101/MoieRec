import React, { useEffect } from 'react';
import { RouterProvider, useRouter } from './router/Router';
import { ToastProvider } from './context/ToastContext';
import { AmbientBackdropProvider } from './context/AmbientBackdropContext';
import { UserTasteProvider } from './context/UserTasteContext';
import { PopcornCursorProvider } from './context/PopcornCursorContext';
import { RootLayout } from './layouts/RootLayout';
import { HomePage } from './pages/HomePage';
import { MovieDetailPage } from './pages/MovieDetailPage';
import { ExplorePage } from './pages/ExplorePage';
import { LibraryPage } from './pages/LibraryPage';
import { AboutPage } from './pages/AboutPage';
import { ApiHealthCard } from './components/status/ApiHealthCard';

const RouteDispatcher: React.FC = () => {
  const { path, navigate } = useRouter();

  // Route redirects
  useEffect(() => {
    if (path === '/login' || path === '/register') {
      navigate('/');
    } else if (path === '/my-taste') {
      navigate('/library');
    }
  }, [path, navigate]);

  if (path === '/' || path === '' || path === '/login' || path === '/register') {
    return <HomePage />;
  }

  if (path.startsWith('/movie/')) {
    return <MovieDetailPage />;
  }

  if (path === '/explore') {
    return <ExplorePage />;
  }

  if (path === '/library' || path === '/my-taste') {
    return <LibraryPage />;
  }

  if (path === '/about') {
    return <AboutPage />;
  }

  if (path === '/system-status') {
    return (
      <div className="pt-28 pb-20 max-w-4xl mx-auto px-6 space-y-6">
        <h1 className="font-serif text-3xl font-bold text-white">System Architecture & Health</h1>
        <ApiHealthCard />
      </div>
    );
  }

  // Default fallback
  return <HomePage />;
};

export const App: React.FC = () => {
  return (
    <RouterProvider>
      <ToastProvider>
        <AmbientBackdropProvider>
          <UserTasteProvider>
            <PopcornCursorProvider>
              <RootLayout>
                <RouteDispatcher />
              </RootLayout>
            </PopcornCursorProvider>
          </UserTasteProvider>
        </AmbientBackdropProvider>
      </ToastProvider>
    </RouterProvider>
  );
};

export default App;
