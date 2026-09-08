import { getModels } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  let models: Awaited<ReturnType<typeof getModels>> = [];
  try {
    models = await getModels();
  } catch {
    models = [];
  }

  return (
    <div className="space-y-6 animate-rise">
      <h1 className="font-display text-4xl">Model registry</h1>
      <p className="text-ink/65 max-w-2xl">
        Statuses: EXPERIMENTAL → VALIDATED → PAPER_TRADING → RETIRED. Only validated / paper-trading models should drive
        production signals. Warnings flag overfitting and fragile OOS performance.
      </p>
      <div className="space-y-4">
        {models.map((m) => (
          <article key={m.model_id} className="rounded-xl border border-ink/10 bg-white/70 p-4">
            <div className="flex flex-wrap justify-between gap-2">
              <h2 className="font-display text-xl">{m.model_id}</h2>
              <span className="text-xs uppercase tracking-wide text-sea">{m.status}</span>
            </div>
            <p className="text-sm text-ink/60 mt-1">
              {m.model_type} · trained {new Date(m.training_date).toLocaleString()}
            </p>
            <div className="grid md:grid-cols-2 gap-3 mt-3 text-xs">
              <pre className="bg-mist/50 p-2 rounded">{JSON.stringify(m.validation_metrics, null, 2)}</pre>
              <pre className="bg-mist/50 p-2 rounded">{JSON.stringify(m.test_metrics, null, 2)}</pre>
            </div>
            <p className="text-sm mt-2 text-alert">Warnings: {(m.warnings || []).join(", ") || "none"}</p>
            <p className="text-xs text-ink/45 mt-1">Features: {m.features?.slice(0, 8).join(", ")}…</p>
          </article>
        ))}
        {!models.length && <p className="text-ink/50">No models yet. Run seed/train.</p>}
      </div>
    </div>
  );
}
