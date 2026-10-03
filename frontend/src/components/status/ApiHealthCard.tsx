import React from 'react';
import { Activity, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { useHealthCheck } from '../../hooks/useHealthCheck';
import { Badge } from '../common/Badge';

export const ApiHealthCard: React.FC = () => {
  const { data, loading, error, refetch } = useHealthCheck();

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-amber-400" />
          <h2 className="text-base font-semibold text-white">Backend Health Status</h2>
        </div>
        <button
          onClick={refetch}
          disabled={loading}
          className="text-xs text-slate-400 hover:text-amber-400 flex items-center gap-1.5 px-2.5 py-1.5 rounded-md hover:bg-slate-800 transition"
          title="Refresh status"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="space-y-3">
        {loading ? (
          <div className="text-sm text-slate-400 py-3">Connecting to FastAPI health endpoint...</div>
        ) : error ? (
          <div className="flex items-start gap-3 p-3.5 rounded-lg bg-red-950/30 border border-red-900/40 text-red-300 text-sm">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Backend not reached</p>
              <p className="text-xs text-red-400/80 mt-1">{error}</p>
              <p className="text-xs text-slate-400 mt-2">
                Ensure the backend is started at <code>http://localhost:8000</code>.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between p-3.5 rounded-lg bg-slate-950/40 border border-slate-800/80">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <p className="text-sm font-medium text-white">{data?.service || 'MoieRec API'}</p>
                <p className="text-xs text-slate-400">Endpoint: /api/health</p>
              </div>
            </div>
            <Badge label={`Status: ${data?.status || 'ok'}`} variant="emerald" />
          </div>
        )}
      </div>
    </div>
  );
};
