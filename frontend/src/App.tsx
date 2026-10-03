import React from 'react';
import { RootLayout } from './layouts/RootLayout';
import { HomePage } from './pages/HomePage';

export const App: React.FC = () => {
  return (
    <RootLayout>
      <HomePage />
    </RootLayout>
  );
};

export default App;
