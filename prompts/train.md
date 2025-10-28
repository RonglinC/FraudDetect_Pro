# Prompt: Train ANN at startup and serve via /score (no artifacts)

Goal
Train a small ANN (scikit-learn MLPClassifier) on creditcard.csv when FastAPI starts, keep it in memory, and use it for /score. No model files saved.

Dataset
- Default path: backend/data/creditcard.csv

Tasks

1) Create backend/app/ann_runtime.py:
   - Globals: _model, _feature_order, _metrics
   - load_and_train_model():
       * load CSV from DATA_PATH or default
       * split: stratified (test_size=0.2, random_state=42)
       * pipeline = StandardScaler -> MLPClassifier(
            hidden_layer_sizes=(64,32),
            activation='relu',
            solver='adam',
            max_iter=30,
            early_stopping=True,
            random_state=42
         )
       * fit on train
       * compute PR-AUC (average_precision_score) and ROC-AUC on test
       * store _model, feature order (all columns except 'Class'), and metrics in _metrics
       * print/log PR-AUC and ROC-AUC
       * return True on success, False if data missing
   - is_ready() -> bool (model loaded)
   - predict_proba(payload: dict) -> float:
       * build a single-row DataFrame in exact feature order
       * return probability of class 1

2) Wire into FastAPI (backend/app/main.py or existing module):
   - On startup event: call load_and_train_model()
   - POST /score accepts numeric fields: Time, Amount, V1..V28
       * if not is_ready(): return 503 with {"error":"model not loaded"}
       * score = predict_proba(payload)
       * decision thresholds:
            allow if score < 0.25
            challenge if 0.25 <= score < 0.60
            block if score >= 0.60
       * return {"score": float, "decision": str, "model_version": "ann_poc"}
   - GET /metrics returns _metrics (pr_auc, roc_auc, n_train, n_test)

3) Makefile (repo root):
   - add target `score-ann` that POSTs a minimal dummy payload to /score
   - add target `metrics` that GETs /metrics

Constraints
- Use only pandas, numpy, scikit-learn, joblib not required
- Keep startup < ~2 minutes
- Clean, readable logging; no dependencies added beyond what’s already installed

Deliverables
- Show unified diffs only, ask for confirmation before applying
