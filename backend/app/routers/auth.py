# app/routers/auth.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import sqlite3
import bcrypt
import uuid
import hashlib
from typing import Optional, List, Dict

ROUTER = APIRouter(prefix="/auth", tags=["auth"])

USERS_DB = "users.db"  # ensure path is correct relative to working dir

# Simple in-memory token store for POC (token -> user_id)
TOKEN_STORE: Dict[str, int] = {}

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    user_id: int
    username: str
    token: str

class TransactionOut(BaseModel):
    id: int
    txn_time: str
    amount: float
    merchant: Optional[str]
    card_masked: Optional[str]
    location: Optional[str]
    is_fraud: int
    description: Optional[str]

def get_db_conn():
    conn = sqlite3.connect(USERS_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@ROUTER.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (req.username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    stored_hash = row["password_hash"]
    # For demo: try both bcrypt and simple hash
    password_matches = False
    try:
        # Try bcrypt first
        password_matches = bcrypt.checkpw(req.password.encode("utf-8"), stored_hash.encode("utf-8"))
    except:
        # Fall back to simple hash for demo
        simple_hash = hashlib.sha256(req.password.encode("utf-8")).hexdigest()
        password_matches = (simple_hash == stored_hash)
    
    if not password_matches:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # issue simple token
    token = str(uuid.uuid4())
    TOKEN_STORE[token] = row["id"]
    return LoginResponse(user_id=row["id"], username=row["username"], token=token)

def get_user_id_from_token(authorization: Optional[str] = Header(None)) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    user_id = TOKEN_STORE.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id

@ROUTER.get("/me/transactions", response_model=List[TransactionOut])
def my_transactions(user_id: int = Depends(get_user_id_from_token), limit: int = 50):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""SELECT id, txn_time, amount, merchant, card_masked, location, is_fraud, description
                   FROM transactions WHERE user_id = ? ORDER BY txn_time DESC LIMIT ?""", (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [TransactionOut(**dict(r)) for r in rows]

@ROUTER.get("/users/{user_id}/transactions", response_model=List[TransactionOut])
def user_transactions(user_id: int, auth_user_id: int = Depends(get_user_id_from_token), limit: int = 50):
    # For POC: allow user to fetch only their own transactions unless token belongs to admin (not implemented)
    if auth_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""SELECT id, txn_time, amount, merchant, card_masked, location, is_fraud, description
                   FROM transactions WHERE user_id = ? ORDER BY txn_time DESC LIMIT ?""", (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [TransactionOut(**dict(r)) for r in rows]
