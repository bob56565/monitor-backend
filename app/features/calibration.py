import numpy as np
from typing import Dict, List, Tuple


def calibrate_sensor_readings(sensor_values: List[float]) -> List[float]:
    """
    Apply calibration to raw sensor readings.
    Uses mean-centering and scaling normalization.
    """
    arr = np.array(sensor_values, dtype=float)
    mean = np.mean(arr)
    std = np.std(arr) + 1e-8
    calibrated = (arr - mean) / std
    return calibrated.tolist()


def apply_offset_correction(readings: List[float], offset: float = 0.5) -> List[float]:
    """Apply bias/offset correction to sensor data."""
    return [r - offset for r in readings]


def normalize_to_range(values: List[float], min_val: float = 0.0, max_val: float = 1.0) -> List[float]:
    """Normalize values to [min_val, max_val] range."""
    arr = np.array(values, dtype=float)
    arr_min = np.min(arr)
    arr_max = np.max(arr)
    if arr_max == arr_min:
        return [min_val] * len(values)
    normalized = (arr - arr_min) / (arr_max - arr_min) * (max_val - min_val) + min_val
    return normalized.tolist()


def get_calibration_metadata(raw_values: List[float]) -> Dict:
    """Return calibration metadata for audit/debugging."""
    arr = np.array(raw_values, dtype=float)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "count": len(raw_values),
    }
