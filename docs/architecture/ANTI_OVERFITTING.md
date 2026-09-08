# Anti-overfitting & leakage controls

| Risk | Prevention |
|------|------------|
| Look-ahead bias | Features use trailing windows only; targets are future-shifted and dropped at series end; backtest callbacks receive `trade_date` and must filter `<= d` |
| Train/test leakage | Chronological and walk-forward splits only; calibration fit on validation, never test |
| Survivorship bias | Universe filters applied with history requirements; sample set is fixed but production should use point-in-time membership |
| Data snooping | Model registry is append-only; warnings for excessive params / unstable OOS |
| Overfitting | Compare train vs test metrics; flag `OVERFITTING_RISK`, `LOW_SAMPLE_SIZE`, `UNSTABLE_PERFORMANCE`, `HIGH_DRAWDOWN`, `POOR_OUT_OF_SAMPLE_PERFORMANCE` |
| Regime fragility | Regime detector + metrics reported separately; strategies should condition on regime |
| Cost optimism | Configurable Indian statutory + slippage model applied at fill time |

A high historical return alone never promotes a model to `VALIDATED` / `PAPER_TRADING`.
