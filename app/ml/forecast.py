from typing import Dict, List
import numpy as np


def forecast_next_step(features: List[float], steps_ahead: int = 1) -> Dict:
    """
    Simple stub forecast using linear extrapolation.
    Generates multi-step forecasts by repeating the step-1 prediction.
    In production, would use proper time-series model (ARIMA, Prophet, etc).
    """
    steps_ahead = max(1, steps_ahead)  # Clamp to at least 1
    
    if len(features) < 2:
        base_forecast = float(features[-1]) if features else 0.0
        forecasts = [base_forecast] * steps_ahead
        return {
            "forecast": base_forecast,
            "forecasts": forecasts,
            "steps_ahead": steps_ahead,
            "confidence": 0.3,  # Low confidence for stub
            "method": "stub_linear_extrapolation",
        }

    arr = np.array(features, dtype=float)
    # Simple linear trend
    trend = arr[-1] - arr[-2]
    
    # Generate multi-step forecast: step 1 uses the trend, subsequent steps repeat step 1
    step1_forecast = float(arr[-1] + trend)
    forecasts = [step1_forecast] * steps_ahead

    return {
        "forecast": step1_forecast,
        "forecasts": forecasts,
        "steps_ahead": steps_ahead,
        "confidence": 0.4,  # Low confidence for stub
        "method": "linear_extrapolation",
        "trend": float(trend),
    }


def batch_forecast(feature_sequences: List[List[float]], steps_ahead: int = 1) -> List[Dict]:
    """Forecast for multiple sequences."""
    return [forecast_next_step(seq, steps_ahead) for seq in feature_sequences]
