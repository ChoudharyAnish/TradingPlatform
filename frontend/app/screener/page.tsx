"use client";

import { useState } from "react";
import { screen, Signal } from "@/lib/api";

export default function ScreenerPage() {
  const [minProb, setMinProb] = useState(0.55);
  const [minRet, setMinRet] = useState(0.01);
  const [maxRisk, setMaxRisk] = useState(0.5);
  const [items, setItems] = useState<Signal[]>([]);
  const [error, setError] = useState("");

  async function run() {
    setError("");
    try {
      const res = await screen({
        min_probability: minProb,
        min_expected_return: minRet,
        max_risk_score: maxRisk,
      });
      setItems(res.items);
    } catch (e) {
      setError("Screener failed — is the API running and seeded?");
    }
  }

  return (
    <div className="space-y-6 animate-rise">
      <h1 className="font-display text-4xl">Screener</h1>
      <div className="grid md:grid-cols-4 gap-4 items-end">
        <label className="text-sm">
          Min probability
          <input type="number" step="0.01" value={minProb} onChange={(e) => setMinProb(+e.target.value)} className="mt-1 w-full border border-ink/15 rounded-md px-3 py-2 bg-white/80" />
        </label>
        <label className="text-sm">
          Min expected return
          <input type="number" step="0.005" value={minRet} onChange={(e) => setMinRet(+e.target.value)} className="mt-1 w-full border border-ink/15 rounded-md px-3 py-2 bg-white/80" />
        </label>
        <label className="text-sm">
          Max risk score
          <input type="number" step="0.05" value={maxRisk} onChange={(e) => setMaxRisk(+e.target.value)} className="mt-1 w-full border border-ink/15 rounded-md px-3 py-2 bg-white/80" />
        </label>
        <button onClick={run} className="bg-sea text-white rounded-md px-4 py-2 hover:bg-ink transition">
          Screen
        </button>
      </div>
      {error && <p className="text-alert text-sm">{error}</p>}
      <ul className="space-y-2">
        {items.map((i) => (
          <li key={i.symbol} className="border-b border-ink/10 py-2 flex justify-between text-sm">
            <span className="font-medium">{i.symbol}</span>
            <span>
              {i.signal} · {(i.probability * 100).toFixed(0)}% · ret {(i.expected_return * 100).toFixed(1)}% · risk{" "}
              {(i.risk_score * 100).toFixed(0)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
