import Link from "next/link";
import { ReactNode } from "react";

const links = [
  { href: "/", label: "Home" },
  { href: "/predictions", label: "Predictions" },
  { href: "/screener", label: "Screener" },
  { href: "/backtests", label: "Backtests" },
  { href: "/models", label: "Models" },
  { href: "/portfolio", label: "Paper" },
  { href: "/quality", label: "Data Quality" },
];

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-ink/10 backdrop-blur bg-sand/70 sticky top-0 z-20">
        <div className="mx-auto max-w-7xl px-4 py-4 flex flex-wrap items-center justify-between gap-4">
          <Link href="/" className="font-display text-2xl tracking-tight text-ink">
            Indian Stock <span className="text-sea">AI</span>
          </Link>
          <nav className="flex flex-wrap gap-1 text-sm">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="px-3 py-1.5 rounded-md text-ink/80 hover:text-ink hover:bg-ink/5 transition"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
      <footer className="mx-auto max-w-7xl px-4 pb-10 text-xs text-ink/60">
        Research & paper-trading only. Backtested results are not guarantees of future performance. No live order
        execution in v1.
      </footer>
    </div>
  );
}
