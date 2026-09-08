import Link from "next/link";
import { getPortfolio, getRegime, getRisk, getSignals } from "@/lib/api";

export const dynamic = "force-dynamic";

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

export default async function HomePage() {
  let regime = { regime: "UNKNOWN", as_of_date: "-", features: {} as Record<string, number> };
  let signals = { top: [] as Awaited<ReturnType<typeof getSignals>>["top"], worst: [] as Awaited<ReturnType<typeof getSignals>>["worst"], disclaimer: "" };
  let risk = { paper: { drawdown: 0, equity: 0 }, limits: {} as Record<string, number> };
  let portfolio = { equity: 0, cash: 0, result_channel: "PAPER" };
  let error: string | null = null;
  try {
    [regime, signals, risk, portfolio] = await Promise.all([
      getRegime().catch(() => regime),
      getSignals(),
      getRisk(),
      getPortfolio(),
    ]);
  } catch (e) {
    error = "API unavailable. Start backend (`make up` / `make api`) and run `make seed`.";
  }

  return (
    <div className="space-y-10">
      <section className="animate-rise">
        <p className="text-sea text-sm font-medium tracking-wide uppercase mb-2">Indian equities research</p>
        <h1 className="font-display text-4xl md:text-5xl text-ink max-w-3xl leading-tight">
          Indian Stock AI
        </h1>
        <p className="mt-4 max-w-2xl text-ink/70 text-lg">
          Probabilistic predictions, rigorous backtests, and paper trading — with explicit risk, not false certainty.
        </p>
        <div className="mt-6 flex gap-3">
          <Link href="/predictions" className="bg-ink text-sand px-4 py-2 rounded-md hover:bg-sea transition">
            View predictions
          </Link>
          <Link href="/backtests" className="border border-ink/20 px-4 py-2 rounded-md hover:border-sea hover:text-sea transition">
            Run backtests
          </Link>
        </div>
      </section>

      {error && <p className="text-alert animate-rise-delay">{error}</p>}

      <section className="grid md:grid-cols-4 gap-4 animate-rise-delay">
        <Metric label="Market regime" value={regime.regime} hint={`as of ${regime.as_of_date}`} />
        <Metric label="NIFTY ret 20d" value={fmtPct(Number(regime.features?.ret_20 || 0))} hint="Index context" />
        <Metric label="Paper equity" value={`₹${Math.round(portfolio.equity).toLocaleString("en-IN")}`} hint={portfolio.result_channel} />
        <Metric label="Today's risk (DD)" value={fmtPct(risk.paper.drawdown)} hint="Paper channel" />
      </section>

      <section className="grid md:grid-cols-2 gap-8">
        <SignalList title="Top signals" items={signals.top} />
        <SignalList title="Worst / sell-side" items={signals.worst} />
      </section>
      <p className="text-xs text-ink/50">{signals.disclaimer}</p>
    </div>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-ink/10 bg-white/60 p-4 shadow-soft">
      <div className="text-xs uppercase tracking-wide text-ink/50">{label}</div>
      <div className="font-display text-2xl mt-1">{value}</div>
      <div className="text-xs text-ink/45 mt-1">{hint}</div>
    </div>
  );
}

function SignalList({ title, items }: { title: string; items: { symbol: string; signal: string; probability: number; expected_return: number }[] }) {
  return (
    <div>
      <h2 className="font-display text-2xl mb-3">{title}</h2>
      <ul className="space-y-2">
        {items.length === 0 && <li className="text-ink/50 text-sm">No signals yet — seed data and train models.</li>}
        {items.map((s) => (
          <li key={s.symbol} className="flex items-center justify-between border-b border-ink/10 py-2">
            <Link href={`/stocks/${s.symbol}`} className="font-medium hover:text-sea">
              {s.symbol}
            </Link>
            <span className="text-sm">
              {s.signal} · {(s.probability * 100).toFixed(0)}% · {(s.expected_return * 100).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
