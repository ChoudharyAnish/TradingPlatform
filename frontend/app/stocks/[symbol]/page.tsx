import { getPredictions, getPrices } from "@/lib/api";
import { PriceChart } from "@/components/PriceChart";

export const dynamic = "force-dynamic";

export default async function StockPage({ params }: { params: { symbol: string } }) {
  const symbol = params.symbol.toUpperCase();
  let bars: Awaited<ReturnType<typeof getPrices>>["bars"] = [];
  let pred: Awaited<ReturnType<typeof getPredictions>>["items"][0] | undefined;
  try {
    const [prices, preds] = await Promise.all([getPrices(symbol), getPredictions()]);
    bars = prices.bars.slice(-180);
    pred = preds.items.find((p) => p.symbol === symbol);
  } catch {
    /* empty */
  }

  return (
    <div className="space-y-8 animate-rise">
      <div>
        <h1 className="font-display text-4xl">{symbol}</h1>
        {pred && (
          <p className="mt-2 text-ink/70">
            {pred.signal} · {(pred.probability * 100).toFixed(0)}% · regime {pred.market_regime} · model{" "}
            {pred.model_version}
          </p>
        )}
      </div>
      <div className="rounded-xl border border-ink/10 bg-white/70 p-4 shadow-soft">
        <PriceChart bars={bars} />
      </div>
      {pred && (
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h2 className="font-display text-2xl mb-2">Trade plan</h2>
            <ul className="text-sm space-y-1 text-ink/80">
              <li>Entry: ₹{pred.current_price?.toFixed?.(2)}</li>
              <li>Stop: ₹{pred.stop_loss?.toFixed?.(2)}</li>
              <li>Target: ₹{pred.target_price?.toFixed?.(2)}</li>
              <li>R:R {pred.risk_reward?.toFixed?.(2)}</li>
              <li>Horizon: {pred.holding_period_days} days</li>
              <li>Channel: {pred.result_channel}</li>
            </ul>
          </div>
          <div>
            <h2 className="font-display text-2xl mb-2">Why (model features)</h2>
            <ul className="text-sm space-y-1">
              {(pred.explanations || []).map((e) => (
                <li key={e.feature} className={e.direction === "positive" ? "text-good" : "text-bad"}>
                  {e.direction === "positive" ? "+" : "-"} {e.feature} ({e.contribution.toFixed(3)})
                </li>
              ))}
              {!pred.explanations?.length && <li className="text-ink/50">Train a model to enable explanations.</li>}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
