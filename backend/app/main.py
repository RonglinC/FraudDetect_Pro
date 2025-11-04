# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_auth_poc import router as auth_poc_router
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

# --- ANN Model Startup ---
@app.on_event("startup")
def train_ann_on_startup():
    ann_runtime.load_and_train_model()

# --- /score endpoint ---
@app.post("/score")
async def score(payload: dict):
    if not ann_runtime.is_ready():
        return JSONResponse(status_code=503, content={"error": "model not loaded"})
    try:
        score = ann_runtime.predict_proba(payload)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    if score < 0.25:
        decision = "allow"
    elif score < 0.60:
        decision = "challenge"
    else:
        decision = "block"
    return {
        "score": score,
        "decision": decision,
        "model_version": "ann_poc"
    }

# --- /metrics endpoint ---
@app.get("/metrics")
async def metrics():
    if not ann_runtime.is_ready():
        return JSONResponse(status_code=503, content={"error": "model not loaded"})
    return ann_runtime._metrics

@app.get("/healthz")
def health():
    return {"status": "ok"}
