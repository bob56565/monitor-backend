import numpy as np
from typing import List, Dict, Tuple


def compute_moving_average(values: List[float], window: int = 3) -> List[float]:
    """Compute moving average over a window."""
    if len(values) < window:
        return values
    arr = np.array(values, dtype=float)
    result = np.convolve(arr, np.ones(window) / window, mode='valid')
    # Pad with original values to maintain length
    padding = len(values) - len(result)
    padded = list(arr[:padding]) + result.tolist()
    return padded


def compute_rolling_std(values: List[float], window: int = 3) -> List[float]:
    """Compute rolling standard deviation."""
    if len(values) < window:
        return [0.0] * len(values)
    arr = np.array(values, dtype=float)
    result = []
    for i in range(len(arr)):
        start = max(0, i - window + 1)
        result.append(float(np.std(arr[start:i+1])))
    return result


def compute_derived_metric(features: List[float]) -> float:
    """
    Compute a derived metric from calibrated features.
    Simple example: weighted sum.
    """
    arr = np.array(features, dtype=float)
    weights = np.array([0.5, 0.3, 0.2])  # Weights for 3 features
    if len(arr) != len(weights):
        # Fallback to simple mean if different length
        return float(np.mean(arr))
    return float(np.dot(arr, weights))


def extract_temporal_features(timestamp_sequence: List[float]) -> Dict[str, float]:
    """Extract temporal features from a sequence of timestamps."""
    if len(timestamp_sequence) < 2:
        return {"delta_mean": 0.0, "delta_std": 0.0, "rate": 0.0}
    
    deltas = np.diff(timestamp_sequence)
    return {
        "delta_mean": float(np.mean(deltas)),
        "delta_std": float(np.std(deltas)),
        "rate": float(1.0 / (np.mean(deltas) + 1e-8)),  # Samples per unit time
    }


def aggregate_features(feature_vectors: List[List[float]]) -> Dict[str, float]:
    """Aggregate multiple feature vectors into summary stats."""
    arr = np.array(feature_vectors, dtype=float)
    return {
        "mean_across_samples": float(np.mean(arr, axis=0).mean()),
        "std_across_samples": float(np.std(arr, axis=0).mean()),
        "max_across_samples": float(np.max(arr)),
        "min_across_samples": float(np.min(arr)),
    }
