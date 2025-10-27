from typing import List, Tuple
from app.config import settings

def apply_policy(score: float) -> Tuple[str, List[str]]:
    if score < settings.allow_threshold:
        return "allow", ["score_below_allow_threshold"]
    if score < settings.challenge_threshold:
        return "challenge", ["score_between_allow_and_challenge_threshold"]
    return "block", ["score_above_challenge_threshold"]
