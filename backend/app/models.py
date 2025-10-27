from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from app.db import Base

class LoginEvent(Base):
    __tablename__ = "login_events"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id_hash = Column(String(128), index=True, nullable=False)
    ip = Column(String(64), nullable=True)
    country = Column(String(64), nullable=True)
    region = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)
    device_id = Column(String(128), nullable=True)
    fingerprint_hash = Column(String(128), nullable=True)
    auth_method = Column(String(32), nullable=True)
    previous_failed_logins = Column(Integer, default=0)
    additional_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ScoreDecision(Base):
    __tablename__ = "score_decisions"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    score = Column(Float, nullable=False)
    decision = Column(String(16), nullable=False)
    reasons = Column(JSON, nullable=True)
    explain = Column(JSON, nullable=True)
    model_version = Column(String(64), nullable=False)
    cached = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
