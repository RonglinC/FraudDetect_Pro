from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class Device(BaseModel):
    userAgent: Optional[str] = None
    deviceId: Optional[str] = None
    fingerprintHash: Optional[str] = None

class Geo(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None

class ScoreRequest(BaseModel):
    event_id: str
    user_id: str = Field(description="Already hashed if possible")
    timestamp: Optional[str] = None
    ip: Optional[str] = None
    device: Optional[Device] = None
    auth_method: Optional[str] = None
    geo: Optional[Geo] = None
    previous_failed_logins: int = 0
    additional_metadata: Optional[Dict] = None

class Explain(BaseModel):
    feature_contributions: Optional[Dict[str, float]] = None

class ScoreResponse(BaseModel):
    event_id: str
    score: float
    decision: str
    reasons: List[str]
    explain: Optional[Explain] = None
    model_version: str
    cached: bool
