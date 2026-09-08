# Research — Indian Equity Transaction Costs

**date_checked:** 2026-09-08  
**Segment focus:** Equity cash (delivery-oriented swing trades; configurable for intraday)

## Important disclaimer

Rates change with budgets, exchange circulars, and broker plans. Defaults below are **configurable assumptions** for research backtests, not legal advice. Always verify against current SEBI/exchange circulars and your broker contract note.

---

### Source 1 — Broker cost breakdowns (STT, stamp, GST, SEBI)

| Field | Value |
|-------|-------|
| **source** | Industry brokerage calculators / broker docs summarizing statutory charges (Zerodha-style contract note structure, Upstox calculator pages, SEBI fee notes) |
| **date_checked** | 2026-09-08 |
| **information_used** | Typical equity **delivery** stack: STT 0.1% buy + 0.1% sell; stamp duty ~0.015% buy only; SEBI turnover fee ~₹10/crore (0.0001%); GST 18% on (brokerage + exchange txn + SEBI); exchange txn charges ~0.00297% NSE CM (indicative); DP charges on delivery sell (broker-specific). Intraday: STT ~0.025% sell only; stamp ~0.003% buy. |
| **implementation_impact** | `TransactionCostModel` in backtesting uses these as defaults in `config/transaction_costs.yaml`. All knobs are env/config overridable. |

### Source 2 — SEBI turnover fee

| Field | Value |
|-------|-------|
| **source** | SEBI/exchange fee schedule summaries (₹10 per crore of turnover) |
| **date_checked** | 2026-09-08 |
| **information_used** | SEBI fee ≈ 0.0001% of turnover per side. |
| **implementation_impact** | Included in cost model; GST applied on brokerage + exchange + SEBI only (not on STT/stamp). |

## Default config (delivery swing)

```yaml
mode: delivery
brokerage_per_order: 20.0          # flat ₹/order assumption
brokerage_pct: 0.0
stt_buy_pct: 0.001                 # 0.1%
stt_sell_pct: 0.001
exchange_txn_pct: 0.0000297
sebi_fee_pct: 0.000001
stamp_duty_buy_pct: 0.00015
gst_pct: 0.18
dp_charge_sell: 15.93
slippage_bps: 5
spread_bps: 5
```

## Implementation notes

- Costs applied **at fill time** in the event-driven engine.  
- Slippage and half-spread are separate assumptions from statutory charges.  
- Round-trip cost is logged per trade for auditability.  
