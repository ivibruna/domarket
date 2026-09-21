"""Datos ficticios para ver el diseño del correo sin conexión."""
import pandas as pd

from .data import Metrics, Quote

_DATE = pd.Timestamp("2026-09-25")


def _m(last, week, month, high, low) -> Metrics:
    return Metrics(last=last, last_date=_DATE, change_1w=week, change_1m=month,
                   high_52w=high, low_52w=low, from_high_pct=(last / high - 1) * 100)


def demo_data() -> dict:
    return {
        "general": [
            Quote("^IBEX", "IBEX 35", _m(10000.0, 1.2, -0.8, 11000.0, 8000.0)),
            Quote("^STOXX50E", "Euro Stoxx 50", _m(5000.0, 0.4, 1.9, 5200.0, 4300.0)),
            Quote("^GSPC", "S&P 500", _m(6000.0, -0.7, 2.5, 6200.0, 5000.0)),
            Quote("CL=F", "Petróleo WTI", _m(70.0, -2.3, -4.1, 85.0, 60.0)),
            Quote("BZ=F", "Petróleo Brent", _m(74.0, -2.1, -3.8, 88.0, 63.0)),
            Quote("GC=F", "Oro", _m(3000.0, 0.9, 3.2, 3100.0, 2200.0)),
            Quote("BTC-EUR", "Bitcoin (EUR)", _m(60000.0, 4.8, -6.2, 90000.0, 40000.0)),
            Quote("EURUSD=X", "EUR/USD", _m(1.1, 0.0, 0.3, 1.2, 1.0)),
        ],
        "watchlist": [
            Quote("NXT.MC", "Nueva Expresión Textil", _m(1.0, -3.5, 2.1, 1.2, 0.7)),
        ],
    }
