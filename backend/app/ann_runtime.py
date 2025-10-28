import os
import logging
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

# Globals
_model = None
_feature_order = None
_metrics = {}

DATA_PATH = os.environ.get("DATA_PATH", os.path.join(os.path.dirname(__file__), "../data/creditcard.csv"))


def load_and_train_model():
    global _model, _feature_order, _metrics
    try:
        df = pd.read_csv(DATA_PATH)
    except Exception as e:
        logging.error(f"Failed to load data: {e}")
        _model = None
        return False
    if 'Class' not in df.columns:
        logging.error("'Class' column missing in data")
        _model = None
        return False
    X = df.drop(columns=['Class'])
    y = df['Class']
    _feature_order = list(X.columns)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    clf = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        activation='relu',
        solver='adam',
        max_iter=30,
        early_stopping=True,
        random_state=42
    )
    clf.fit(X_train_scaled, y_train)
    y_proba = clf.predict_proba(X_test_scaled)[:, 1]
    pr_auc = average_precision_score(y_test, y_proba)
    roc_auc = roc_auc_score(y_test, y_proba)
    _model = (clf, scaler)
    _metrics = {
        "pr_auc": float(pr_auc),
        "roc_auc": float(roc_auc),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
    }
    logging.info(f"ANN PR-AUC: {pr_auc:.4f}, ROC-AUC: {roc_auc:.4f}")
    print(f"[ANN] PR-AUC: {pr_auc:.4f}, ROC-AUC: {roc_auc:.4f}")
    return True

def is_ready():
    return _model is not None and _feature_order is not None

def predict_proba(payload: dict) -> float:
    if not is_ready():
        raise RuntimeError("Model not loaded")
    clf, scaler = _model
    # Ensure all features are present in correct order
    row = [payload.get(f, 0.0) for f in _feature_order]
    X = np.array(row).reshape(1, -1)
    X_scaled = scaler.transform(X)
    proba = clf.predict_proba(X_scaled)[0, 1]
    return float(proba)
