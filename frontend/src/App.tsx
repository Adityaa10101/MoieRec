import React from 'react';
import { RouterProvider, useRouter } from './router/Router';
import { ToastProvider } from './context/ToastContext';
import { AmbientBackdropProvider } from './context/AmbientBackdropContext';
import { UserTasteProvider } from './context/UserTasteContext';
import { PopcornCursorProvider } from './context/PopcornCursorContext';
import { RootLayout } from './layouts/RootLayout';
import { HomePage } from './pages/HomePage';
import { MovieDetailPage } from './pages/MovieDetailPage';
import { ExplorePage } from './pages/ExplorePage';
import { MyTastePage } from './pages/MyTastePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ApiHealthCard } from './components/status/ApiHealthCard';

const RouteDispatcher: React.FC = () => {
  const { path } = useRouter();

  if (path === '/' || path === '') {
    return <HomePage />;
  }

  if (path.startsWith('/movie/')) {
    return <MovieDetailPage />;
  }

  if (path === '/explore') {
    return <ExplorePage />;
  }

  if (path === '/my-taste') {
    return <MyTastePage />;
  }

  if (path === '/login') {
    return <LoginPage />;
  }

  if (path === '/register') {
    return <RegisterPage />;
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
