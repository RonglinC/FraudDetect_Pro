"""
ML Models for Fraud Detection
Implements ANN, SVM, and KNN classifiers with training, testing, and persistence.
"""
import os
import pickle
import logging
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, average_precision_score
)
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Paths
DATA_PATH = os.environ.get("DATA_PATH", os.path.join(os.path.dirname(__file__), "../data/creditcard.csv"))
MODEL_DIR = os.path.join(os.path.dirname(__file__), "../models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Global state
_models = {}  # algorithm_name -> (model, scaler, feature_order, metrics)
_active_algorithm = "ann"  # default


def get_model_path(algorithm: str) -> str:
    """Get the file path for a saved model."""
    return os.path.join(MODEL_DIR, f"{algorithm}_model.pkl")


def load_and_preprocess_data() -> Tuple[pd.DataFrame, pd.Series]:
    """
    Step 1-2: Load dataset and observe
    Returns features (X) and target (y)
    """
    logger.info(f"Loading dataset from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    
    if 'Class' not in df.columns:
        raise ValueError("'Class' column not found in dataset")
    
    # Separate features and target
    X = df.drop(columns=['Class'])
    y = df['Class']
    
    logger.info(f"Dataset loaded: {len(df)} samples, {len(X.columns)} features")
    logger.info(f"Class distribution - Fraud: {y.sum()}, Normal: {len(y) - y.sum()}")
    
    return X, y


def preprocess_and_split(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42):
    """
    Step 3: Data preprocessing - scaling, normalization, and splitting
    Returns: X_train, X_test, y_train, y_test, scaler, feature_order
    """
    feature_order = list(X.columns)
    
    # Split data (stratified to maintain class balance)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    
    # Scale and normalize data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    logger.info(f"Data split - Train: {len(X_train)}, Test: {len(X_test)}")
    
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, feature_order


def train_ann(X_train, y_train, hidden_layers=(64, 32), max_iter=30):
    """
    Step 4: Train ANN model
    Dense layers with activation function
    """
    logger.info(f"Training ANN with hidden layers {hidden_layers}")
    
    model = MLPClassifier(
        hidden_layer_sizes=hidden_layers,
        activation='relu',
        solver='adam',
        max_iter=max_iter,
        early_stopping=True,
        random_state=42,
        verbose=False
    )
    
    model.fit(X_train, y_train)
    logger.info("ANN training complete")
    
    return model


def train_svm(X_train, y_train, kernel='rbf', C=1.0):
    """
    Step 4: Train SVM classifier
    """
    logger.info(f"Training SVM with kernel={kernel}, C={C}")
    
    model = SVC(
        kernel=kernel,
        C=C,
        probability=True,  # enable probability estimates
        random_state=42,
        verbose=False
    )
    
    model.fit(X_train, y_train)
    logger.info("SVM training complete")
    
    return model


def train_knn(X_train, y_train, n_neighbors=5):
    """
    Step 4: Train KNN classifier
    """
    logger.info(f"Training KNN with n_neighbors={n_neighbors}")
    
    model = KNeighborsClassifier(
        n_neighbors=n_neighbors,
        weights='distance',  # weight by inverse distance
        algorithm='auto'
    )
    
    model.fit(X_train, y_train)
    logger.info("KNN training complete")
    
    return model


def evaluate_model(model, X_test, y_test) -> Dict[str, Any]:
    """
    Step 5: Calculate metrics (accuracy, precision, recall, F1, confusion matrix, AUC)
    """
    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)
    
    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "confusion_matrix": {
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1])
        },
        "n_test": int(len(y_test)),
        "n_fraud": int(y_test.sum()),
        "n_valid": int(len(y_test) - y_test.sum())
    }
    
    # Add AUC metrics if probabilities available
    if y_proba is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba))
            metrics["pr_auc"] = float(average_precision_score(y_test, y_proba))
        except Exception as e:
            logger.warning(f"Could not calculate AUC: {e}")
    
    logger.info(f"Metrics - Accuracy: {accuracy:.4f}, Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")
    
    return metrics


