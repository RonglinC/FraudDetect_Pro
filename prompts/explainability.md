# Prompt: Deterministic Explainability

Create backend/app/explain.py:
- interpret key features (geo mismatch, prev_failed_logins)
- return top 1–3 readable reason strings
- no LLM usage; pure logic

Modify the `/score` route to:
- include `reasons` array in response
- log internal numeric features and decisions

Output only unified diffs. Ask before applying.
