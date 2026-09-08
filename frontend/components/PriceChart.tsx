"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";
import type { Bar } from "@/lib/api";

export function PriceChart({ bars }: { bars: Bar[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !bars?.length) return;
    const chart = createChart(ref.current, {
      height: 360,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#0f2744",
      },
      grid: {
        vertLines: { color: "rgba(15,39,68,0.06)" },
        horzLines: { color: "rgba(15,39,68,0.06)" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#047857",
      downColor: "#b91c1c",
      borderVisible: false,
      wickUpColor: "#047857",
      wickDownColor: "#b91c1c",
    });
    series.setData(
      bars.map((b) => ({
        time: b.trade_date as unknown as string,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    );
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    });
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [bars]);

  return <div ref={ref} className="w-full animate-rise" />;
}
