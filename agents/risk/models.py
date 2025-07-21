"""
AI/ML Risk Assessment Models

This module implements various machine learning models for risk assessment:
- Time series prediction models (LSTM/Transformer)
- Risk classification models (Random Forest/XGBoost)
- Anomaly detection models (Isolation Forest)
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import logging
from pathlib import Path

# ML libraries
try:
    import torch
    import torch.nn as nn
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    import xgboost as xgb
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML libraries not available. Using mock implementations.")

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskPrediction:
    """Risk prediction result"""
    risk_level: RiskLevel
    probability: float
    confidence: float
    factors: Dict[str, float]
    timestamp: datetime
    model_version: str


@dataclass
class TimeSeriesData:
    """Time series data structure"""
    timestamp: datetime
    values: Dict[str, float]
    metadata: Dict[str, Any]


@dataclass
class AnomalyResult:
    """Anomaly detection result"""
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    timestamp: datetime
    features: Dict[str, float]


class RiskAssessmentModel:
    """Base class for risk assessment models"""
    
    def __init__(self, model_name: str, model_version: str = "1.0.0"):
        self.model_name = model_name
        self.model_version = model_version
        self.is_trained = False
        self.scaler = StandardScaler() if ML_AVAILABLE else None
        self.model = None
        self.feature_names = []
        self.training_history = []
        
    async def train(self, data: pd.DataFrame, target: str) -> Dict[str, Any]:
        """Train the risk assessment model"""
        try:
            if not ML_AVAILABLE:
                logger.warning("ML libraries not available. Using mock training.")
                self.is_trained = True
                return {
                    "status": "success",
                    "model_name": self.model_name,
                    "training_samples": len(data),
                    "mock": True
                }
            
            # Prepare features
            features = data.drop(columns=[target])
            labels = data[target]
            self.feature_names = features.columns.tolist()
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Train model (implementation depends on specific model type)
            await self._train_model(features_scaled, labels)
            
            self.is_trained = True
            
            training_result = {
                "status": "success",
                "model_name": self.model_name,
                "training_samples": len(data),
                "features": len(self.feature_names),
                "feature_names": self.feature_names,
                "timestamp": datetime.now().isoformat()
            }
            
            self.training_history.append(training_result)
            
            logger.info(f"Model {self.model_name} trained successfully")
            return training_result
            
        except Exception as e:
            logger.error(f"Training failed for {self.model_name}: {e}")
            return {
                "status": "error",
                "model_name": self.model_name,
                "error": str(e)
            }
    
    async def _train_model(self, features: np.ndarray, labels: np.ndarray):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement _train_model")
    
    async def predict(self, features: Dict[str, float]) -> RiskPrediction:
        """Make risk prediction"""
        if not self.is_trained:
            raise ValueError(f"Model {self.model_name} is not trained")
        
        try:
            # Mock prediction if ML libraries not available
            if not ML_AVAILABLE:
                return RiskPrediction(
                    risk_level=RiskLevel.MEDIUM,
                    probability=0.5,
                    confidence=0.8,
                    factors=features,
                    timestamp=datetime.now(),
                    model_version=self.model_version
                )
            
            # Prepare features
            feature_values = [features.get(name, 0.0) for name in self.feature_names]
            feature_array = np.array(feature_values).reshape(1, -1)
            feature_scaled = self.scaler.transform(feature_array)
            
            # Make prediction
            prediction_result = await self._predict_model(feature_scaled)
            
            return RiskPrediction(
                risk_level=prediction_result["risk_level"],
                probability=prediction_result["probability"],
                confidence=prediction_result["confidence"],
                factors=features,
                timestamp=datetime.now(),
                model_version=self.model_version
            )
            
        except Exception as e:
            logger.error(f"Prediction failed for {self.model_name}: {e}")
            # Return fallback prediction
            return RiskPrediction(
                risk_level=RiskLevel.MEDIUM,
                probability=0.5,
                confidence=0.0,
                factors=features,
                timestamp=datetime.now(),
                model_version=self.model_version
            )
    
    async def _predict_model(self, features: np.ndarray) -> Dict[str, Any]:
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement _predict_model")
    
    async def evaluate(self, test_data: pd.DataFrame, target: str) -> Dict[str, float]:
        """Evaluate model performance"""
        if not self.is_trained:
            raise ValueError(f"Model {self.model_name} is not trained")
        
        try:
            if not ML_AVAILABLE:
                return {
                    "accuracy": 0.85,
                    "precision": 0.82,
                    "recall": 0.88,
                    "f1_score": 0.85,
                    "mock": True
                }
            
            # Prepare test data
            features = test_data.drop(columns=[target])
            labels = test_data[target]
            features_scaled = self.scaler.transform(features)
            
            # Make predictions
            predictions = []
            for i in range(len(features_scaled)):
                feature_dict = {name: features_scaled[i][j] 
                              for j, name in enumerate(self.feature_names)}
                pred = await self.predict(feature_dict)
                predictions.append(pred.risk_level.value)
            
            # Calculate metrics
            accuracy = accuracy_score(labels, predictions)
            precision = precision_score(labels, predictions, average='weighted')
            recall = recall_score(labels, predictions, average='weighted')
            f1 = 2 * (precision * recall) / (precision + recall)
            
            return {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "test_samples": len(test_data)
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed for {self.model_name}: {e}")
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "error": str(e)
            }


class TimeSeriesPredictor(RiskAssessmentModel):
    """Time series prediction model using LSTM/Transformer"""
    
    def __init__(self, sequence_length: int = 30, hidden_size: int = 64):
        super().__init__("TimeSeriesPredictor", "1.0.0")
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if ML_AVAILABLE else None
        
    async def _train_model(self, features: np.ndarray, labels: np.ndarray):
        """Train LSTM model for time series prediction"""
        if not ML_AVAILABLE:
            return
        
        # Create LSTM model
        input_size = features.shape[1]
        self.model = LSTMModel(input_size, self.hidden_size, 4)  # 4 risk levels
        self.model.to(self.device)
        
        # Prepare training data
        X_train, y_train = self._prepare_sequences(features, labels)
        
        # Train model
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        
        self.model.train()
        for epoch in range(100):  # Simple training loop
            optimizer.zero_grad()
            outputs = self.model(X_train)
            loss = criterion(outputs, y_train)
            loss.backward()
            optimizer.step()
            
            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}, Loss: {loss.item():.4f}")
    
    def _prepare_sequences(self, features: np.ndarray, labels: np.ndarray) -> Tuple[torch.Tensor, torch.Tensor]:
        """Prepare sequences for LSTM training"""
        if not ML_AVAILABLE:
            return None, None
        
        X, y = [], []
        for i in range(len(features) - self.sequence_length):
            X.append(features[i:i+self.sequence_length])
            y.append(labels[i+self.sequence_length])
        
        return torch.FloatTensor(X).to(self.device), torch.LongTensor(y).to(self.device)
    
    async def _predict_model(self, features: np.ndarray) -> Dict[str, Any]:
        """Make prediction using trained LSTM model"""
        if not ML_AVAILABLE:
            return {
                "risk_level": RiskLevel.MEDIUM,
                "probability": 0.5,
                "confidence": 0.8
            }
        
        # Use last sequence_length points for prediction
        if len(features) < self.sequence_length:
            # Pad with zeros if not enough data
            padded_features = np.zeros((self.sequence_length, features.shape[1]))
            padded_features[-len(features):] = features
            features = padded_features
        else:
            features = features[-self.sequence_length:]
        
        X = torch.FloatTensor(features).unsqueeze(0).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(X)
            probabilities = torch.softmax(outputs, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1).item()
            confidence = torch.max(probabilities).item()
        
        risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        return {
            "risk_level": risk_levels[predicted_class],
            "probability": probabilities[0][predicted_class].item(),
            "confidence": confidence
        }


class RandomForestRiskClassifier(RiskAssessmentModel):
    """Random Forest risk classification model"""
    
    def __init__(self, n_estimators: int = 100, max_depth: int = 10):
        super().__init__("RandomForestRiskClassifier", "1.0.0")
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        
    async def _train_model(self, features: np.ndarray, labels: np.ndarray):
        """Train Random Forest model"""
        if not ML_AVAILABLE:
            return
        
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=42
        )
        self.model.fit(features, labels)
        
    async def _predict_model(self, features: np.ndarray) -> Dict[str, Any]:
        """Make prediction using trained Random Forest model"""
        if not ML_AVAILABLE:
            return {
                "risk_level": RiskLevel.MEDIUM,
                "probability": 0.5,
                "confidence": 0.8
            }
        
        # Get prediction and probabilities
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        
        risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        predicted_risk = risk_levels[prediction]
        confidence = max(probabilities)
        
        return {
            "risk_level": predicted_risk,
            "probability": probabilities[prediction],
            "confidence": confidence
        }


class AnomalyDetector(RiskAssessmentModel):
    """Anomaly detection model using Isolation Forest"""
    
    def __init__(self, contamination: float = 0.1):
        super().__init__("AnomalyDetector", "1.0.0")
        self.contamination = contamination
        self.threshold = 0.0
        
    async def _train_model(self, features: np.ndarray, labels: np.ndarray):
        """Train Isolation Forest model"""
        if not ML_AVAILABLE:
            return
        
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42
        )
        self.model.fit(features)
        
        # Calculate threshold
        scores = self.model.decision_function(features)
        self.threshold = np.percentile(scores, self.contamination * 100)
        
    async def detect_anomaly(self, features: Dict[str, float]) -> AnomalyResult:
        """Detect anomalies in input features"""
        if not self.is_trained:
            raise ValueError(f"Model {self.model_name} is not trained")
        
        try:
            if not ML_AVAILABLE:
                return AnomalyResult(
                    is_anomaly=False,
                    anomaly_score=0.0,
                    threshold=self.threshold,
                    timestamp=datetime.now(),
                    features=features
                )
            
            # Prepare features
            feature_values = [features.get(name, 0.0) for name in self.feature_names]
            feature_array = np.array(feature_values).reshape(1, -1)
            feature_scaled = self.scaler.transform(feature_array)
            
            # Detect anomaly
            anomaly_score = self.model.decision_function(feature_scaled)[0]
            is_anomaly = anomaly_score < self.threshold
            
            return AnomalyResult(
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                threshold=self.threshold,
                timestamp=datetime.now(),
                features=features
            )
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return AnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                threshold=self.threshold,
                timestamp=datetime.now(),
                features=features
            )
    
    async def _predict_model(self, features: np.ndarray) -> Dict[str, Any]:
        """Not used for anomaly detection"""
        anomaly_result = await self.detect_anomaly(
            {name: features[0][i] for i, name in enumerate(self.feature_names)}
        )
        
        return {
            "risk_level": RiskLevel.HIGH if anomaly_result.is_anomaly else RiskLevel.LOW,
            "probability": 1.0 if anomaly_result.is_anomaly else 0.0,
            "confidence": abs(anomaly_result.anomaly_score)
        }


# Neural Network Models
if ML_AVAILABLE:
    class LSTMModel(nn.Module):
        """LSTM neural network for time series prediction"""
        
        def __init__(self, input_size: int, hidden_size: int, num_classes: int):
            super(LSTMModel, self).__init__()
            self.hidden_size = hidden_size
            self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
            self.fc = nn.Linear(hidden_size, num_classes)
            self.dropout = nn.Dropout(0.2)
            
        def forward(self, x):
            lstm_out, _ = self.lstm(x)
            last_output = lstm_out[:, -1, :]
            dropped = self.dropout(last_output)
            output = self.fc(dropped)
            return output


class ModelEnsemble:
    """Ensemble of multiple risk assessment models"""
    
    def __init__(self, models: List[RiskAssessmentModel]):
        self.models = models
        self.weights = [1.0 / len(models)] * len(models)  # Equal weights initially
        
    async def train_all(self, data: pd.DataFrame, target: str) -> Dict[str, Any]:
        """Train all models in the ensemble"""
        results = {}
        
        for i, model in enumerate(self.models):
            result = await model.train(data, target)
            results[f"model_{i}_{model.model_name}"] = result
            
        return results
    
    async def predict_ensemble(self, features: Dict[str, float]) -> RiskPrediction:
        """Make ensemble prediction"""
        predictions = []
        
        for model in self.models:
            if model.is_trained:
                pred = await model.predict(features)
                predictions.append(pred)
        
        if not predictions:
            raise ValueError("No trained models available for prediction")
        
        # Weighted average of predictions
        risk_scores = {
            RiskLevel.LOW: 0.0,
            RiskLevel.MEDIUM: 0.0,
            RiskLevel.HIGH: 0.0,
            RiskLevel.CRITICAL: 0.0
        }
        
        total_weight = 0.0
        for i, pred in enumerate(predictions):
            weight = self.weights[i] if i < len(self.weights) else 1.0
            risk_scores[pred.risk_level] += pred.probability * weight
            total_weight += weight
        
        # Normalize scores
        for level in risk_scores:
            risk_scores[level] /= total_weight
        
        # Get highest scoring risk level
        predicted_level = max(risk_scores, key=risk_scores.get)
        confidence = sum(p.confidence for p in predictions) / len(predictions)
        
        return RiskPrediction(
            risk_level=predicted_level,
            probability=risk_scores[predicted_level],
            confidence=confidence,
            factors=features,
            timestamp=datetime.now(),
            model_version="ensemble_1.0.0"
        )
    
    async def update_weights(self, performance_metrics: List[Dict[str, float]]):
        """Update model weights based on performance"""
        if len(performance_metrics) != len(self.models):
            return
        
        # Update weights based on F1 score
        f1_scores = [metrics.get('f1_score', 0.0) for metrics in performance_metrics]
        total_f1 = sum(f1_scores)
        
        if total_f1 > 0:
            self.weights = [score / total_f1 for score in f1_scores]
        
        logger.info(f"Updated ensemble weights: {self.weights}")


# Utility functions for model management
async def create_risk_model(model_type: str, **kwargs) -> RiskAssessmentModel:
    """Factory function to create risk models"""
    if model_type == "timeseries":
        return TimeSeriesPredictor(**kwargs)
    elif model_type == "random_forest":
        return RandomForestRiskClassifier(**kwargs)
    elif model_type == "anomaly_detector":
        return AnomalyDetector(**kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


async def load_training_data(data_path: str) -> pd.DataFrame:
    """Load training data from file"""
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Training data not found: {data_path}")
    
    return pd.read_csv(data_path)


async def save_model(model: RiskAssessmentModel, model_path: str):
    """Save trained model to file"""
    import pickle
    
    model_data = {
        'model_name': model.model_name,
        'model_version': model.model_version,
        'is_trained': model.is_trained,
        'feature_names': model.feature_names,
        'training_history': model.training_history
    }
    
    # Save model-specific data
    if hasattr(model, 'model') and model.model is not None:
        if ML_AVAILABLE and hasattr(model.model, 'state_dict'):
            # PyTorch model
            torch.save(model.model.state_dict(), f"{model_path}.pth")
        elif ML_AVAILABLE:
            # Scikit-learn model
            with open(f"{model_path}.pkl", 'wb') as f:
                pickle.dump(model.model, f)
    
    # Save scaler
    if model.scaler is not None:
        with open(f"{model_path}_scaler.pkl", 'wb') as f:
            pickle.dump(model.scaler, f)
    
    # Save metadata
    with open(f"{model_path}_metadata.json", 'w') as f:
        json.dump(model_data, f, indent=2)
    
    logger.info(f"Model saved: {model_path}")


async def load_model(model_path: str, model_type: str) -> RiskAssessmentModel:
    """Load trained model from file"""
    import pickle
    
    # Load metadata
    with open(f"{model_path}_metadata.json", 'r') as f:
        model_data = json.load(f)
    
    # Create model instance
    model = await create_risk_model(model_type)
    model.model_name = model_data['model_name']
    model.model_version = model_data['model_version']
    model.is_trained = model_data['is_trained']
    model.feature_names = model_data['feature_names']
    model.training_history = model_data['training_history']
    
    # Load scaler
    scaler_path = f"{model_path}_scaler.pkl"
    if Path(scaler_path).exists():
        with open(scaler_path, 'rb') as f:
            model.scaler = pickle.load(f)
    
    # Load model
    if model_type == "timeseries":
        model_file = f"{model_path}.pth"
        if Path(model_file).exists() and ML_AVAILABLE:
            model.model = LSTMModel(len(model.feature_names), model.hidden_size, 4)
            model.model.load_state_dict(torch.load(model_file))
    else:
        model_file = f"{model_path}.pkl"
        if Path(model_file).exists():
            with open(model_file, 'rb') as f:
                model.model = pickle.load(f)
    
    logger.info(f"Model loaded: {model_path}")
    return model