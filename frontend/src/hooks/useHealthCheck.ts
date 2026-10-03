import { useState, useEffect } from 'react';
import { healthService } from '../services/healthService';
import type { HealthStatus } from '../types';

export function useHealthCheck() {
  const [data, setData] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await healthService.checkHealth();
      setData(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Unknown error connecting to API');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return { data, loading, error, refetch: fetchHealth };
}
