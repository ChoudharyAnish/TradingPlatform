import { getPortfolio } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PortfolioPage() {
  let p: Awaited<ReturnType<typeof getPortfolio>> | null = null;
  try {
    p = await getPortfolio();
  } catch {
    p = null;
  }

  return (
    <div className="space-y-6 animate-rise">
      <h1 className="font-display text-4xl">Paper trading</h1>
      <p className="text-ink/65 max-w-2xl">
        Virtual capital only. Live broker adapters are intentionally not implemented. Results are labeled{" "}
        <strong>PAPER</strong>, never mixed with backtests.
      </p>
      {!p && <p className="text-alert">API unavailable.</p>}
      {p && (
        <div className="grid md:grid-cols-4 gap-4">
          <Stat label="Equity" value={`₹${Math.round(p.equity).toLocaleString("en-IN")}`} />
          <Stat label="Cash" value={`₹${Math.round(p.cash).toLocaleString("en-IN")}`} />
          <Stat label="Realized P&L" value={`₹${Math.round(p.realized_pnl).toLocaleString("en-IN")}`} />
          <Stat label="Drawdown" value={`${(p.drawdown * 100).toFixed(2)}%`} />
        </div>
      )}
      {p && (
        <>
          <h2 className="font-display text-2xl">Positions</h2>
          <pre className="text-xs bg-white/70 border border-ink/10 rounded-xl p-3 overflow-auto">
            {JSON.stringify(p.positions, null, 2)}
          </pre>
          <h2 className="font-display text-2xl">Recent trades</h2>
          <pre className="text-xs bg-white/70 border border-ink/10 rounded-xl p-3 overflow-auto">
            {JSON.stringify(p.trades, null, 2)}
          </pre>
          <p className="text-xs text-ink/50">{p.disclaimer}</p>
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink/10 bg-white/70 p-4">
      <div className="text-xs uppercase text-ink/45">{label}</div>
      <div className="font-display text-2xl mt-1">{value}</div>
    </div>
  );
}
