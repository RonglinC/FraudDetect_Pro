from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sqlite3
from pathlib import Path
import logging

from . import ml_models
from .routes_auth_poc import router as auth_poc_router
from .routers.chatbot import router as chatbot_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Login Fraud Scoring POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev; restrict in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_poc_router)
app.include_router(chatbot_router)

# ----------------------------
# Database
# ----------------------------
DB_PATH = str(Path(__file__).resolve().parents[1] / "users.db")

# ----------------------------
# Startup: load/train ANN model
# ----------------------------
@app.on_event("startup")
def train_models_on_startup():
    """Train or load ANN model at startup"""
    # Force retrain to fix sklearn version compatibility issues
    success = ml_models.train_algorithm("ann", force_retrain=True)
    if success:
        logger.info("Startup: ANN model ready")
    else:
        logger.error("Startup: Failed to load/train ANN model")

# ----------------------------
# User Authentication
# ----------------------------
@app.post("/login_user")
def login_user(payload: dict):
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

# ----------------------------
# Transaction Endpoints
# ----------------------------
@app.get("/transactions/{user_id}")
def get_transactions(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    columns = [desc[0] for desc in cur.description]
    data = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()
    return {"transactions": data}

@app.get("/transactions/by_username/{username}")
def get_transactions_by_username(username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    user_id = user[0]
    cur.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    columns = [desc[0] for desc in cur.description]
    data = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()
    return {"transactions": data}

# ----------------------------
# Fraud Detection
# ----------------------------
@app.post("/detect_fraud/{user_id}")
def detect_fraud(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id=?", (user_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No transactions found for this user")

    # Prepare features (skip id and user_id)
    try:
        feature_matrix = [list(map(float, r[2:])) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error preparing features: {e}")

    algo = ml_models._active_algorithm
    if not ml_models.is_ready(algo):
        raise HTTPException(status_code=503, detail=f"Model {algo} not loaded")

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

# ----------------------------
# Homepage transactions for template
# ----------------------------
@app.get("/homepage/transactions/{username}")
def get_homepage_transactions(username: str, limit: int = Query(10, ge=1, le=50)):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_row = cur.fetchone()
        if not user_row:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute("""
            SELECT id, txn_time, amount, merchant, location, is_fraud
            FROM transactions
            WHERE user_id = ?
            ORDER BY txn_time DESC
            LIMIT ?
        """, (user_row["id"], limit))

        transactions = []
        for row in cur.fetchall():
            transactions.append([
                row["id"],
                row["txn_time"][:16].replace("T", " "),
                f"{row['amount']:.2f}",
                row["merchant"] or "Unknown",
                row["location"] or "Unknown",
                "FRAUD" if row["is_fraud"] else "SAFE"
            ])
        conn.close()
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ----------------------------
# Score endpoint
# ----------------------------
@app.post("/score")
async def score(payload: dict, algorithm: Optional[str] = Query(None)):
    algo = algorithm or ml_models._active_algorithm

    if not ml_models.is_ready(algo):
        return JSONResponse(status_code=503, content={"error": f"Model {algo} not loaded"})

    try:
        result = ml_models.predict_fraud(payload, algo)
        score_val = result["score"]
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    decision = (
        "allow" if score_val < 0.25
        else "challenge" if score_val < 0.60
        else "block"
    )

    return {
        "score": score_val,
        "decision": decision,
        "algorithm": result["algorithm"],
        "confidence": result["confidence"],
        "model_version": "v1.0"
    }

# ----------------------------
# List available algorithms
# ----------------------------
@app.get("/algorithms")
async def list_algorithms():
    available = ml_models.get_available_algorithms()
    return {
        "algorithms": ["ann", "svm", "knn"],
        "available": available,
        "active": ml_models._active_algorithm
    }

# ----------------------------
# Train a model on-demand
# ----------------------------
@app.post("/train/{algorithm}")
async def train_model(algorithm: str, force_retrain: bool = Query(False)):
    if algorithm not in ["ann", "svm", "knn"]:
        return JSONResponse(status_code=400, content={"error": f"Unknown algorithm: {algorithm}"})

    success = ml_models.train_algorithm(algorithm, force_retrain=force_retrain)
    if success:
        metrics = ml_models.get_metrics(algorithm)
        return {"status": "success", "algorithm": algorithm, "metrics": metrics}
    else:
        return JSONResponse(status_code=500, content={"error": f"Training failed for {algorithm}"})

# ----------------------------
# Select active algorithm
# ----------------------------
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

# ----------------------------
# Healthcheck
# ----------------------------
@app.get("/healthz")
def health():
    return {"status": "ok"}
