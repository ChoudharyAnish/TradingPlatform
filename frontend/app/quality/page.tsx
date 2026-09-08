import { getDataQuality } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function QualityPage() {
  let rows: Awaited<ReturnType<typeof getDataQuality>> = [];
  try {
    rows = await getDataQuality();
  } catch {
    rows = [];
  }

  return (
    <div className="space-y-6 animate-rise">
      <h1 className="font-display text-4xl">Data quality</h1>
      <p className="text-ink/65">Automated checks for gaps, duplicates, impossible OHLC, volume spikes, and stale series.</p>
      <ul className="space-y-2 text-sm">
        {rows.map((r, i) => (
          <li key={i} className="border-b border-ink/10 py-2 flex gap-3">
            <span className={r.severity === "ERROR" ? "text-bad" : "text-alert"}>{r.severity}</span>
            <span className="font-medium">{r.check_type}</span>
            <span className="text-ink/70">{r.message}</span>
          </li>
        ))}
        {!rows.length && <li className="text-ink/50">No issues logged yet (or API offline).</li>}
      </ul>
    </div>
  );
}
