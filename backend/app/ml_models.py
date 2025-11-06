# ----------------------------
# ML Models for Fraud Detection (Refactored)
# ----------------------------
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
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score, average_precision_score
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATA_PATH = os.environ.get("DATA_PATH", os.path.join(os.path.dirname(__file__), "../data/creditcard.csv"))
MODEL_DIR = os.path.join(os.path.dirname(__file__), "../models")
os.makedirs(MODEL_DIR, exist_ok=True)

_models: Dict[str, Tuple] = {}  # algorithm_name -> (model, scaler, feature_order, metrics)
_active_algorithm = "ann"


# ----------------------------
# Helper Functions
# ----------------------------
def get_model_path(algorithm: str) -> str:
    return os.path.join(MODEL_DIR, f"{algorithm.lower()}_model.pkl")


def load_and_preprocess_data() -> Tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(DATA_PATH)
    if 'Class' not in df.columns:
        raise ValueError("'Class' column not found in dataset")
    X = df.drop(columns=['Class'])
    y = df['Class']
    return X, y


def preprocess_and_split(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42):
    feature_order = list(X.columns)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, stratify=y, random_state=random_state)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, feature_order


# ----------------------------
# Training Functions
# ----------------------------
def train_ann(X_train, y_train, hidden_layers=(64, 32), max_iter=30):
    model = MLPClassifier(hidden_layer_sizes=hidden_layers, activation='relu', solver='adam',
                          max_iter=max_iter, early_stopping=True, random_state=42)
    model.fit(X_train, y_train)
    return model


def train_svm(X_train, y_train, kernel='rbf', C=1.0):
    try:
        model = SVC(kernel=kernel, C=C, probability=True, random_state=42)
        model.fit(X_train, y_train)
        return model
    except Exception as e:
        logger.error(f"SVM training failed: {e}")
        raise


def train_knn(X_train, y_train, n_neighbors=5):
    model = KNeighborsClassifier(n_neighbors=n_neighbors, weights='distance', algorithm='auto')
    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test, y_test) -> Dict[str, Any]:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
        "confusion_matrix": {
            "tn": int(confusion_matrix(y_test, y_pred)[0,0]),
            "fp": int(confusion_matrix(y_test, y_pred)[0,1]),
            "fn": int(confusion_matrix(y_test, y_pred)[1,0]),
            "tp": int(confusion_matrix(y_test, y_pred)[1,1])
        },
        "n_test": int(len(y_test)),
        "n_fraud": int(y_test.sum()),
        "n_valid": int(len(y_test) - y_test.sum())
    }

    if y_proba is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba))
            metrics["pr_auc"] = float(average_precision_score(y_test, y_proba))
        except Exception as e:
            logger.warning(f"AUC calculation failed: {e}")

    return metrics


def save_model(algorithm: str, model, scaler, feature_order, metrics):
    model_path = get_model_path(algorithm)
    with open(model_path, 'wb') as f:
        pickle.dump({"model": model, "scaler": scaler, "feature_order": feature_order, "metrics": metrics}, f)
    logger.info(f"{algorithm.upper()} model saved at {model_path}")


def load_model(algorithm: str) -> Optional[Tuple]:
    model_path = get_model_path(algorithm)
    if not os.path.exists(model_path):
        return None
    try:
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        return data["model"], data["scaler"], data["feature_order"], data["metrics"]
    except Exception as e:
        logger.error(f"Failed to load {algorithm}: {e}")
        return None


def train_algorithm(algorithm: str, force_retrain: bool = False) -> bool:
    global _models
    algorithm = algorithm.lower()

    if not force_retrain:
        loaded = load_model(algorithm)
        if loaded:
            _models[algorithm] = loaded
            return True

    try:
        X, y = load_and_preprocess_data()
        X_train, X_test, y_train, y_test, scaler, feature_order = preprocess_and_split(X, y)

        if algorithm == "ann":
            model = train_ann(X_train, y_train)
        elif algorithm == "svm":
            model = train_svm(X_train, y_train)
        elif algorithm == "knn":
            model = train_knn(X_train, y_train)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        metrics = evaluate_model(model, X_test, y_test)
        _models[algorithm] = (model, scaler, feature_order, metrics)
        save_model(algorithm, model, scaler, feature_order, metrics)

        logger.info(f"{algorithm.upper()} trained successfully")
        return True
    except Exception as e:
        logger.error(f"Training failed for {algorithm}: {e}")
        return False


# ----------------------------
# Active Algorithm Management
# ----------------------------
def set_active_algorithm(algorithm: str) -> bool:
    global _active_algorithm
    algorithm = algorithm.lower()
    if algorithm not in ["ann", "svm", "knn"]:
        logger.error(f"Invalid algorithm: {algorithm}")
        return False

    if algorithm not in _models:
        logger.info(f"{algorithm.upper()} model not loaded. Training on-demand...")
        if not train_algorithm(algorithm):
            logger.error(f"Failed to load/train {algorithm}")
            return False

    _active_algorithm = algorithm
    logger.info(f"Active algorithm set to {algorithm.upper()}")
    return True


def is_ready(algorithm: Optional[str] = None) -> bool:
    algo = (algorithm or _active_algorithm).lower()
    return algo in _models and _models[algo] is not None


def predict_fraud(payload: dict, algorithm: Optional[str] = None) -> Dict[str, Any]:
    algo = (algorithm or _active_algorithm).lower()
    if not is_ready(algo):
        raise RuntimeError(f"Model {algo} not loaded")

    model, scaler, feature_order, _ = _models[algo]

    # Ensure payload aligns with original feature names
    X_row = np.array([payload.get(f, 0.0) for f in feature_order]).reshape(1, -1)
    X_scaled = scaler.transform(X_row)

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_scaled)[0, 1]
    else:
        proba = float(model.predict(X_scaled)[0])

    return {
        "score": float(proba),
        "algorithm": algo,
        "confidence": float(proba) if proba > 0.5 else float(1 - proba)
    }


def get_metrics(algorithm: Optional[str] = None) -> Dict[str, Any]:
    algo = (algorithm or _active_algorithm).lower()
    if not is_ready(algo):
        return {"error": f"Model {algo} not loaded"}
    _, _, _, metrics = _models[algo]
    return metrics


def get_available_algorithms() -> list:
    return [algo for algo in ["ann", "svm", "knn"] if os.path.exists(get_model_path(algo)) or algo in _models]
