import { apiClient } from './apiClient';
import type { HealthStatus } from '../types';

export const healthService = {
  async checkHealth(): Promise<HealthStatus> {
    return apiClient.get<HealthStatus>('/health');
  },
};
