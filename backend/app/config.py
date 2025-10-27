from pydantic import BaseModel
import os

class Settings(BaseModel):
    app_name: str = "Login Fraud Scoring POC"
    database_url: str = os.getenv("DATABASE_URL","sqlite:///./fraud.db")
    allow_threshold: float = float(os.getenv("ALLOW_THRESHOLD", "0.3"))
    challenge_threshold: float = float(os.getenv("CHALLENGE_THRESHOLD", "0.7"))
    model_version: str = os.getenv("MODEL_VERSION", "mock-0.1")
    enable_debug_logging: bool = os.getenv("DEBUG_LOGS", "false").lower() == "true"

settings = Settings()
