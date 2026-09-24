#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_GOLD_BOT_MONITOR_ENGINE.py
=============================

Gold Trading & Compounding Accumulation System — monitoring daemon and Telegram alerting bot.

Pipeline (one cycle):

    OHLCV provider ──► schema validation ──► indicators (Wilder RSI14, EMA50/200, ATR14, 4H regime)
         ──► divergence engine (scipy.signal.find_peaks, dual direction, freshness filter)
         ──► debounce / state store ──► in-memory mplfinance chart (io.BytesIO)
         ──► Telegram sendPhoto with Markdown caption

Signal rules (1H timeframe):

    Bearish divergence : price2 >= price1 * 0.999  (higher / equal high)
                         rsi2   <  rsi1            (lower RSI high)
                         rsi2   >= 55.0            (exhaustion band)
    Bullish divergence : price2 <= price1 * 1.001  (lower / equal low)
                         rsi2   >  rsi1            (higher RSI low)
                         rsi2   <= 35.0 and rsi1 < 30.0
    Freshness          : the second pivot must be confirmed within the last 3 closed candles.

Data sources:

    simulated     Seeded synthetic 1H gold series that advances one candle per poll (default).
    csv           Local CSV with columns timestamp,open,high,low,close[,volume].
    binance_paxg  Public Binance PAXGUSDT 1H klines (PAX Gold, 1 token = 1 troy oz), used as a
                  keyless proxy for spot XAU/USD. No API key required.

Usage:

    python 04_GOLD_BOT_MONITOR_ENGINE.py --self-test
    python 04_GOLD_BOT_MONITOR_ENGINE.py --once --dry-run
    TELEGRAM_BOT_TOKEN=<token> TELEGRAM_CHAT_ID=<chat_id> python 04_GOLD_BOT_MONITOR_ENGINE.py --source binance_paxg

Every setting can be supplied as an environment variable (see Config.from_env) and most can be
overridden on the command line (see build_arg_parser).

This software produces technical-analysis notifications. It is not investment advice.
"""

from __future__ import annotations

import argparse
import dataclasses
import io
import json
import logging
import math
import os
import signal
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")  # headless backend: the daemon never opens a window

import matplotlib.pyplot as plt  # noqa: E402
import mplfinance as mpf  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402
from scipy.signal import find_peaks  # noqa: E402

__version__ = "1.0.0"

LOG = logging.getLogger("gold_bot")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)  # silence font-weight fallback noise

OHLCV_COLUMNS: Tuple[str, ...] = ("open", "high", "low", "close", "volume")
TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_CAPTION_LIMIT = 1024
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# ════════════════════════════════════════════════════════════════════════════════════════════
# Configuration
# ════════════════════════════════════════════════════════════════════════════════════════════


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value.strip() == "" else value.strip()


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name}={raw!r} is not a valid number") from exc


def _env_optional_float(name: str) -> Optional[float]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name}={raw!r} is not a valid number") from exc


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name}={raw!r} is not a valid integer") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y"}


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration. Build with Config.from_env() and override via replace()."""

    # Telegram
    telegram_token: str = ""
    telegram_chat_id: str = ""
    dry_run: bool = False

    # Market data
    data_source: str = "simulated"
    csv_path: str = "gold_1h.csv"
    symbol_label: str = "XAU/USD"
    history_bars: int = 500
    min_bars: int = 250
    poll_seconds: float = 60.0
    request_timeout: float = 15.0
    sim_seed: int = 20260924
    sim_start_price: float = 4300.0

    # Position / currency
    position_oz: float = 0.10
    entry_price: Optional[float] = None
    usd_thb: float = 32.50
    profit_targets_pct: Tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)

    # Indicators
    rsi_period: int = 14
    ema_fast: int = 50
    ema_slow: int = 200
    atr_period: int = 14

    # Divergence engine
    pivot_distance: int = 5
    pivot_prominence_atr: float = 0.6
    min_pivot_gap: int = 5
    max_pivot_gap: int = 40
    rsi_pivot_window: int = 2
    freshness_bars: int = 3
    bear_price_tolerance: float = 0.999
    bull_price_tolerance: float = 1.001
    bear_rsi_min: float = 55.0
    bull_rsi_max: float = 35.0
    bull_prior_rsi_max: float = 30.0

    # Charting
    chart_bars: int = 60
    chart_dpi: int = 110
    display_tz: str = "Asia/Bangkok"

    # State / debounce
    state_path: str = "gold_bot_state.json"
    alert_cooldown_minutes: float = 180.0
    state_retention_days: float = 14.0

    # Loop resilience
    max_backoff_seconds: float = 900.0

    @classmethod
    def from_env(cls) -> "Config":
        targets_raw = _env_str("PROFIT_TARGETS_PCT", "1.0,1.5,2.0,3.0")
        try:
            targets = tuple(float(x) for x in targets_raw.split(",") if x.strip())
        except ValueError as exc:
            raise ValueError(f"PROFIT_TARGETS_PCT={targets_raw!r} must be comma-separated numbers") from exc
        return cls(
            telegram_token=_env_str("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=_env_str("TELEGRAM_CHAT_ID", ""),
            dry_run=_env_bool("DRY_RUN", False),
            data_source=_env_str("DATA_SOURCE", "simulated").lower(),
            csv_path=_env_str("CSV_PATH", "gold_1h.csv"),
            symbol_label=_env_str("SYMBOL_LABEL", "XAU/USD"),
            history_bars=_env_int("HISTORY_BARS", 500),
            min_bars=_env_int("MIN_BARS", 250),
            poll_seconds=_env_float("POLL_SECONDS", 60.0),
            request_timeout=_env_float("REQUEST_TIMEOUT", 15.0),
            sim_seed=_env_int("SIM_SEED", 20260924),
            sim_start_price=_env_float("SIM_START_PRICE", 4300.0),
            position_oz=_env_float("POSITION_OZ", 0.10),
            entry_price=_env_optional_float("ENTRY_PRICE"),
            usd_thb=_env_float("USD_THB", 32.50),
            profit_targets_pct=targets,
            rsi_period=_env_int("RSI_PERIOD", 14),
            ema_fast=_env_int("EMA_FAST", 50),
            ema_slow=_env_int("EMA_SLOW", 200),
            atr_period=_env_int("ATR_PERIOD", 14),
            pivot_distance=_env_int("PIVOT_DISTANCE", 5),
            pivot_prominence_atr=_env_float("PIVOT_PROMINENCE_ATR", 0.6),
            min_pivot_gap=_env_int("MIN_PIVOT_GAP", 5),
            max_pivot_gap=_env_int("MAX_PIVOT_GAP", 40),
            rsi_pivot_window=_env_int("RSI_PIVOT_WINDOW", 2),
            freshness_bars=_env_int("FRESHNESS_BARS", 3),
            bear_rsi_min=_env_float("BEAR_RSI_MIN", 55.0),
            bull_rsi_max=_env_float("BULL_RSI_MAX", 35.0),
            bull_prior_rsi_max=_env_float("BULL_PRIOR_RSI_MAX", 30.0),
            chart_bars=_env_int("CHART_BARS", 60),
            chart_dpi=_env_int("CHART_DPI", 110),
            display_tz=_env_str("DISPLAY_TZ", "Asia/Bangkok"),
            state_path=_env_str("STATE_PATH", "gold_bot_state.json"),
            alert_cooldown_minutes=_env_float("ALERT_COOLDOWN_MINUTES", 180.0),
            state_retention_days=_env_float("STATE_RETENTION_DAYS", 14.0),
            max_backoff_seconds=_env_float("MAX_BACKOFF_SECONDS", 900.0),
        )

    def validate(self) -> None:
        errors: List[str] = []
        if self.data_source not in {"simulated", "csv", "binance_paxg"}:
            errors.append(f"data_source must be simulated|csv|binance_paxg, got {self.data_source!r}")
        if self.rsi_period < 2:
            errors.append("rsi_period must be >= 2")
        if not (0 < self.ema_fast < self.ema_slow):
            errors.append("ema_fast must be positive and smaller than ema_slow")
        if self.history_bars < self.min_bars:
            errors.append("history_bars must be >= min_bars")
        if self.min_bars < self.ema_slow:
            errors.append("min_bars must be >= ema_slow so EMA200 is meaningful")
        if self.chart_bars < 20 or self.chart_bars > self.history_bars:
            errors.append("chart_bars must be between 20 and history_bars")
        if self.freshness_bars < 1:
            errors.append("freshness_bars must be >= 1")
        if not (1 <= self.min_pivot_gap < self.max_pivot_gap):
            errors.append("min_pivot_gap must be >= 1 and smaller than max_pivot_gap")
        if self.max_pivot_gap + self.freshness_bars + 2 * self.rsi_pivot_window >= self.chart_bars:
            errors.append("chart_bars must exceed max_pivot_gap + freshness_bars so both pivots are plotted")
        if self.position_oz < 0:
            errors.append("position_oz must be >= 0")
        if self.entry_price is not None and self.entry_price <= 0:
            errors.append("entry_price must be positive when set")
        if self.usd_thb <= 0:
            errors.append("usd_thb must be positive")
        if self.poll_seconds <= 0:
            errors.append("poll_seconds must be positive")
        try:
            ZoneInfo(self.display_tz)
        except Exception:  # noqa: BLE001 - ZoneInfo raises several unrelated exception types
            errors.append(f"display_tz {self.display_tz!r} is not a valid IANA time zone")
        if errors:
            raise ValueError("Invalid configuration:\n  - " + "\n  - ".join(errors))

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.telegram_chat_id) and not self.dry_run


