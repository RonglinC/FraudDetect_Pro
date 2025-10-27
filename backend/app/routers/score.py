from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas import ScoreRequest, ScoreResponse, Explain
from app.db import get_db
from app.models import LoginEvent, ScoreDecision
from app.policy import apply_policy
from app.config import settings
from app.model.mock_model import predict

router = APIRouter(prefix="/score", tags=["score"])

def _enrich(req: ScoreRequest) -> dict:
    geo = (req.geo.country or "").upper() if req.geo else ""
    home = (req.additional_metadata or {}).get("home_country", "US").upper()
    unusual_geo = bool(geo and home and geo != home)
    new_device = bool(req.device and (req.device.fingerprintHash or req.device.deviceId) and
                      (req.additional_metadata or {}).get("seen_device_hash") not in
                      {req.device.fingerprintHash, req.device.deviceId})
    return {
        "event_id": req.event_id,
        "previous_failed_logins": req.previous_failed_logins,
        "unusual_geo": unusual_geo,
        "new_device": new_device,
    }

@router.post("", response_model=ScoreResponse)
def score(req: ScoreRequest, db: Session = Depends(get_db)):
    existing = db.query(ScoreDecision).filter(ScoreDecision.event_id == req.event_id).first()
    if existing:
        return ScoreResponse(
            event_id=existing.event_id,
            score=existing.score,
            decision=existing.decision,
            reasons=existing.reasons or [],
            explain=Explain(feature_contributions=(existing.explain or {}).get("feature_contributions")),
            model_version=existing.model_version,
            cached=True,
        )

    ev = LoginEvent(
        event_id=req.event_id,
        user_id_hash=req.user_id,
        ip=req.ip,
        country=(req.geo.country if req.geo else None),
        region=(req.geo.region if req.geo else None),
        user_agent=(req.device.userAgent if req.device else None),
        device_id=(req.device.deviceId if req.device else None),
        fingerprint_hash=(req.device.fingerprintHash if req.device else None),
        auth_method=req.auth_method,
        previous_failed_logins=req.previous_failed_logins,
        additional_metadata=req.additional_metadata,
    )
    db.add(ev)

    features = _enrich(req)
    score_val, contribs = predict(features)
    decision, reasons = apply_policy(score_val)

    record = ScoreDecision(
        event_id=req.event_id,
        score=score_val,
        decision=decision,
        reasons=reasons,
        explain={"feature_contributions": contribs},
        model_version=settings.model_version,
        cached=False
    )
    db.add(record)
    db.commit()

    return ScoreResponse(
        event_id=req.event_id,
        score=score_val,
        decision=decision,
        reasons=reasons,
        explain=Explain(feature_contributions=contribs),
        model_version=settings.model_version,
        cached=False
    )
