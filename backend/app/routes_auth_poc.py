# backend/routes_auth_poc.py
import sqlite3
import bcrypt
from fastapi import APIRouter
from typing import List

# import your pydantic schemas (adjust import path if necessary)
from app.schemas import LoginRequest, LoginResponse, AlgorithmsResponse

DB_FILE = "users.db"
router = APIRouter(prefix="/auth", tags=["auth"])


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash FROM users WHERE username=? OR email=?",
        (req.email_or_user_id, req.email_or_user_id),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return LoginResponse(user_id="", success=False)

    user_id, username, password_hash = row
    ok = _verify_password(req.password, password_hash)
    return LoginResponse(user_id=username if ok else "", success=ok)


@router.get("/algorithms", response_model=AlgorithmsResponse)
def algorithms():
    return AlgorithmsResponse(algorithms=["logreg", "xgboost"])
