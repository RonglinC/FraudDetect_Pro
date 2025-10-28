from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.db import get_db
from app.models import User
from app.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    AlgorithmsResponse,
)
from app.security import hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check existing email
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="email already exists")

    user_id = uuid.uuid4().hex[:8]
    stored = hash_password(req.password)

    user = User(
        user_id=user_id,
        email=req.email,
        phone=req.phone,
        password_hash=stored,
        home_country=(req.home_country or None),
    )
    db.add(user)
    db.commit()
    return RegisterResponse(user_id=user_id, email=req.email)


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    q = db.query(User).filter((User.email == req.email_or_user_id) | (User.user_id == req.email_or_user_id))
    user = q.first()
    if not user:
        # return generic failure (do not disclose existence)
        return LoginResponse(user_id="", success=False)

    ok = verify_password(req.password, user.password_hash)

    # Minimal event write: use event_id as short uuid
    # We write to existing login_events table if present (uses event_id and user_id_hash field)
    try:
        from app.models import LoginEvent

        ev = LoginEvent(
            event_id=uuid.uuid4().hex[:12],
            user_id_hash=user.user_id,
            ip=None,
            country=(req.geo_country or None),
            region=None,
            user_agent=None,
            device_id=None,
            fingerprint_hash=None,
            auth_method="password",
            previous_failed_logins=0,
            additional_metadata={"poc": True},
        )
        db.add(ev)
        db.commit()
    except Exception:
        # if login_events table isn't compatible, ignore event write for PoC
        db.rollback()

    return LoginResponse(user_id=user.user_id, success=bool(ok))


@router.get("/algorithms", response_model=AlgorithmsResponse)
def algorithms():
    return AlgorithmsResponse(algorithms=["logreg", "xgboost"])
