"""
Configuration and thresholds for the Correlation Engine.
All weights, thresholds, paths, and limits are centrally configurable.
"""
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class CorrelationSettings(BaseSettings):
    # Core Processing Parameters
    CHUNK_SIZE: int = 50000
    MAX_TRANSACTIONS_DEFAULT: Optional[int] = None  # None = process all
    CORRELATION_TIME_WINDOW_SECONDS: float = 120.0   # +/- 120s window

    # Thresholds for Behavioral Flagging
    HIGH_FAN_IN_THRESHOLD: int = 4
    HIGH_FAN_OUT_THRESHOLD: int = 4
    LARGE_TRANSACTION_THRESHOLD: float = 10.0  # BTC
    VERY_LARGE_TRANSACTION_THRESHOLD: float = 50.0  # BTC
    HIGH_FEE_THRESHOLD: float = 0.01  # BTC
    CONNECTED_WALLETS_THRESHOLD: int = 5
    NETWORK_CONFIDENCE_THRESHOLD: float = 0.5

    # Transparent Scoring Weights (0 - 100)
    WEIGHT_HIGH_FAN_IN: int = 15
    WEIGHT_HIGH_FAN_OUT: int = 15
    WEIGHT_LARGE_TRANSACTION: int = 15
    WEIGHT_STRONG_NETWORK: int = 25
    WEIGHT_MULTIPLE_WALLETS: int = 10
    WEIGHT_KNOWN_ILLICIT_CLASS: int = 20
    WEIGHT_RAPID_TEMPORAL_BURST: int = 10

    # Risk Priority Cutoffs
    PRIORITY_LOW_MAX: int = 39
    PRIORITY_MEDIUM_MAX: int = 69
    # 70+ is HIGH

    # Dataset Directories (checked in order of fallback)
    DATA_DIRS: List[Path] = [
        Path("C:/Users/ASUS/Desktop/SIHH"),
        Path("C:/Users/ASUS/Documents/SIH/data/correlation"),
        Path("C:/Users/ASUS/Documents/SIH/data"),
        Path("C:/Users/ASUS/Documents/DATASET"),
    ]

    # Output Directory
    OUTPUT_DIR: Path = Path("C:/Users/ASUS/Documents/SIH/correlation_output")
    MODELS_DIR: Path = Path("C:/Users/ASUS/Documents/SIH/models")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

correlation_settings = CorrelationSettings()
