from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # === Bybit API (Testnet) ===
    bybit_api_key: str = Field("", env="REDACTED_BYBIT_API_KEY")
    bybit_api_secret: str = Field("", env="REDACTED_BYBIT_API_SECRET")
    bybit_testnet: bool = Field(True, env="BYBIT_TESTNET")

    # === Trading Setup ===
    symbol: str = Field("BTCUSDT", env="SYMBOL")
    timeframe: str = Field("5m", env="TIMEFRAME")
    leverage: int = Field(3, env="LEVERAGE")
    risk_per_trade_pct: float = Field(0.5, env="RISK_PER_TRADE_PCT")
    daily_loss_limit_pct: float = Field(2.0, env="DAILY_LOSS_LIMIT_PCT")
    max_new_entries_per_hour: int = Field(3, env="MAX_NEW_ENTRIES_PER_HOUR")
    start_balance: float = Field(10000.0, env="START_BALANCE")

    # === Exits ===
    use_tp: bool = Field(True, env="USE_TP")
    tp_pct: float = Field(2.5, env="TP_PCT")
    sl_pct: float = Field(1.0, env="SL_PCT")
    trail_trigger_pct: float = Field(1.5, env="TRAIL_TRIGGER_PCT")
    trail_distance_pct: float = Field(0.5, env="TRAIL_DISTANCE_PCT")

    # === Fine Tuning ===
    atr_min_pct: float = Field(0.20, env="ATR_MIN_PCT")
    atr_max_pct: float = Field(1.20, env="ATR_MAX_PCT")
    cooldown_bars: int = Field(1, env="COOLDOWN_BARS")
    use_session: bool = Field(True, env="USE_SESSION")
    session_start: str = Field("06:00", env="SESSION_START")
    session_end: str = Field("23:00", env="SESSION_END")
    tz: str = Field("Europe/Zurich", env="TZ")
    max_spread_pct: float = Field(0.04, env="MAX_SPREAD_PCT")
    entry_min_seconds: int = Field(120, env="ENTRY_MIN_SECONDS")
    heartbeat_secs: int = Field(15, env="HEARTBEAT_SECS")
    missed_heartbeats_max: int = Field(2, env="MISSED_HEARTBEATS_MAX")
    use_event_guard: bool = Field(True, env="USE_EVENT_GUARD")
    event_guard_minutes: int = Field(15, env="EVENT_GUARD_MINUTES")
    strict_precision: bool = Field(True, env="STRICT_PRECISION")
    enforce_backtest_parity: bool = Field(True, env="ENFORCE_BACKTEST_PARITY")
    dry_run: bool = Field(True, env="DRY_RUN")
    allow_continuation: bool = Field(True, env="ALLOW_CONTINUATION")

    # === Adaptive Parameters ===
    adaptive_vol_mult: bool = Field(True, env="ADAPTIVE_VOL_MULT")
    vol_mult_base: float = Field(1.2, env="VOL_MULT_BASE")
    vol_mult_tight: float = Field(1.3, env="VOL_MULT_TIGHT")
    adaptive_tp: bool = Field(True, env="ADAPTIVE_TP")

    # === Debug / Logging ===
    debug_signals: bool = Field(True, env="DEBUG_SIGNALS")
    loguru_level: str = Field("DEBUG", env="LOGURU_LEVEL")

    # === Model Config ===
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # erlaubt zusätzliche Variablen wie RSI_ oder ATR_
    )


SETTINGS = Settings()