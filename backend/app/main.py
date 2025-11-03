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

@app.get("/healthz")
def health():
    return {"status": "ok"}
