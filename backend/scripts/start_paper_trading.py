"""Start / demo paper trading session from latest signals."""

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.portfolio.paper import PaperBroker, PaperOrder
from app.services.market import prices_frame
from app.services.predictions import generate_predictions


def main():
    db = SessionLocal()
    broker = PaperBroker()
    signals = generate_predictions(db)
    print("result_channel=PAPER")
    print("disclaimer: Paper trading is simulated. Not live market execution.")
    for sig in signals:
        if sig["signal"] in {"BUY", "STRONG BUY"} and sig["probability"] >= 0.55:
            df = prices_frame(db, sig["symbol"])
            if df.empty:
                continue
            px = float(df.iloc[-1]["close"])
            qty = max(1, int((get_settings().initial_capital * sig["position_size_pct"]) // px))
            fill = broker.place_order(
                PaperOrder(
                    symbol=sig["symbol"],
                    side="BUY",
                    qty=qty,
                    stop_loss=sig["stop_loss"],
                    take_profit=sig["target_price"],
                ),
                px,
            )
            print(fill)
    marks = {s: float(prices_frame(db, s).iloc[-1]["close"]) for s in broker.account.positions}
    print(broker.snapshot(marks))
    db.close()


if __name__ == "__main__":
    main()
