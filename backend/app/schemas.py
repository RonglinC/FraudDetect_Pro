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
    event_id: str = Field(
        min_length=1,
        max_length=64,
        description="Unique identifier for the login event"
    )
    user_id: str = Field(
        min_length=1,
        max_length=128,
        description="Hashed user identifier"
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO-8601 formatted timestamp of the login event"
    )
    ip: Optional[str] = Field(
        default=None,
        max_length=64,
        description="IP address of the login attempt"
    )
    device: Optional[Device] = Field(
        default=None,
        description="Device information from the login attempt"
    )
    auth_method: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Authentication method used (e.g., password, 2fa, sso)"
    )
    geo: Optional[Geo] = Field(
        default=None,
        description="Geographic location information"
    )
    previous_failed_logins: int = Field(
        default=0,
        ge=0,
        description="Number of failed login attempts prior to this one"
    )
    additional_metadata: Optional[Dict] = Field(
        default=None,
        description="Additional context about the login attempt"
    )

class Explain(BaseModel):
    feature_contributions: Optional[Dict[str, float]] = None

class ScoreResponse(BaseModel):
    event_id: str = Field(description="The event ID from the request")
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Risk score between 0.0 and 1.0"
    )
    decision: str = Field(
        description="Risk decision: allow, challenge, or block",
        pattern="^(allow|challenge|block)$"
    )
    reasons: List[str] = Field(
        description="List of reasons for the decision"
    )
    explain: Optional[Explain] = Field(
        default=None,
        description="Model explanation details"
    )
    model_version: str = Field(
        description="Version of the model used for scoring"
    )
    cached: bool = Field(
        description="Whether this response was served from cache"
    )
