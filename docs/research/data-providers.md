# Research — Indian Equity Data Providers

**date_checked:** 2026-09-08

## Summary

Production historical equity data for NSE/BSE is available via (a) official paid NSE EOD/historical products, (b) broker/vendor APIs, and (c) unofficial public scrapers. For this research platform we prefer **provider interfaces + sample CSV + optional Yahoo Finance**, with stubs for official/broker adapters.

---

### Source 1 — NSE Paid EOD / Historical Data

| Field | Value |
|-------|-------|
| **source** | https://www.nseindia.com/static/market-data/eod-historical-data-subscription |
| **date_checked** | 2026-09-08 |
| **information_used** | NSE offers paid End-of-Day and historical order/trade data via SFTP/online platform for CM, F&O, CD, COM. Contact: marketdata@nse.co.in |
| **implementation_impact** | Official commercial source for production. Implemented as `NseOfficialProvider` stub requiring credentials. Not default for open-source demo. |

### Source 2 — NSE Historical Price/Volume UI

| Field | Value |
|-------|-------|
| **source** | https://www.nseindia.com/historical/price-and-volume-data-per-security |
| **date_checked** | 2026-09-08 |
| **information_used** | Manual CSV download of security price/volume history from NSE site. |
| **implementation_impact** | Supports offline ingest path (`scripts/import_nse_csv.py`). Not a stable unattended API. |

### Source 3 — NSE Index Historical Data

| Field | Value |
|-------|-------|
| **source** | https://www.nseindia.com/reports-indices-historical-index-data |
| **date_checked** | 2026-09-08 |
| **information_used** | Official index historical CSV downloads (NIFTY 50, Bank Nifty, etc.). |
| **implementation_impact** | Index series used for regime detection and buy-and-hold benchmarks. |

### Source 4 — NSE Trading Holidays

| Field | Value |
|-------|-------|
| **source** | https://www.nseindia.com/resources/exchange-communication-holidays |
| **date_checked** | 2026-09-08 |
| **information_used** | Exchange holiday calendar; note on Muhurat trading (e.g. Diwali). |
| **implementation_impact** | Trading calendar module must exclude weekends + listed holidays; Muhurat days configurable. |

### Source 5 — Community/archive libraries (secondary)

| Field | Value |
|-------|-------|
| **source** | PyPI `nse-archives`, `nselib`; GitHub `aynse` |
| **date_checked** | 2026-09-08 |
| **information_used** | Unofficial helpers around NSE public/archive endpoints. Not exchange-endorsed. |
| **implementation_impact** | Optional adapters only; not default. Prefer official paid data for production. |

### Source 6 — Yahoo Finance (optional convenience)

| Field | Value |
|-------|-------|
| **source** | Yahoo Finance via `yfinance` (symbols like `RELIANCE.NS`) |
| **date_checked** | 2026-09-08 |
| **information_used** | Convenient adjusted OHLCV for many NSE listings; not an exchange primary source; may have gaps/delays/corporate-action quirks. |
| **implementation_impact** | `YahooFinanceProvider` behind feature flag for research ingest. Sample CSV remains CI source of truth. |

## Chosen default stack

1. **CSVSampleProvider** — deterministic demo + CI  
2. **YahooFinanceProvider** — optional research ingest  
3. **NseOfficialProvider / BrokerAdapter** — stubs with clear TODOs  

## Missing external dependencies (to obtain for production)

- NSE EOD subscription credentials (or licensed vendor feed)  
- Broker API keys if live trading is added later  
- Optional news API (e.g. licensed Indian financial news) for sentiment  
- Optional fundamentals vendor (exchange filings / licensed fundamentals)  
