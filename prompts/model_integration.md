# Prompt: Integrate Real Model + Training Script

Create:
- backend/ml/train.py with a synthetic training pipeline using XGBoost
- backend/ml/model.py exposing:
   - load_model()
   - predict_score(payload)->float
   - deterministic fallback if model missing

Modify:
- backend/app/main.py to call predict_score() instead of fake model
- backend/requirements.txt add numpy, pandas, scikit-learn, xgboost, joblib, shap

Add Make targets:
- make train
- make eval

Output only unified diffs. Wait for my approval to apply.
