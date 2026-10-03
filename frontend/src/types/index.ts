export interface HealthStatus {
  status: string;
  service: string;
}

export interface ApiError {
  message: string;
  statusCode?: number;
}
