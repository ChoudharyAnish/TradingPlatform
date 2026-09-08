import Link from "next/link";
import { getPredictions } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PredictionsPage() {
  let items: Awaited<ReturnType<typeof getPredictions>>["items"] = [];
  let disclaimer = "";
  try {
    const data = await getPredictions();
    items = data.items;
    disclaimer = data.disclaimer;
  } catch {
    disclaimer = "API unavailable.";
  }

  return (
    <div className="space-y-6 animate-rise">
      <h1 className="font-display text-4xl">Predictions</h1>
      <p className="text-ink/65 max-w-2xl">
        Each row includes probability, expected return, risk, stops/targets, and model version. Channel labels
        distinguish research outputs from live markets.
      </p>
      <div className="overflow-x-auto rounded-xl border border-ink/10 bg-white/70">
        <table className="min-w-full text-sm">
          <thead className="text-left text-ink/50 border-b border-ink/10">
            <tr>
              <th className="p-3">Stock</th>
              <th className="p-3">Signal</th>
              <th className="p-3">Prob</th>
              <th className="p-3">Exp. return</th>
              <th className="p-3">Risk</th>
              <th className="p-3">Stop</th>
              <th className="p-3">Target</th>
              <th className="p-3">Channel</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.symbol} className="border-b border-ink/5 hover:bg-mist/50">
                <td className="p-3">
                  <Link className="text-sea font-medium" href={`/stocks/${p.symbol}`}>
                    {p.symbol}
                  </Link>
                  <div className="text-xs text-ink/45">₹{p.current_price?.toFixed?.(2)}</div>
                </td>
                <td className="p-3">{p.signal}</td>
                <td className="p-3">{(p.probability * 100).toFixed(0)}%</td>
                <td className="p-3">{(p.expected_return * 100).toFixed(2)}%</td>
                <td className="p-3">{(p.risk_score * 100).toFixed(0)}</td>
                <td className="p-3">₹{p.stop_loss?.toFixed?.(2)}</td>
                <td className="p-3">₹{p.target_price?.toFixed?.(2)}</td>
                <td className="p-3 text-xs">{p.result_channel}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-ink/50">{disclaimer}</p>
    </div>
  );
}
