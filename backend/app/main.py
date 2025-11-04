# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

from .routes_auth_poc import router as auth_poc_router
from . import ml_models
# import other routers if you have them, e.g. score_router = ...
# from .routers.score import router as score_router

app = FastAPI(title="Login Fraud Scoring POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev; lock this down in prod
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth_poc_router)
# app.include_router(score_router)
# app.include_router(other_router)

# --- ML Model Startup ---
@app.on_event("startup")
def train_models_on_startup():
    """Train ANN model on startup (can train others on demand)"""
    ml_models.train_algorithm("ann", force_retrain=False)

# --- /score endpoint ---
@app.post("/score")
async def score(payload: dict, algorithm: Optional[str] = Query(None, description="Algorithm to use: ann, svm, knn")):
    """Score a transaction for fraud risk"""
    algo = algorithm or ml_models._active_algorithm
    
    if not ml_models.is_ready(algo):
        return JSONResponse(status_code=503, content={"error": f"model {algo} not loaded"})
    
    try:
        result = ml_models.predict_fraud(payload, algo)
        score = result["score"]
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    
    # Apply decision thresholds
    if score < 0.25:
        decision = "allow"
    elif score < 0.60:
        decision = "challenge"
    else:
        decision = "block"
    
    return {
        "score": score,
        "decision": decision,
        "algorithm": result["algorithm"],
        "confidence": result["confidence"],
        "model_version": "v1.0"
    }

# --- /metrics endpoint ---
@app.get("/metrics")
async def metrics(algorithm: Optional[str] = Query(None, description="Algorithm: ann, svm, knn")):
    """Get model performance metrics"""
    algo = algorithm or ml_models._active_algorithm
    
    if not ml_models.is_ready(algo):
        return JSONResponse(status_code=503, content={"error": f"model {algo} not loaded"})
    
    return ml_models.get_metrics(algo)

# --- /algorithms endpoint ---
@app.get("/algorithms")
async def list_algorithms():
    """List available ML algorithms"""
    available = ml_models.get_available_algorithms()
    return {
        "algorithms": ["ann", "svm", "knn"],
        "available": available,
        "active": ml_models._active_algorithm
    }

# --- /train endpoint ---
@app.post("/train/{algorithm}")
async def train_model(algorithm: str, force_retrain: bool = Query(False, description="Force retrain even if model exists")):
    """Train a specific algorithm"""
    if algorithm not in ["ann", "svm", "knn"]:
        return JSONResponse(status_code=400, content={"error": f"Unknown algorithm: {algorithm}"})
    
    success = ml_models.train_algorithm(algorithm, force_retrain=force_retrain)
    
    if success:
        metrics = ml_models.get_metrics(algorithm)
        return {
            "status": "success",
            "algorithm": algorithm,
            "metrics": metrics
        }
    else:
        return JSONResponse(status_code=500, content={"error": f"Training failed for {algorithm}"})

# --- /select endpoint ---
@app.post("/select/{algorithm}")
async def select_algorithm(algorithm: str):
    """Set the active algorithm for scoring"""
    if algorithm not in ["ann", "svm", "knn"]:
        return JSONResponse(status_code=400, content={"error": f"Unknown algorithm: {algorithm}"})
    
    success = ml_models.set_active_algorithm(algorithm)
    
    if success:
        return {
            "status": "success",
            "active_algorithm": algorithm,
            "message": f"{algorithm.upper()} is now the active algorithm"
        }
    else:
        return JSONResponse(status_code=500, content={"error": f"Failed to activate {algorithm}"})

@app.get("/healthz")
def health():
    return {"status": "ok"}
