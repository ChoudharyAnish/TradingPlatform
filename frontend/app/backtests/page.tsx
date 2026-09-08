"use client";

import { useEffect, useState } from "react";
import { BacktestDetail, BacktestRow, createBacktest, getBacktest, getBacktests } from "@/lib/api";

export default function BacktestsPage() {
  const [rows, setRows] = useState<BacktestRow[]>([]);
  const [detail, setDetail] = useState<BacktestDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function refresh() {
    try {
      setRows(await getBacktests());
    } catch {
      setMsg("API unavailable");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function run() {
    setBusy(true);
    setMsg("");
    try {
      const bt = await createBacktest({
        name: "ui_momentum",
        strategy: "ensemble_momentum",
        symbols: ["RELIANCE", "TCS", "INFY", "HDFCBANK"],
        start_date: "2024-01-01",
        end_date: "2025-06-30",
        initial_capital: 1000000,
        risk_per_trade: 0.005,
        max_position_size: 0.05,
      });
      setDetail(bt);
      await refresh();
    } catch {
      setMsg("Backtest failed — seed market data first.");
    } finally {
      setBusy(false);
    }
  }

  async function open(id: number) {
    setDetail(await getBacktest(id));
  }

  return (
    <div className="space-y-6 animate-rise">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl">Backtests</h1>
          <p className="text-ink/65 mt-2 max-w-xl">
            Channel: <strong>BACKTEST</strong> only. Includes transaction costs, slippage assumptions, and NIFTY buy&amp;hold
            comparison. Not a forecast of live results.
          </p>
        </div>
        <button disabled={busy} onClick={run} className="bg-ink text-sand px-4 py-2 rounded-md disabled:opacity-50">
          {busy ? "Running…" : "Run example backtest"}
        </button>
      </div>
      {msg && <p className="text-alert text-sm">{msg}</p>}
      <ul className="space-y-2 text-sm">
        {rows.map((r) => (
          <li key={r.id} className="flex justify-between border-b border-ink/10 py-2">
            <button className="text-sea" onClick={() => open(r.id)}>
              #{r.id} {r.name}
            </button>
            <span>
              ret {((r.metrics?.total_return || 0) * 100).toFixed(1)}% · sharpe {(r.metrics?.sharpe || 0).toFixed(2)} ·{" "}
              {r.result_channel}
            </span>
          </li>
        ))}
      </ul>
      {detail && (
        <div className="rounded-xl border border-ink/10 bg-white/70 p-4 space-y-3">
          <h2 className="font-display text-2xl">{detail.name}</h2>
          <pre className="text-xs overflow-auto bg-mist/60 p-3 rounded-md">{JSON.stringify(detail.metrics, null, 2)}</pre>
          <pre className="text-xs overflow-auto bg-mist/60 p-3 rounded-md">{JSON.stringify(detail.benchmark_metrics, null, 2)}</pre>
          <p className="text-sm text-alert">Warnings: {(detail.warnings || []).join(", ") || "none"}</p>
          <p className="text-xs text-ink/50">{detail.disclaimer}</p>
          <EquitySpark curve={detail.equity_curve || []} />
        </div>
      )}
    </div>
  );
}

function EquitySpark({ curve }: { curve: { date: string; equity: number }[] }) {
  if (!curve.length) return null;
  const min = Math.min(...curve.map((c) => c.equity));
  const max = Math.max(...curve.map((c) => c.equity));
  const w = 600;
  const h = 120;
  const pts = curve
    .map((c, i) => {
      const x = (i / (curve.length - 1)) * w;
      const y = h - ((c.equity - min) / (max - min + 1e-9)) * h;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-28">
      <polyline fill="none" stroke="#0e7490" strokeWidth="2" points={pts} />
    </svg>
  );
}
