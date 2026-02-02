import numpy as np
from typing import Dict, List, Tuple
from sklearn.preprocessing import StandardScaler


class MVPInferenceModel:
    """
    Minimal Viable Product inference model.
    Uses simple linear regression-like prediction with uncertainty heuristic.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.weights = np.array([0.4, 0.35, 0.25])  # Feature weights
        self.bias = 0.1
        self.fitted = False

    def fit(self, features: List[List[float]], targets: List[float]):
        """
        Simple fit: standardize features and store for prediction.
        In production, would use proper ML model training.
        """
        self.features_training = np.array(features, dtype=float)
        self.targets_training = np.array(targets, dtype=float)
        self.scaler.fit(self.features_training)
        self.fitted = True

    def predict(self, features: List[float]) -> Dict[str, float]:
        """
        Predict target value and compute uncertainty heuristic.
        
        Returns:
            dict with 'prediction', 'confidence', 'uncertainty', 'reasoning'
        """
        arr = np.array(features, dtype=float)
        
        # Simple linear prediction
        if len(arr) != len(self.weights):
            # Fallback: use mean
            prediction = float(np.mean(arr)) + self.bias
        else:
            prediction = float(np.dot(arr, self.weights)) + self.bias

        # Uncertainty heuristic: distance from training data mean
        if self.fitted and len(self.features_training) > 0:
            training_feature_mean = np.mean(self.features_training, axis=0)
            distance = np.linalg.norm(arr - training_feature_mean) + 1e-8
            # Inverse relationship: closer to training data = lower uncertainty
            uncertainty = 1.0 / (1.0 + np.exp(-distance / 2.0))  # Sigmoid
        else:
            uncertainty = 0.5  # Default medium uncertainty

        # Confidence: inverse of uncertainty
        confidence = 1.0 - uncertainty

        return {
            "prediction": float(prediction),
            "confidence": float(confidence),
            "uncertainty": float(uncertainty),
            "reasoning": "MVP linear model with distance-based uncertainty",
        }

    def batch_predict(self, feature_list: List[List[float]]) -> List[Dict[str, float]]:
        """Predict for multiple feature vectors."""
        return [self.predict(features) for features in feature_list]


# Global model instance (in production, would use proper model persistence)
_inference_model = MVPInferenceModel()


def initialize_model(training_features: List[List[float]] = None, training_targets: List[float] = None):
    """Initialize the global inference model."""
    global _inference_model
    _inference_model = MVPInferenceModel()
    if training_features is not None and training_targets is not None:
        _inference_model.fit(training_features, training_targets)


def infer(features: List[float]) -> Dict[str, float]:
    """Perform inference using global model."""
    return _inference_model.predict(features)


def batch_infer(feature_list: List[List[float]]) -> List[Dict[str, float]]:
    """Batch inference."""
    return _inference_model.batch_predict(feature_list)
