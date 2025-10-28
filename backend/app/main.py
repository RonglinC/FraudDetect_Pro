from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers.score import router as score_router
from .logging import get_logger
from .routes_auth_poc import router as auth_poc_router
from .routers.auth import ROUTER as auth_router


logger = get_logger(__name__)




app = FastAPI(title="Login Fraud Scoring POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
app.include_router(score_router)
app.include_router(auth_poc_router)
app.include_router(auth_router)

@app.get("/healthz")
def health():
    logger.info("health_check")
    return {"status": "ok"}
