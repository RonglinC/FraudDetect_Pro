from typing import Dict, Tuple

def predict(features: Dict) -> Tuple[float, Dict[str, float]]:
    base = 0.12
    contribs = {}
    pfl = features.get("previous_failed_logins", 0)
    if pfl > 3:
        contribs["previous_failed_logins"] = 0.55
    elif pfl > 0:
        contribs["previous_failed_logins"] = 0.08
    if features.get("unusual_geo", False):
        contribs["unusual_geo"] = 0.28
    if features.get("new_device", False):
        contribs["new_device"] = 0.15
    ev = features.get("event_id", "")
    jitter = (hash(ev) % 7) / 100.0
    contribs["bias+jitter"] = base + jitter
    score = base + jitter + sum(v for k, v in contribs.items() if k != "bias+jitter")
    score = min(1.0, max(0.0, score))
    return score, contribs
