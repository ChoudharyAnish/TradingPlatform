# Missing External Dependencies

**date_checked:** 2026-09-08

| Dependency | Why needed | Status in v1 |
|------------|------------|--------------|
| NSE paid EOD / historical SFTP | Authoritative exchange prices | Stub `NseOfficialProvider` |
| Licensed fundamentals feed | PE/PB/ROE etc. point-in-time | Null provider; schema ready |
| Licensed news / sentiment | Reliable sentiment features | Null provider; schema ready |
| Broker API (Zerodha/others) | Live orders later | `LiveBrokerAdapter` stub only |
| Production Postgres + Redis | Persistence / jobs | Docker Compose provided |
| Calibrated production models | Real signals | Train on sample / your data |

Until official feeds are configured, use `csv_sample` or optional Yahoo for research only.
