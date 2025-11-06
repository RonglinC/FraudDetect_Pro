# backend/main.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import sqlite3

from .routes_auth_poc import router as auth_poc_router
from . import ml_models

app = FastAPI(title="Login Fraud Scoring POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev; lock down in prod
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth_poc_router)

# --- ML Model Startup ---
@app.on_event("startup")
def train_models_on_startup():
    """Train or load the ANN model at startup."""
    ml_models.train_algorithm("ann", force_retrain=False)


DB_PATH = "users.db"  # Adjust if your DB file lives elsewhere


@app.post("/login_user")
def login_user(payload: dict):
    """Authenticate a user using the SQLite database."""
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username or password")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"user_id": row[0]}


@app.get("/transactions/{user_id}")
def get_transactions(user_id: int):
    """Fetch a user's transaction history from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    columns = [desc[0] for desc in cur.description]
    data = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()
    return {"transactions": data}

@app.get("/transactions/by_username/{username}")
def get_transactions_by_username(username: str):
    """Fetch transactions for a given username."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Find user ID
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    user_id = user[0]

    # Fetch transactions for that user
    cur.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    columns = [desc[0] for desc in cur.description]
    data = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()

    return {"transactions": data}



@app.post("/detect_fraud/{user_id}")
def detect_fraud(user_id: int):
    """Run fraud detection on a user's transactions using the active model."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No transactions found for this user")

    # Extract features (skip first two columns: id, user_id)
    try:
        feature_matrix = [list(map(float, r[2:])) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error preparing features: {e}")

    algo = ml_models._active_algorithm
    if not ml_models.is_ready(algo):
        raise HTTPException(status_code=503, detail=f"Model {algo} not loaded")

    # Run model inference
    predictions = []
    for features in feature_matrix:
        payload = {f"feature_{i}": val for i, val in enumerate(features)}
        result = ml_models.predict_fraud(payload, algo)
        predictions.append({
            "score": result["score"],
            "decision": (
                "allow" if result["score"] < 0.25
                else "challenge" if result["score"] < 0.6
                else "block"
            ),
            "confidence": result["confidence"],
            "algorithm": result["algorithm"]
        })

    return {"user_id": user_id, "results": predictions}


# ============================================================
# Existing Endpoints
# ============================================================

@app.post("/score")
async def score(payload: dict, algorithm: Optional[str] = Query(None, description="Algorithm to use: ann, svm, knn")):
    algo = algorithm or ml_models._active_algorithm

    if not ml_models.is_ready(algo):
        return JSONResponse(status_code=503, content={"error": f"model {algo} not loaded"})

    try:
        result = ml_models.predict_fraud(payload, algo)
        score = result["score"]
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    decision = (
        "allow" if score < 0.25
        else "challenge" if score < 0.60
        else "block"
    )

    return {
        "score": score,
        "decision": decision,
        "algorithm": result["algorithm"],
        "confidence": result["confidence"],
        "model_version": "v1.0"
    }


@app.get("/metrics")
async def metrics(algorithm: Optional[str] = Query(None, description="Algorithm: ann, svm, knn")):
    algo = algorithm or ml_models._active_algorithm

    if not ml_models.is_ready(algo):
        return JSONResponse(status_code=503, content={"error": f"model {algo} not loaded"})

    return ml_models.get_metrics(algo)


@app.get("/algorithms")
async def list_algorithms():
    available = ml_models.get_available_algorithms()
    return {
        "algorithms": ["ann", "svm", "knn"],
        "available": available,
        "active": ml_models._active_algorithm
    }


@app.post("/train/{algorithm}")
async def train_model(algorithm: str, force_retrain: bool = Query(False, description="Force retrain even if model exists")):
    if algorithm not in ["ann", "svm", "knn"]:
        return JSONResponse(status_code=400, content={"error": f"Unknown algorithm: {algorithm}"})

    success = ml_models.train_algorithm(algorithm, force_retrain=force_retrain)

    if success:
        metrics = ml_models.get_metrics(algorithm)
        return {"status": "success", "algorithm": algorithm, "metrics": metrics}
    else:
        return JSONResponse(status_code=500, content={"error": f"Training failed for {algorithm}"})


@app.post("/select/{algorithm}")
async def select_algorithm(algorithm: str):
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
