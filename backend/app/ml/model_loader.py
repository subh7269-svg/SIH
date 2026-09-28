"""
Model Loader and Cache for ML Anomaly Detectors.
Loads serialized Isolation Forest and Scaler joblib models.
"""
from pathlib import Path
from typing import Optional, Tuple, Any
import joblib
import logging

logger = logging.getLogger("tracex.ml.loader")

_MODEL_CACHE: dict = {}

def get_model_paths(models_dir: Optional[Path] = None) -> Tuple[Path, Path]:
    base = models_dir or Path("C:/Users/ASUS/Documents/SIH/models")
    base.mkdir(parents=True, exist_ok=True)
    return base / "isolation_forest.joblib", base / "scaler.joblib"

def load_models(models_dir: Optional[Path] = None, force_reload: bool = False) -> Tuple[Optional[Any], Optional[Any]]:
    """Loads Isolation Forest model and Scaler from joblib artifacts."""
    global _MODEL_CACHE
    model_path, scaler_path = get_model_paths(models_dir)

    cache_key = f"{model_path}_{scaler_path}"
    if not force_reload and cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]

    model = None
    scaler = None

    if model_path.exists():
        try:
            model = joblib.load(model_path)
            logger.info(f"Loaded Isolation Forest model from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load Isolation Forest from {model_path}: {e}")

    if scaler_path.exists():
        try:
            scaler = joblib.load(scaler_path)
            logger.info(f"Loaded Scaler from {scaler_path}")
        except Exception as e:
            logger.error(f"Failed to load Scaler from {scaler_path}: {e}")

    _MODEL_CACHE[cache_key] = (model, scaler)
    return model, scaler

def save_models(model: Any, scaler: Any, models_dir: Optional[Path] = None) -> Tuple[Path, Path]:
    """Saves Isolation Forest model and Scaler using joblib."""
    model_path, scaler_path = get_model_paths(models_dir)
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    logger.info(f"Successfully saved Isolation Forest to {model_path} and Scaler to {scaler_path}")
    return model_path, scaler_path
