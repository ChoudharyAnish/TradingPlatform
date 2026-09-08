function getApiUrl(): string {
  // Server components run inside Docker: use internal service DNS.
  // Browser/client components must hit the host-published API port.
  if (typeof window === "undefined") {
    return (
      process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000"
    );
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiUrl()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const getHealth = () => api<{ status: string }>("/api/health");
export const getRegime = () => api<{ regime: string; as_of_date: string; features: Record<string, number> }>("/api/market/regime");
export const getSignals = () => api<{ top: Signal[]; worst: Signal[]; disclaimer: string }>("/api/signals");
export const getPredictions = () => api<{ items: Signal[]; disclaimer: string }>("/api/predictions");
export const getStocks = () => api<Stock[]>("/api/stocks");
export const getPrices = (symbol: string) => api<{ bars: Bar[] }>(`/api/stocks/${symbol}/prices`);
export const getModels = () => api<ModelRow[]>("/api/models");
export const getBacktests = () => api<BacktestRow[]>("/api/backtests");
export const getBacktest = (id: number) => api<BacktestDetail>(`/api/backtests/${id}`);
export const createBacktest = (body: unknown) =>
  api<BacktestDetail>("/api/backtests", { method: "POST", body: JSON.stringify(body) });
export const getPortfolio = () => api<Portfolio>("/api/portfolio");
export const getRisk = () => api<{ paper: { drawdown: number; equity: number }; limits: Record<string, number> }>("/api/risk");
export const getDataQuality = () => api<DQRow[]>("/api/data-quality");
export const screen = (body: unknown) => api<{ items: Signal[] }>("/api/screener", { method: "POST", body: JSON.stringify(body) });

export type Signal = {
  symbol: string;
  signal: string;
  probability: number;
  expected_return: number;
  risk_score: number;
  stop_loss: number;
  target_price: number;
  current_price: number;
  market_regime: string;
  model_version: string;
  risk_reward: number;
  holding_period_days: number;
  explanations?: { feature: string; contribution: number; direction: string }[];
  result_channel?: string;
};

export type Stock = { id: number; symbol: string; name: string; is_liquid: boolean; instrument_type: string };
export type Bar = { trade_date: string; open: number; high: number; low: number; close: number; volume: number };
export type ModelRow = {
  model_id: string;
  model_type: string;
  version: string;
  status: string;
  validation_metrics: Record<string, number>;
  test_metrics: Record<string, number>;
  warnings: string[];
  training_date: string;
  features: string[];
};
export type BacktestRow = { id: number; name: string; strategy: string; metrics: Record<string, number>; warnings: string[]; result_channel: string };
export type BacktestDetail = BacktestRow & {
  equity_curve: { date: string; equity: number }[];
  drawdown_curve: { date: string; drawdown: number }[];
  monthly_returns: Record<string, number>;
  benchmark_metrics: Record<string, unknown>;
  disclaimer?: string;
};
export type Portfolio = {
  cash: number;
  equity: number;
  unrealized_pnl: number;
  realized_pnl: number;
  drawdown: number;
  positions: unknown[];
  trades: unknown[];
  result_channel: string;
  disclaimer: string;
};
export type DQRow = { check_type: string; severity: string; message: string; checked_at?: string };
