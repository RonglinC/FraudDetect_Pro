# Prompt: Identify Repo Gaps and Upgrade Bootstrap

Analyze this repository. Produce:

1. Endpoint & data flow map (health check, score route)
2. Current SQLite schema
3. Missing parts needed for:
   - storing login events
   - storing score decisions
   - returning allow/challenge/block deterministically
   - versioning the model
4. Proposed minimal enhancements split per file path

Then apply improvements:
- Add structured logging
- Add idempotency protection for duplicate event_id
- Add clear FastAPI response schema for `/score`

Output only unified diffs for code modifications.
Ask for confirmation before applying.
