"""Descarga de precios y cálculo de métricas. Fuente: Yahoo Finance vía yfinance."""
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yaml


@dataclass
class Metrics:
    last: float
    last_date: pd.Timestamp
    change_1w: Optional[float]  # % vs. cierre de hace 7 días (o anterior)
    change_1m: Optional[float]  # % vs. cierre de hace 30 días (o anterior)
    high_52w: float
    low_52w: float
    from_high_pct: float        # % respecto al máximo de 52 semanas (<= 0)


@dataclass
class Quote:
    symbol: str
    name: str
    metrics: Optional[Metrics] = None
    error: Optional[str] = None


def _pct(new: float, old: Optional[float]) -> Optional[float]:
    return (new / old - 1) * 100 if old else None


def _value_on_or_before(closes: pd.Series, date: pd.Timestamp) -> Optional[float]:
    prior = closes[closes.index <= date]
    return float(prior.iloc[-1]) if len(prior) else None


def compute_metrics(closes: pd.Series) -> Metrics:
    """Calcula métricas a partir de una serie de cierres diarios (índice = fechas)."""
    closes = closes.dropna()
    if closes.empty:
        raise ValueError("Serie de precios vacía")
    last_date = closes.index[-1]
    last = float(closes.iloc[-1])
    year = closes[closes.index > last_date - pd.Timedelta(days=365)]
    high, low = float(year.max()), float(year.min())
    return Metrics(
        last=last,
        last_date=last_date,
        change_1w=_pct(last, _value_on_or_before(closes, last_date - pd.Timedelta(days=7))),
        change_1m=_pct(last, _value_on_or_before(closes, last_date - pd.Timedelta(days=30))),
        high_52w=high,
        low_52w=low,
        from_high_pct=_pct(last, high),
    )


def fetch_quote(symbol: str, name: str) -> Quote:
    """Descarga 1 año de cierres diarios. Un fallo no debe tumbar todo el correo."""
    try:
        import yfinance as yf  # import diferido: los tests no lo necesitan

        hist = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=True)
        return Quote(symbol, name, metrics=compute_metrics(hist["Close"]))
    except Exception as exc:  # noqa: BLE001
        return Quote(symbol, name, error=f"{type(exc).__name__}: {exc}")


def load_config(path: str = "config.yml") -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def fetch_all(cfg: dict) -> dict:
    return {
        section: [fetch_quote(a["symbol"], a["name"]) for a in cfg.get(section, [])]
        for section in ("general", "watchlist")
    }