def save_model(algorithm: str, model, scaler, feature_order, metrics):
    """
    Save trained model to disk for later use
    """
    model_path = get_model_path(algorithm)
    
    model_data = {
        "model": model,
        "scaler": scaler,
        "feature_order": feature_order,
        "metrics": metrics
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    logger.info(f"Model saved to {model_path}")


def load_model(algorithm: str) -> Optional[Tuple]:
    """
    Load a previously trained model from disk
    Returns: (model, scaler, feature_order, metrics) or None
    """
    model_path = get_model_path(algorithm)
    
    if not os.path.exists(model_path):
        logger.warning(f"No saved model found at {model_path}")
        return None
    
    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        logger.info(f"Model loaded from {model_path}")
        return (
            model_data["model"],
            model_data["scaler"],
            model_data["feature_order"],
            model_data["metrics"]
        )
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None


def train_algorithm(algorithm: str, force_retrain: bool = False) -> bool:
    """
    Main training function for any algorithm
    
    Args:
        algorithm: 'ann', 'svm', or 'knn'
        force_retrain: If False, will load existing model if available
    
    Returns:
        True if successful, False otherwise
    """
    global _models
    
    # Try to load existing model first
    if not force_retrain:
        loaded = load_model(algorithm)
        if loaded is not None:
            _models[algorithm] = loaded
            logger.info(f"Using pre-trained {algorithm.upper()} model")
            return True
    
    try:
        # Step 1-2: Load and observe data
        X, y = load_and_preprocess_data()
        
        # Step 3: Preprocess and split
        X_train, X_test, y_train, y_test, scaler, feature_order = preprocess_and_split(X, y)
        
        # Step 4: Train model based on algorithm
        if algorithm == 'ann':
            model = train_ann(X_train, y_train)
        elif algorithm == 'svm':
            model = train_svm(X_train, y_train)
        elif algorithm == 'knn':
            model = train_knn(X_train, y_train)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Step 5: Evaluate and calculate metrics
        metrics = evaluate_model(model, X_test, y_test)
        metrics["algorithm"] = algorithm
        metrics["n_train"] = int(len(y_train))
        
        # Store in memory
        _models[algorithm] = (model, scaler, feature_order, metrics)
        
        # Save to disk
        save_model(algorithm, model, scaler, feature_order, metrics)
        
        logger.info(f"{algorithm.upper()} training complete and saved")
        print(f"[{algorithm.upper()}] Accuracy: {metrics['accuracy']:.4f}, Precision: {metrics['precision']:.4f}, Recall: {metrics['recall']:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Training failed for {algorithm}: {e}")
        return False


def set_active_algorithm(algorithm: str) -> bool:
    """Set the active algorithm for predictions"""
    global _active_algorithm
    
    if algorithm not in ['ann', 'svm', 'knn']:
        logger.error(f"Invalid algorithm: {algorithm}")
        return False
    
    # Ensure model is loaded
    if algorithm not in _models:
        success = train_algorithm(algorithm, force_retrain=False)
        if not success:
            return False
    
    _active_algorithm = algorithm
    logger.info(f"Active algorithm set to {algorithm.upper()}")
    return True


def is_ready(algorithm: Optional[str] = None) -> bool:
    """Check if a model is ready for predictions"""
    algo = algorithm or _active_algorithm
    return algo in _models and _models[algo] is not None


def predict_fraud(payload: dict, algorithm: Optional[str] = None) -> Dict[str, Any]:
    """
    Predict fraud probability for a transaction
    
    Args:
        payload: dict with transaction features (Time, Amount, V1-V28)
        algorithm: optional algorithm name (defaults to active)
    
    Returns:
        dict with score, decision, algorithm, and confidence
    """
    algo = algorithm or _active_algorithm
    
    if not is_ready(algo):
        raise RuntimeError(f"Model {algo} not loaded")
    
    model, scaler, feature_order, metrics = _models[algo]
    
    # Build feature vector in correct order
    row = [payload.get(f, 0.0) for f in feature_order]
    X = np.array(row).reshape(1, -1)
    X_scaled = scaler.transform(X)
    
    # Predict
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(X_scaled)[0, 1]
    else:
        # Fallback for models without probability
        pred = model.predict(X_scaled)[0]
        proba = float(pred)
    
    return {
        "score": float(proba),
        "algorithm": algo,
        "confidence": float(proba) if proba > 0.5 else float(1 - proba)
    }


def get_metrics(algorithm: Optional[str] = None) -> Dict[str, Any]:
    """Get metrics for a trained model"""
    algo = algorithm or _active_algorithm
    
    if not is_ready(algo):
        return {"error": f"Model {algo} not loaded"}
    
    _, _, _, metrics = _models[algo]
    return metrics


def get_available_algorithms() -> list:
    """Get list of trained/available algorithms"""
    available = []
    for algo in ['ann', 'svm', 'knn']:
        if os.path.exists(get_model_path(algo)) or algo in _models:
            available.append(algo)
    return available