class DataError(RuntimeError):
    """Raised when market data is missing, malformed, or violates the OHLCV data contract."""


class DispatchError(RuntimeError):
    """Raised when a Telegram message cannot be delivered after all retries."""


# ════════════════════════════════════════════════════════════════════════════════════════════
# Data contract
# ════════════════════════════════════════════════════════════════════════════════════════════


def validate_ohlcv(df: pd.DataFrame, min_bars: int) -> pd.DataFrame:
    """Enforce the OHLCV data contract and return a clean float64 copy.

    Contract: tz-aware UTC DatetimeIndex, strictly increasing and unique; float64 columns
    open/high/low/close/volume; no NaN; high >= max(open, close); low <= min(open, close).
    """
    if not isinstance(df, pd.DataFrame):
        raise DataError("OHLCV payload is not a pandas DataFrame")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataError("OHLCV index must be a pandas DatetimeIndex")
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise DataError(f"OHLCV frame missing columns: {missing}")

    out = df.loc[:, list(OHLCV_COLUMNS)].astype("float64").copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out.index.name = "timestamp"

    if out.index.has_duplicates:
        out = out[~out.index.duplicated(keep="last")]
    if not out.index.is_monotonic_increasing:
        out = out.sort_index()
    if out.isna().any().any():
        bad = int(out.isna().any(axis=1).sum())
        raise DataError(f"OHLCV frame contains {bad} rows with NaN values")
    if (out[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataError("OHLCV prices must be strictly positive")
    body_high = out[["open", "close"]].max(axis=1)
    body_low = out[["open", "close"]].min(axis=1)
    if (out["high"] + 1e-9 < body_high).any() or (out["low"] - 1e-9 > body_low).any():
        raise DataError("OHLCV integrity violated: high/low do not bracket open/close")
    if len(out) < min_bars:
        raise DataError(f"Need at least {min_bars} bars, received {len(out)}")
    return out


# ════════════════════════════════════════════════════════════════════════════════════════════
# Market data providers
# ════════════════════════════════════════════════════════════════════════════════════════════


def _floor_hour_utc(ts: Optional[datetime] = None) -> pd.Timestamp:
    now = pd.Timestamp(ts or datetime.now(timezone.utc))
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    return now.tz_convert("UTC").floor("h")


def _ohlc_from_closes(
    closes: np.ndarray, rng: np.random.Generator, wick_scale: float, start_open: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Derive open/high/low/volume from a close path with realistic wicks."""
    opens = np.empty_like(closes)
    opens[0] = start_open
    opens[1:] = closes[:-1]
    body_high = np.maximum(opens, closes)
    body_low = np.minimum(opens, closes)
    upper = np.abs(rng.normal(0.0, wick_scale, size=closes.size))
    lower = np.abs(rng.normal(0.0, wick_scale, size=closes.size))
    highs = body_high + upper
    lows = body_low - lower
    ranges = highs - lows
    volume = np.round(800.0 + 60.0 * ranges / max(wick_scale, 1e-9) + rng.gamma(2.0, 150.0, size=closes.size))
    return opens, highs, lows, volume


def generate_simulated_ohlcv(
    bars: int,
    start_price: float = 4300.0,
    seed: int = 20260924,
    end: Optional[pd.Timestamp] = None,
    hourly_vol: float = 0.0022,
) -> pd.DataFrame:
    """Generate a seeded 1H gold OHLCV history with swing structure.

    The close path is a regime-switching mean-reverting process: a slowly drifting anchor
    (trend) plus an Ornstein-Uhlenbeck swing component, which produces the alternating
    impulse/pullback structure that divergence detection needs. Hourly volatility defaults
    to 0.22%, close to realised 1H volatility of spot gold.
    """
    if bars < 2:
        raise ValueError("bars must be >= 2")
    rng = np.random.default_rng(seed)
    end_ts = _floor_hour_utc() if end is None else pd.Timestamp(end).tz_convert("UTC").floor("h")
    index = pd.date_range(end=end_ts, periods=bars, freq="h", tz="UTC", name="timestamp")

    log_anchor = math.log(start_price)
    swing = 0.0
    drift = 0.0
    closes = np.empty(bars)
    for i in range(bars):
        if i % 36 == 0:
            drift = rng.normal(0.0, 0.00035)
        log_anchor += drift
        swing = 0.90 * swing + rng.normal(0.0, hourly_vol)
        closes[i] = math.exp(log_anchor + swing)
    opens, highs, lows, volume = _ohlc_from_closes(closes, rng, start_price * hourly_vol * 0.35, start_price)
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volume}, index=index
    )


def build_divergence_scenario(kind: str, bars: int = 320, base: float = 4300.0, seed: int = 7) -> pd.DataFrame:
    """Build a deterministic 1H series that ends with a textbook divergence (for self-tests).

    BULLISH: sharp flush into an oversold trough (RSI < 30), relief rally, choppy grind to a marginal
             lower low with a higher RSI trough (<= 35), then two confirming up-candles.
    BEARISH: strong impulse into an overbought peak, pullback, choppy grind to a marginal higher
             high with a lower RSI peak (>= 55), then two confirming down-candles.

    The lead-in is a mean-reverting range around `base` so RSI starts near 50.
    """
    kind = kind.upper()
    if kind not in {"BULLISH", "BEARISH"}:
        raise ValueError("kind must be BULLISH or BEARISH")
    rng = np.random.default_rng(seed)
    sign = -1.0 if kind == "BULLISH" else 1.0

    # (bars, total % move, alternating chop %). The last segment leaves pivot 2 two bars from the end.
    segments: List[Tuple[int, float, float]] = [
        (12, sign * 1.20, 0.03),   # impulse into first pivot -> extreme RSI
        (7, -sign * 0.70, 0.03),   # counter-move / relief
        (12, sign * 1.10, 0.16),   # choppy grind to a marginal new extreme -> weaker RSI
        (2, -sign * 0.25, 0.00),   # confirmation candles
    ]
    tail_len = sum(n for n, _, _ in segments)
    lead_len = bars - tail_len
    if lead_len < 250:
        raise ValueError("bars too small for scenario (need >= 250 lead-in bars)")

    x = 0.0
    lead = np.empty(lead_len)
    for i in range(lead_len):
        x = 0.85 * x + rng.normal(0.0, 0.0012)
        lead[i] = base * math.exp(x)
    lead *= base / lead[-1]

    returns: List[float] = []
    for n, pct, chop in segments:
        drift = math.log1p(pct / 100.0) / n
        for j in range(n):
            # Chop alternates against the drift first, and the final bar of a segment is always
            # clean so the segment ends exactly on its extreme.
            wiggle = 0.0 if j == n - 1 else (chop / 100.0) * (1.0 if j % 2 else -1.0) * np.sign(drift)
            returns.append(drift + wiggle)
    closes_tail = lead[-1] * np.exp(np.cumsum(returns))
    closes = np.concatenate([lead, closes_tail])

    end = pd.Timestamp("2026-09-24 10:00", tz="UTC")
    index = pd.date_range(end=end, periods=closes.size, freq="h", tz="UTC", name="timestamp")
    opens, highs, lows, volume = _ohlc_from_closes(closes, rng, base * 0.0003, closes[0])
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volume}, index=index)


class SimulatedProvider:
    """Stateful synthetic feed: seeds history once, then appends one new candle per fetch()."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self._rng = np.random.default_rng(cfg.sim_seed + 1)
        self._df = generate_simulated_ohlcv(cfg.history_bars, cfg.sim_start_price, cfg.sim_seed)
        self._swing = 0.0
        self._anchor = math.log(float(self._df["close"].iloc[-1]))
        self._fetches = 0

    def fetch(self) -> pd.DataFrame:
        if self._fetches > 0:
            self._append_bar()
        self._fetches += 1
        return self._df.copy()

    def _append_bar(self) -> None:
        last = self._df.iloc[-1]
        self._anchor += self._rng.normal(0.0, 0.00035)
        self._swing = 0.90 * self._swing + self._rng.normal(0.0, 0.0022)
        close = math.exp(self._anchor + self._swing)
        open_ = float(last["close"])
        wick = self.cfg.sim_start_price * 0.0022 * 0.35
        high = max(open_, close) + abs(self._rng.normal(0.0, wick))
        low = min(open_, close) - abs(self._rng.normal(0.0, wick))
        volume = round(800.0 + 60.0 * (high - low) / wick + self._rng.gamma(2.0, 150.0))
        ts = self._df.index[-1] + pd.Timedelta(hours=1)
        row = pd.DataFrame(
            {"open": [open_], "high": [high], "low": [low], "close": [close], "volume": [float(volume)]},
            index=pd.DatetimeIndex([ts], name="timestamp"),
        )
        self._df = pd.concat([self._df, row]).iloc[-self.cfg.history_bars:]


class CSVProvider:
    """Reads a local CSV (timestamp,open,high,low,close[,volume]); re-read every cycle."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def fetch(self) -> pd.DataFrame:
        path = self.cfg.csv_path
        if not os.path.isfile(path):
            raise DataError(f"CSV file not found: {path}")
        raw = pd.read_csv(path)
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        ts_col = next((c for c in ("timestamp", "datetime", "date", "time") if c in raw.columns), None)
        if ts_col is None:
            raise DataError("CSV must contain a timestamp/datetime/date/time column")
        if "volume" not in raw.columns:
            raw["volume"] = 0.0
        raw.index = pd.to_datetime(raw[ts_col], utc=True)
        return raw.drop(columns=[ts_col]).iloc[-self.cfg.history_bars:]


class BinancePAXGProvider:
    """Public Binance PAXGUSDT 1H klines. Drops the still-forming candle."""

    def __init__(self, cfg: Config, session: Optional[requests.Session] = None) -> None:
        self.cfg = cfg
        self.session = session or requests.Session()

    def fetch(self) -> pd.DataFrame:
        params = {"symbol": "PAXGUSDT", "interval": "1h", "limit": min(1000, self.cfg.history_bars + 1)}
        resp = self.session.get(BINANCE_KLINES_URL, params=params, timeout=self.cfg.request_timeout)
        if resp.status_code != 200:
            raise DataError(f"Binance klines HTTP {resp.status_code}: {resp.text[:200]}")
        rows = resp.json()
        if not isinstance(rows, list) or not rows:
            raise DataError("Binance klines returned an empty or malformed payload")
        now_ms = int(time.time() * 1000)
        closed = [r for r in rows if int(r[6]) < now_ms]  # r[6] = close time (ms)
        frame = pd.DataFrame(
            {
                "open": [float(r[1]) for r in closed],
                "high": [float(r[2]) for r in closed],
                "low": [float(r[3]) for r in closed],
                "close": [float(r[4]) for r in closed],
                "volume": [float(r[5]) for r in closed],
            },
            index=pd.to_datetime([int(r[0]) for r in closed], unit="ms", utc=True),
        )
        return frame.iloc[-self.cfg.history_bars:]


def build_provider(cfg: Config):
    if cfg.data_source == "simulated":
        return SimulatedProvider(cfg)
    if cfg.data_source == "csv":
        return CSVProvider(cfg)
    if cfg.data_source == "binance_paxg":
        return BinancePAXGProvider(cfg)
    raise ValueError(f"Unknown data source {cfg.data_source!r}")


# ════════════════════════════════════════════════════════════════════════════════════════════
# Indicators
# ════════════════════════════════════════════════════════════════════════════════════════════


def wilder_smooth(values: pd.Series, period: int, skip_first: bool = True) -> pd.Series:
    """Wilder's smoothing (RMA): SMA seed, then an EMA with alpha = 1/period.

    RMA_t = RMA_{t-1} + (x_t - RMA_{t-1}) / period  ==  EMA(alpha=1/period, adjust=False).

    skip_first=True treats element 0 as undefined (a diff() artefact, as for RSI gains/losses), so
    the seed is mean(values[1..period]) placed at index `period`. skip_first=False (ATR) seeds with
    mean(values[0..period-1]) at index `period - 1`. Output is NaN before the seed.
    """
    arr = values.to_numpy(dtype="float64")
    start = 1 if skip_first else 0
    seed_idx = start + period - 1
    out = pd.Series(np.nan, index=values.index, dtype="float64")
    if arr.size <= seed_idx:
        return out
    seeded = np.full(arr.size, np.nan)
    seeded[seed_idx] = arr[start : seed_idx + 1].mean()
    seeded[seed_idx + 1 :] = arr[seed_idx + 1 :]
    smoothed = pd.Series(seeded, index=values.index).ewm(alpha=1.0 / period, adjust=False).mean()
    out.iloc[seed_idx:] = smoothed.iloc[seed_idx:].to_numpy()
    return out


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Exact Wilder RSI: RSI = 100 - 100 / (1 + RMA(gain) / RMA(loss))."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = wilder_smooth(gain, period)
    avg_loss = wilder_smooth(loss, period)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
        rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    rsi = rsi.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    rsi[avg_gain.isna() | avg_loss.isna()] = np.nan
    return rsi.rename(f"rsi{period}")


def wilder_rsi_reference(close: Sequence[float], period: int = 14) -> np.ndarray:
    """Loop-based textbook Wilder RSI, used by the self-test to verify the vectorised version."""
    c = np.asarray(close, dtype="float64")
    out = np.full(c.size, np.nan)
    if c.size <= period:
        return out
    d = np.diff(c)
    g = np.where(d > 0, d, 0.0)
    l_ = np.where(d < 0, -d, 0.0)
    ag = g[:period].mean()
    al = l_[:period].mean()
    for i in range(period, c.size):
        if i > period:
            ag = (ag * (period - 1) + g[i - 1]) / period
            al = (al * (period - 1) + l_[i - 1]) / period
        if al == 0.0:
            out[i] = 50.0 if ag == 0.0 else 100.0
        else:
            out[i] = 100.0 - 100.0 / (1.0 + ag / al)
    return out


def ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean().rename(f"ema{span}")


def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1
    ).max(axis=1)
    tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
    return wilder_smooth(tr, period, skip_first=False).rename(f"atr{period}")


def compute_indicators(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    out = df.copy()
    out["rsi"] = wilder_rsi(out["close"], cfg.rsi_period)
    out["ema_fast"] = ema(out["close"], cfg.ema_fast)
    out["ema_slow"] = ema(out["close"], cfg.ema_slow)
    out["atr"] = wilder_atr(out, cfg.atr_period)
    return out


@dataclass(frozen=True)
class RegimeContext:
    """Higher-timeframe (4H) context for Cardwell/Brown range rules and conflict resolution."""

    rsi_4h: float
    regime: str          # BULL_RANGE | BEAR_RANGE | TRANSITION
    trend_1h: str        # UPTREND | DOWNTREND | MIXED (EMA50 vs EMA200 and price location)


def classify_regime(df_ind: pd.DataFrame, cfg: Config) -> RegimeContext:
    """Resample closed 1H candles to 4H and classify the RSI range regime.

    Cardwell / Brown range rules: in bull markets RSI(14) oscillates ~40-80 (40-50 is support);
    in bear markets ~20-60 (55-65 is resistance). Over the last 30 4H bars: min >= 40 -> BULL_RANGE,
    max <= 60 -> BEAR_RANGE, otherwise TRANSITION.
    """
    four_h = (
        df_ind[["open", "high", "low", "close"]]
        .resample("4h", label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )
    rsi_4h = wilder_rsi(four_h["close"], cfg.rsi_period).dropna()
    if rsi_4h.empty:
        regime, rsi_now = "TRANSITION", float("nan")
    else:
        window = rsi_4h.iloc[-30:]
        rsi_now = float(rsi_4h.iloc[-1])
        if window.min() >= 40.0:
            regime = "BULL_RANGE"
        elif window.max() <= 60.0:
            regime = "BEAR_RANGE"
        else:
            regime = "TRANSITION"
    last = df_ind.iloc[-1]
    if last["ema_fast"] > last["ema_slow"] and last["close"] > last["ema_fast"]:
        trend = "UPTREND"
    elif last["ema_fast"] < last["ema_slow"] and last["close"] < last["ema_fast"]:
        trend = "DOWNTREND"
    else:
        trend = "MIXED"
    return RegimeContext(rsi_4h=rsi_now, regime=regime, trend_1h=trend)


# ════════════════════════════════════════════════════════════════════════════════════════════
# Divergence engine
# ════════════════════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Divergence:
    kind: str                    # "BEARISH" | "BULLISH"
    idx1: int
    idx2: int
    t1: pd.Timestamp
    t2: pd.Timestamp
    price1: float
    price2: float
    rsi_idx1: int
    rsi_idx2: int
    rsi_t1: pd.Timestamp
    rsi_t2: pd.Timestamp
    rsi1: float
    rsi2: float
    bars_since_pivot: int

    @property
    def key(self) -> str:
        """Debounce key: one alert per (direction, second pivot candle)."""
        return f"{self.kind}:{self.t2.isoformat()}"


def _rsi_extreme(rsi: np.ndarray, center: int, window: int, last_idx: int, use_max: bool) -> Tuple[int, float]:
    lo = max(0, center - window)
    hi = min(last_idx, center + window)
    seg = rsi[lo : hi + 1]
    if np.all(np.isnan(seg)):
        return center, float("nan")
    rel = int(np.nanargmax(seg) if use_max else np.nanargmin(seg))
    return lo + rel, float(seg[rel])


class DivergenceEngine:
    """Dual-direction RSI divergence detector built on scipy.signal.find_peaks."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def _prominence(self, df: pd.DataFrame) -> float:
        atr = df["atr"].dropna()
        if atr.empty:
            return 0.0
        return float(atr.iloc[-100:].median() * self.cfg.pivot_prominence_atr)

    def find_pivots(self, df: pd.DataFrame, kind: str) -> np.ndarray:
        """Indices of confirmed swing highs (BEARISH) or swing lows (BULLISH).

        Troughs are found by inverting the low array (-low), turning minima into maxima so the
        same find_peaks call detects both directions.
        """
        series = df["high"].to_numpy() if kind == "BEARISH" else -df["low"].to_numpy()
        peaks, _ = find_peaks(series, distance=self.cfg.pivot_distance, prominence=self._prominence(df))
        rsi = df["rsi"].to_numpy()
        return peaks[~np.isnan(rsi[peaks])]

    def detect(self, df: pd.DataFrame, kind: str) -> Optional[Divergence]:
        cfg = self.cfg
        pivots = self.find_pivots(df, kind)
        if pivots.size < 2:
            return None
        last_idx = len(df) - 1
        p2 = int(pivots[-1])
        bars_since = last_idx - p2
        # find_peaks never marks the final bar, so bars_since >= 1 guarantees >= 1 confirming candle.
        if bars_since < 1 or bars_since > cfg.freshness_bars:
            return None

        is_bear = kind == "BEARISH"
        prices = df["high"].to_numpy() if is_bear else df["low"].to_numpy()
        rsi = df["rsi"].to_numpy()
        price2 = float(prices[p2])
        r2i, r2 = _rsi_extreme(rsi, p2, cfg.rsi_pivot_window, last_idx, use_max=is_bear)
        if math.isnan(r2):
            return None

        for p1 in pivots[-2::-1]:
            p1 = int(p1)
            gap = p2 - p1
            if gap < cfg.min_pivot_gap:
                continue
            if gap > cfg.max_pivot_gap:
                break
            price1 = float(prices[p1])
            r1i, r1 = _rsi_extreme(rsi, p1, cfg.rsi_pivot_window, last_idx, use_max=is_bear)
            if math.isnan(r1):
                continue
            if is_bear:
                ok = price2 >= price1 * cfg.bear_price_tolerance and r2 < r1 and r2 >= cfg.bear_rsi_min
            else:
                ok = (
                    price2 <= price1 * cfg.bull_price_tolerance
                    and r2 > r1
                    and r2 <= cfg.bull_rsi_max
                    and r1 < cfg.bull_prior_rsi_max
                )
            if ok:
                idx = df.index
                return Divergence(
                    kind=kind, idx1=p1, idx2=p2, t1=idx[p1], t2=idx[p2], price1=price1, price2=price2,
                    rsi_idx1=r1i, rsi_idx2=r2i, rsi_t1=idx[r1i], rsi_t2=idx[r2i], rsi1=r1, rsi2=r2,
                    bars_since_pivot=bars_since,
                )
        return None

    def scan(self, df: pd.DataFrame) -> List[Divergence]:
        signals = [self.detect(df, "BULLISH"), self.detect(df, "BEARISH")]
        return [s for s in signals if s is not None]


# ════════════════════════════════════════════════════════════════════════════════════════════
# Position analytics
# ════════════════════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PositionSnapshot:
    oz: float
    entry: Optional[float]
    price: float
    usd_thb: float

    @property
    def is_open(self) -> bool:
        return self.entry is not None and self.oz > 0

    @property
    def pnl_usd(self) -> float:
        return (self.price - self.entry) * self.oz if self.is_open else 0.0

    @property
    def pnl_thb(self) -> float:
        return self.pnl_usd * self.usd_thb

    @property
    def pnl_pct(self) -> float:
        return (self.price / self.entry - 1.0) * 100.0 if self.is_open else 0.0

    def target_price(self, pct: float, base: Optional[float] = None) -> float:
        ref = base if base is not None else (self.entry if self.is_open else self.price)
        return ref * (1.0 + pct / 100.0)


# ════════════════════════════════════════════════════════════════════════════════════════════
# Chart rendering (in memory only)
# ════════════════════════════════════════════════════════════════════════════════════════════

_MARKET_COLORS = mpf.make_marketcolors(up="#26a69a", down="#ef5350", edge="inherit", wick="inherit", volume="in")
CHART_STYLE = mpf.make_mpf_style(
    base_mpf_style="charles",
    marketcolors=_MARKET_COLORS,
    gridstyle=":",
    gridcolor="#d9d9d9",
    facecolor="#ffffff",
    figcolor="#ffffff",
    rc={"font.size": 9, "axes.labelsize": 9, "axes.titlesize": 11},
)
RSI_LEVEL_COLORS: Dict[float, str] = {30.0: "#2e7d32", 35.0: "#66bb6a", 55.0: "#fb8c00", 70.0: "#c62828"}


def render_signal_chart(df_ind: pd.DataFrame, sig: Optional[Divergence], cfg: Config, title: str) -> bytes:
    """Render the last `chart_bars` candles plus RSI panel to PNG bytes. Nothing touches disk."""
    tz = ZoneInfo(cfg.display_tz)
    view = df_ind.iloc[-cfg.chart_bars:].copy()
    view.index = view.index.tz_convert(tz).tz_localize(None)

    def local(ts: pd.Timestamp) -> pd.Timestamp:
        return ts.tz_convert(tz).tz_localize(None)

    apds = [
        mpf.make_addplot(view["ema_fast"], panel=0, color="#1e88e5", width=1.0),
        mpf.make_addplot(view["ema_slow"], panel=0, color="#8e24aa", width=1.0),
        mpf.make_addplot(view["rsi"], panel=1, color="#37474f", width=1.2, ylabel=f"RSI {cfg.rsi_period}",
                         ylim=(0, 100)),
    ]
    for level, color in RSI_LEVEL_COLORS.items():
        apds.append(
            mpf.make_addplot(pd.Series(level, index=view.index), panel=1, color=color, width=0.8,
                             linestyle="--", ylim=(0, 100))
        )

    kwargs = {}
    div_color = "#c62828" if sig is not None and sig.kind == "BEARISH" else "#2e7d32"
    if sig is not None:
        t1, t2 = local(sig.t1), local(sig.t2)
        if t1 in view.index and t2 in view.index:
            kwargs["alines"] = dict(alines=[[(t1, sig.price1), (t2, sig.price2)]], colors=[div_color],
                                    linewidths=2.0, alpha=0.9)
        rt1, rt2 = local(sig.rsi_t1), local(sig.rsi_t2)
        if rt1 in view.index and rt2 in view.index:
            line = pd.Series(np.nan, index=view.index)
            i1, i2 = view.index.get_loc(rt1), view.index.get_loc(rt2)
            line.iloc[i1 : i2 + 1] = np.linspace(sig.rsi1, sig.rsi2, i2 - i1 + 1)
            apds.append(mpf.make_addplot(line, panel=1, color=div_color, width=2.0, ylim=(0, 100)))
    if cfg.entry_price is not None and cfg.position_oz > 0:
        kwargs["hlines"] = dict(hlines=[cfg.entry_price], colors=["#546e7a"], linestyle="-.", linewidths=0.9)

    fig, _axes = mpf.plot(
        view[["open", "high", "low", "close", "volume"]],
        type="candle",
        style=CHART_STYLE,
        addplot=apds,
        panel_ratios=(3, 1.3),
        volume=False,
        figsize=(12, 7.5),
        title=title,
        ylabel="Price (USD/oz)",
        datetime_format="%d %b %H:%M",
        xrotation=15,
        returnfig=True,
        warn_too_much_data=10_000,
        **kwargs,
    )
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", dpi=cfg.chart_dpi, bbox_inches="tight")
    finally:
        plt.close(fig)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════════════════════
# Caption builder
# ════════════════════════════════════════════════════════════════════════════════════════════


def md_escape(text: str) -> str:
    """Escape Telegram legacy-Markdown control characters in dynamic text."""
    for ch in ("\\", "_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def fmt_usd(x: float, signed: bool = False) -> str:
    sign = ("+" if x > 0 else "-" if x < 0 else "") if signed else ("-" if x < 0 else "")
    return f"{sign}${abs(x):,.2f}"


def fmt_thb(x: float, signed: bool = False) -> str:
    sign = ("+" if x > 0 else "-" if x < 0 else "") if signed else ("-" if x < 0 else "")
    return f"{sign}{abs(x):,.2f} THB"


def recommended_actions(sig: Divergence, pos: PositionSnapshot, ctx: RegimeContext, cfg: Config) -> List[str]:
    t1, t15, t2 = (pos.target_price(p) for p in (1.0, 1.5, 2.0))
    actions: List[str] = []
    if sig.kind == "BULLISH":
        if pos.is_open and pos.pnl_pct < 0:
            actions.append("HOLD the physical position. Do NOT sell into RSI < 30 - the wallet has no margin call.")
            actions.append("Averaging is allowed ONLY if it was pre-planned; never exceed your max allocation.")
        elif pos.is_open:
            actions.append("Position already in profit - keep it; do not chase a second entry at a worse price.")
        else:
            actions.append(f"ENTRY WATCH: consider a planned tranche ({cfg.position_oz:.2f} oz) after the "
                           "next 1H candle closes above the signal candle high.")
        if ctx.regime == "BEAR_RANGE":
            actions.append("4H is in a BEAR range: expect the bounce to stall at RSI 55-60 - take profit early.")
        elif ctx.regime == "BULL_RANGE":
            actions.append("4H is in a BULL range: dip-buy context is favourable; 1H RSI 40-50 should hold.")
        else:
            actions.append("4H regime is in transition: size small and respect the +1.0% first target.")
        actions.append(f"Targets: +1.0% {fmt_usd(t1)} | +1.5% {fmt_usd(t15)} | +2.0% {fmt_usd(t2)}")
    else:
        if pos.is_open and pos.pnl_pct >= 1.0:
            actions.append(f"TAKE PROFIT: position is {pos.pnl_pct:+.2f}% - sell all or at least half now.")
            actions.append("Trail the remainder at breakeven + 0.5%; exit fully on a close below EMA50.")
        elif pos.is_open and pos.pnl_pct >= 0:
            actions.append(f"EXIT / SCRATCH: momentum fading at {pos.pnl_pct:+.2f}% - close at breakeven or "
                           "better rather than risk a round trip.")
        elif pos.is_open:
            actions.append("Position is under water: do NOT add. Hold the physical gold and wait for the next "
                           "bullish divergence to exit near breakeven.")
        else:
            actions.append("NO NEW BUY: RSI exhaustion at 55-60+. Wait for a pullback and a bullish setup.")
        if ctx.regime == "BEAR_RANGE":
            actions.append("4H BEAR range confirms: RSI 55-60 is the resistance band - this signal is high quality.")
        elif ctx.regime == "BULL_RANGE":
            actions.append("4H BULL range: divergence may only produce a pullback to RSI 40-50 - lock partial gains.")
        else:
            actions.append("4H regime in transition: tighten stops and reduce exposure.")
    return actions


def build_caption(
    sig: Divergence, df_ind: pd.DataFrame, pos: PositionSnapshot, ctx: RegimeContext, cfg: Config
) -> str:
    tz = ZoneInfo(cfg.display_tz)
    last = df_ind.iloc[-1]
    ts_local = df_ind.index[-1].tz_convert(tz)
    rule = "━━━━━━━━━━━━━━━━"
    if sig.kind == "BULLISH":
        head = "🟢 *BULLISH DIVERGENCE - ENTRY WATCH*"
        struct = (f"Price lower low `{fmt_usd(sig.price1)} → {fmt_usd(sig.price2)}`\n"
                  f"RSI higher low `{sig.rsi1:.1f} → {sig.rsi2:.1f}`")
    else:
        head = "🔴 *BEARISH DIVERGENCE - EXIT WATCH*"
        struct = (f"Price higher high `{fmt_usd(sig.price1)} → {fmt_usd(sig.price2)}`\n"
                  f"RSI lower high `{sig.rsi1:.1f} → {sig.rsi2:.1f}`")
    lines = [
        head,
        f"*{md_escape(cfg.symbol_label)}* · 1H · `{ts_local:%d %b %Y %H:%M} {md_escape(cfg.display_tz)}`",
        rule,
        f"*Price:* `{fmt_usd(float(last['close']))}`",
        f"*Signal:* {sig.kind.title()} RSI({cfg.rsi_period}) divergence",
        struct,
        f"*RSI(14) now:* `{float(last['rsi']):.1f}` · pivot {sig.bars_since_pivot} bar(s) ago",
        f"*EMA50/200:* `{fmt_usd(float(last['ema_fast']))} / {fmt_usd(float(last['ema_slow']))}` ({ctx.trend_1h})",
        f"*4H regime:* {ctx.regime.replace('_', ' ')} (RSI4H `{ctx.rsi_4h:.1f}`)",
        rule,
    ]
    if pos.is_open:
        lines.append(f"*Position:* {pos.oz:.2f} oz @ `{fmt_usd(pos.entry)}`")
        lines.append(f"*P/L:* `{fmt_usd(pos.pnl_usd, True)}` | `{fmt_thb(pos.pnl_thb, True)}` "
                     f"({pos.pnl_pct:+.2f}%)")
    else:
        lines.append("*Position:* none configured (set ENTRY\\_PRICE)")
    lines.append(rule)
    lines.append("*Action:*")
    lines.extend(f"{i}. {md_escape(a)}" for i, a in enumerate(recommended_actions(sig, pos, ctx, cfg), 1))
    lines.append("_Not financial advice._")
    caption = "\n".join(lines)
    if len(caption) > TELEGRAM_CAPTION_LIMIT:
        # Drop action lines from the end (never the header/prices) until it fits.
        while len(caption) > TELEGRAM_CAPTION_LIMIT and len(lines) > 12:
            lines.pop(-2)
            caption = "\n".join(lines)
        caption = caption[:TELEGRAM_CAPTION_LIMIT]
    return caption


# ════════════════════════════════════════════════════════════════════════════════════════════
# Telegram dispatcher
# ════════════════════════════════════════════════════════════════════════════════════════════


class TelegramDispatcher:
    """sendPhoto with retry on 429/5xx and a plain-text fallback when Markdown fails to parse."""

    def __init__(self, cfg: Config, session: Optional[requests.Session] = None, max_attempts: int = 4) -> None:
        self.cfg = cfg
        self.session = session or requests.Session()
        self.max_attempts = max_attempts

    @property
    def url(self) -> str:
        return f"{TELEGRAM_API_BASE}/bot{self.cfg.telegram_token}/sendPhoto"

    def send_photo(self, png: bytes, caption: str) -> None:
        if not self.cfg.telegram_enabled:
            LOG.info("[DRY-RUN] sendPhoto suppressed (%d bytes PNG). Caption:\n%s", len(png), caption)
            return
        parse_mode: Optional[str] = "Markdown"
        attempt = 0
        delay = 2.0
        while True:
            attempt += 1
            data = {"chat_id": self.cfg.telegram_chat_id, "caption": caption}
            if parse_mode:
                data["parse_mode"] = parse_mode
            files = {"photo": ("gold_signal.png", png, "image/png")}
            try:
                resp = self.session.post(self.url, data=data, files=files, timeout=self.cfg.request_timeout)
            except requests.RequestException as exc:
                if attempt >= self.max_attempts:
                    raise DispatchError(f"Telegram network error after {attempt} attempts: {exc}") from exc
                LOG.warning("Telegram network error (%s); retrying in %.0fs", exc, delay)
                time.sleep(delay)
                delay *= 2
                continue

            if resp.status_code == 200:
                LOG.info("Telegram alert delivered (attempt %d).", attempt)
                return
            try:
                payload = resp.json()
            except ValueError:
                payload = {}
            description = str(payload.get("description", resp.text[:200]))
            if resp.status_code == 400 and parse_mode and "parse" in description.lower():
                LOG.warning("Telegram rejected Markdown (%s); resending as plain text.", description)
                parse_mode = None
                caption = caption.replace("*", "").replace("`", "").replace("\\", "")
                continue
            if attempt >= self.max_attempts:
                raise DispatchError(f"Telegram HTTP {resp.status_code}: {description}")
            if resp.status_code == 429:
                retry_after = float(payload.get("parameters", {}).get("retry_after", delay))
                LOG.warning("Telegram rate-limited; sleeping %.0fs", retry_after)
                time.sleep(retry_after)
                continue
            if 500 <= resp.status_code < 600:
                LOG.warning("Telegram HTTP %d; retrying in %.0fs", resp.status_code, delay)
                time.sleep(delay)
                delay *= 2
                continue
            raise DispatchError(f"Telegram HTTP {resp.status_code}: {description}")


# ════════════════════════════════════════════════════════════════════════════════════════════
# State store / debounce
# ════════════════════════════════════════════════════════════════════════════════════════════


class StateStore:
    """Persists alerted divergence keys so restarts never re-send the same pivot.

    path=None keeps state in memory only (used by --self-test). Writes are atomic
    (temp file + os.replace) so a crash mid-write cannot corrupt the state file.
    """

    def __init__(self, path: Optional[str], cooldown_minutes: float, retention_days: float) -> None:
        self.path = path
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.retention = timedelta(days=retention_days)
        self._lock = threading.Lock()
        self.alerted: Dict[str, str] = {}
        self.last_by_kind: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path or not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.alerted = {str(k): str(v) for k, v in data.get("alerted", {}).items()}
            self.last_by_kind = {str(k): str(v) for k, v in data.get("last_by_kind", {}).items()}
        except (OSError, ValueError) as exc:
            LOG.error("State file %s unreadable (%s); starting with empty state.", self.path, exc)
            self.alerted, self.last_by_kind = {}, {}

    def _save(self) -> None:
        if not self.path:
            return
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".gold_bot_state.", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"alerted": self.alerted, "last_by_kind": self.last_by_kind,
                           "version": __version__}, fh, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def should_alert(self, sig: Divergence, now: datetime) -> bool:
        with self._lock:
            if sig.key in self.alerted:
                return False
            last = self.last_by_kind.get(sig.kind)
            if last is not None and now - datetime.fromisoformat(last) < self.cooldown:
                LOG.info("Cooldown active for %s (last alert %s); suppressing %s", sig.kind, last, sig.key)
                return False
            return True

    def mark_alerted(self, sig: Divergence, now: datetime) -> None:
        with self._lock:
            self.alerted[sig.key] = now.isoformat()
            self.last_by_kind[sig.kind] = now.isoformat()
            cutoff = now - self.retention
            self.alerted = {k: v for k, v in self.alerted.items() if datetime.fromisoformat(v) >= cutoff}
            self._save()


# ════════════════════════════════════════════════════════════════════════════════════════════
# Orchestration
# ════════════════════════════════════════════════════════════════════════════════════════════


class GoldMonitorBot:
    def __init__(self, cfg: Config, provider=None, dispatcher: Optional[TelegramDispatcher] = None,
                 state: Optional[StateStore] = None) -> None:
        cfg.validate()
        self.cfg = cfg
        self.provider = provider or build_provider(cfg)
        self.dispatcher = dispatcher or TelegramDispatcher(cfg)
        self.state = state or StateStore(cfg.state_path, cfg.alert_cooldown_minutes, cfg.state_retention_days)
        self.engine = DivergenceEngine(cfg)
        self._stop = threading.Event()

    def stop(self, *_args) -> None:
        LOG.info("Stop requested; finishing current cycle.")
        self._stop.set()

    def run_cycle(self, now: Optional[datetime] = None) -> List[Divergence]:
        """One full pipeline pass. Returns the signals that were dispatched."""
        now = now or datetime.now(timezone.utc)
        raw = self.provider.fetch()
        df = validate_ohlcv(raw, self.cfg.min_bars)
        df_ind = compute_indicators(df, self.cfg)
        ctx = classify_regime(df_ind, self.cfg)
        last = df_ind.iloc[-1]
        LOG.info("Bar %s close=%.2f RSI=%.2f EMA50=%.2f EMA200=%.2f 4H=%s",
                 df_ind.index[-1].isoformat(), last["close"], last["rsi"], last["ema_fast"], last["ema_slow"],
                 ctx.regime)

        dispatched: List[Divergence] = []
        for sig in self.engine.scan(df_ind):
            if not self.state.should_alert(sig, now):
                LOG.debug("Debounced %s", sig.key)
                continue
            pos = PositionSnapshot(self.cfg.position_oz, self.cfg.entry_price, float(last["close"]), self.cfg.usd_thb)
            title = f"{self.cfg.symbol_label} 1H - {sig.kind.title()} RSI Divergence"
            png = render_signal_chart(df_ind, sig, self.cfg, title)
            caption = build_caption(sig, df_ind, pos, ctx, self.cfg)
            LOG.info("Signal %s price %.2f->%.2f RSI %.1f->%.1f", sig.key, sig.price1, sig.price2, sig.rsi1, sig.rsi2)
            self.dispatcher.send_photo(png, caption)
            self.state.mark_alerted(sig, now)
            dispatched.append(sig)
        return dispatched

    def run_forever(self) -> None:
        LOG.info("Gold monitor v%s started: source=%s poll=%.0fs telegram=%s", __version__, self.cfg.data_source,
                 self.cfg.poll_seconds, "ON" if self.cfg.telegram_enabled else "DRY-RUN")
        backoff = self.cfg.poll_seconds
        while not self._stop.is_set():
            try:
                self.run_cycle()
                backoff = self.cfg.poll_seconds
                wait = self.cfg.poll_seconds
            except (DataError, requests.RequestException) as exc:
                backoff = min(backoff * 2, self.cfg.max_backoff_seconds)
                wait = backoff
                LOG.warning("Data/network problem: %s. Retrying in %.0fs.", exc, wait)
            except DispatchError as exc:
                backoff = min(backoff * 2, self.cfg.max_backoff_seconds)
                wait = backoff
                LOG.error("Alert delivery failed: %s. Signal stays pending; retrying in %.0fs.", exc, wait)
            except Exception:  # noqa: BLE001 - daemon must survive unexpected faults
                backoff = min(backoff * 2, self.cfg.max_backoff_seconds)
                wait = backoff
                LOG.exception("Unexpected error in cycle; retrying in %.0fs.", wait)
            self._stop.wait(wait)
        LOG.info("Gold monitor stopped.")


# ════════════════════════════════════════════════════════════════════════════════════════════
# Self-test
# ════════════════════════════════════════════════════════════════════════════════════════════


class _RecordingDispatcher(TelegramDispatcher):
    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg)
        self.sent: List[Tuple[bytes, str]] = []

    def send_photo(self, png: bytes, caption: str) -> None:
        self.sent.append((png, caption))


class _StaticProvider:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def fetch(self) -> pd.DataFrame:
        return self.df.copy()


def run_self_test(cfg: Config) -> int:
    """Deterministic end-to-end verification. Returns a process exit code."""
    cfg = dataclasses.replace(cfg, dry_run=True, state_path="")
    failures: List[str] = []

    def check(cond: bool, label: str) -> None:
        LOG.info("  [%s] %s", "PASS" if cond else "FAIL", label)
        if not cond:
            failures.append(label)

    LOG.info("Self-test 1: Wilder RSI vectorised == textbook loop")
    hist = generate_simulated_ohlcv(600, cfg.sim_start_price, cfg.sim_seed)
    vec = wilder_rsi(hist["close"], cfg.rsi_period).to_numpy()
    ref = wilder_rsi_reference(hist["close"].to_numpy(), cfg.rsi_period)
    check(bool(np.allclose(vec, ref, equal_nan=True, atol=1e-9)), "RSI matches reference within 1e-9")
    check(bool(np.isnan(vec[: cfg.rsi_period]).all()) and not math.isnan(vec[cfg.rsi_period]),
          "RSI undefined before seed bar, defined from bar 14")
    finite = vec[~np.isnan(vec)]
    check(bool(((finite >= 0) & (finite <= 100)).all()), "RSI bounded in [0, 100]")
    check(len(validate_ohlcv(hist, cfg.min_bars)) == 600, "Simulated history satisfies OHLCV contract")

    for kind in ("BULLISH", "BEARISH"):
        LOG.info("Self-test: %s divergence scenario end-to-end", kind)
        scenario = build_divergence_scenario(kind)
        entry = float(scenario["close"].iloc[-25])
        run_cfg = dataclasses.replace(cfg, entry_price=entry)
        recorder = _RecordingDispatcher(run_cfg)
        state = StateStore(None, run_cfg.alert_cooldown_minutes, run_cfg.state_retention_days)
        bot = GoldMonitorBot(run_cfg, provider=_StaticProvider(scenario), dispatcher=recorder, state=state)
        now = datetime(2026, 9, 24, 10, 5, tzinfo=timezone.utc)
        sigs = bot.run_cycle(now)
        kinds = [s.kind for s in sigs]
        check(kind in kinds, f"{kind} divergence detected (got {kinds})")
        other = "BEARISH" if kind == "BULLISH" else "BULLISH"
        check(other not in kinds, f"No false {other} signal on {kind} scenario")
        sig = next((s for s in sigs if s.kind == kind), None)
        if sig is not None:
            if kind == "BULLISH":
                check(sig.price2 <= sig.price1 * 1.001 and sig.rsi2 > sig.rsi1, "Bullish price/RSI geometry")
                check(sig.rsi2 <= 35.0 and sig.rsi1 < 30.0, "Bullish RSI zone rules (<=35, prior <30)")
            else:
                check(sig.price2 >= sig.price1 * 0.999 and sig.rsi2 < sig.rsi1, "Bearish price/RSI geometry")
                check(sig.rsi2 >= 55.0, "Bearish RSI peak >= 55")
            check(1 <= sig.bars_since_pivot <= 3, "Freshness: pivot confirmed within last 3 candles")
        check(len(recorder.sent) == len(sigs), "One Telegram payload per signal")
        if recorder.sent:
            png, caption = recorder.sent[0]
            check(png.startswith(PNG_SIGNATURE) and len(png) > 20_000, f"Chart is a valid PNG ({len(png)} bytes)")
            check(len(caption) <= TELEGRAM_CAPTION_LIMIT, f"Caption within Telegram limit ({len(caption)} chars)")
            check("P/L" in caption and "THB" in caption, "Caption carries USD and THB P/L")
        again = bot.run_cycle(now + timedelta(minutes=1))
        check(len(again) == 0, "Debounce: identical pivot is not re-alerted")

        stale = scenario.iloc[:-2]
        stale_bot = GoldMonitorBot(run_cfg, provider=_StaticProvider(stale), dispatcher=_RecordingDispatcher(run_cfg),
                                   state=StateStore(None, 0, 1))
        check(all(s.kind != kind for s in stale_bot.run_cycle(now)),
              "Unconfirmed pivot (0 closing candles after it) is not signalled")

    LOG.info("Self-test: walk-forward scan over simulated history (informational)")
    engine = DivergenceEngine(cfg)
    full = compute_indicators(generate_simulated_ohlcv(1500, cfg.sim_start_price, cfg.sim_seed), cfg)
    seen: Dict[str, int] = {"BULLISH": 0, "BEARISH": 0}
    keys = set()
    for end in range(cfg.min_bars, len(full) + 1):
        for s in engine.scan(full.iloc[:end]):
            if s.key not in keys:
                keys.add(s.key)
                seen[s.kind] += 1
    LOG.info("  Unique signals over %d bars: %s", len(full) - cfg.min_bars, seen)

    if failures:
        LOG.error("SELF-TEST FAILED (%d): %s", len(failures), "; ".join(failures))
        return 1
    LOG.info("SELF-TEST PASSED")
    return 0


# ════════════════════════════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════════════════════════════


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Gold RSI divergence monitor with Telegram chart alerts.")
    p.add_argument("--self-test", action="store_true", help="run deterministic verification and exit")
    p.add_argument("--once", action="store_true", help="run a single cycle and exit")
    p.add_argument("--dry-run", action="store_true", help="never call Telegram; log captions instead")
    p.add_argument("--source", choices=["simulated", "csv", "binance_paxg"], help="market data source")
    p.add_argument("--csv", dest="csv_path", help="CSV path when --source csv")
    p.add_argument("--state-file", dest="state_path", help="JSON debounce state path")
    p.add_argument("--position-oz", type=float, help="open position size in troy ounces")
    p.add_argument("--entry-price", type=float, help="average entry price in USD/oz")
    p.add_argument("--usd-thb", type=float, help="USD/THB conversion rate")
    p.add_argument("--poll-seconds", type=float, help="seconds between cycles")
    p.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO"), help="DEBUG|INFO|WARNING|ERROR")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    try:
        cfg = Config.from_env()
        overrides = {k: v for k, v in {
            "data_source": args.source, "csv_path": args.csv_path, "state_path": args.state_path,
            "position_oz": args.position_oz, "entry_price": args.entry_price, "usd_thb": args.usd_thb,
            "poll_seconds": args.poll_seconds,
        }.items() if v is not None}
        if args.dry_run:
            overrides["dry_run"] = True
        cfg = dataclasses.replace(cfg, **overrides)
        cfg.validate()
    except ValueError as exc:
        LOG.error("%s", exc)
        return 2

    if args.self_test:
        return run_self_test(cfg)

    if not cfg.telegram_enabled:
        LOG.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set or dry-run requested: alerts will be logged only.")

    bot = GoldMonitorBot(cfg)
    if args.once:
        try:
            sigs = bot.run_cycle()
        except (DataError, DispatchError, requests.RequestException) as exc:
            LOG.error("Cycle failed: %s", exc)
            return 1
        LOG.info("Cycle complete: %d alert(s) dispatched.", len(sigs))
        return 0

    signal.signal(signal.SIGINT, bot.stop)
    signal.signal(signal.SIGTERM, bot.stop)
    bot.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
