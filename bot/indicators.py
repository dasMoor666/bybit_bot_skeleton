import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    # Standard-RSI (Wilder-Approx, hier mit Simple Moving Average)
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.rolling(length, min_periods=length).mean()
    avg_loss = loss.rolling(length, min_periods=length).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def atr_pct(df: pd.DataFrame, length: int = 14) -> pd.Series:
    # erwartet Spalten: high, low, close (float)
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)

    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    # True Range je Zeile (Pandas, nicht NumPy)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(length, min_periods=length).mean()
    return (atr / close) * 100.0


def volume_sma(df: pd.DataFrame, length: int = 10) -> pd.Series:
    return sma(df["volume"], length=length)


def compute_all(
    df: pd.DataFrame,
    ema_fast: int = 10,
    ema_slow: int = 30,
    rsi_len: int = 14,
    atr_len: int = 14,
    vol_len: int = 10,
) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = ema(out["close"], ema_fast)
    out["ema_slow"] = ema(out["close"], ema_slow)
    out["rsi"] = rsi(out["close"], rsi_len)
    out["atr_pct"] = atr_pct(out, atr_len)
    out["vol_sma"] = volume_sma(out, vol_len)
    return out