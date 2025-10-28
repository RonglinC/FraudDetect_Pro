# Prompt: Minimal Auth + Algorithm List (PoC)

Goal
Add the smallest possible registration, login, and algorithm selection to the existing FastAPI app using current SQLite setup. No external deps beyond what’s already in backend/requirements.txt.

Scope
- Tables: users, login_events (very small schemas)
- Endpoints: POST /register, POST /login, GET /algorithms
- Passwords: store a simple salted SHA256 (stdlib hashlib); this is PoC, not production
- Keep existing /healthz and /score working

Changes

1) backend/app/models.py
- Add User table:
  - user_id TEXT (PK or unique), email TEXT (unique), phone TEXT, password_hash TEXT,
    home_country TEXT, registered_at DateTime default now
- Add LoginEvent table with minimal fields if not present:
  - event_id TEXT (unique), user_id TEXT, ts DateTime default now,
    geo_country TEXT, success INT (0/1)
- Ensure Base.metadata.create_all(bind=engine) still creates tables.

2) backend/app/schemas.py
- Add minimal Pydantic models:
  - RegisterRequest {email:str, phone:str, password:str, home_country:str}
  - RegisterResponse {user_id:str, email:str}
  - LoginRequest {email_or_user_id:str, password:str, geo_country:str}
  - LoginResponse {user_id:str, success:bool}
  - AlgorithmsResponse {algorithms:list[str]}

3) backend/app/security.py (new)
- Implement:
  - make_salt() -> str
  - hash_password(pw:str, salt:str) -> "salt$hexhash"
  - verify_password(plain:str, stored:str) -> bool
Use hashlib.sha256 with salt, all stdlib.

4) backend/app/routes_auth_poc.py (new)
- POST /register:
  - If email exists -> 409
  - Else create user_id as short uuid (e.g., first 8 chars), hash password, insert, return {user_id,email}
- POST /login:
  - Lookup by email OR user_id
  - Verify password, insert LoginEvent with success 0/1 and geo_country uppercased
  - Return {user_id, success}
- GET /algorithms:
  - Return {algorithms:["logreg","xgboost"]}

5) backend/app/main.py
- Include the new router so routes are live.
- Do not break /healthz or /score.

6) Makefile (repo root)
- Add quick demo targets:
  - register-poc: POST /register with demo user
  - login-poc: POST /login with the same creds
  - algorithms: GET /algorithms

Output
- Provide unified diffs only for modified/created files.
- Ask for confirmation before applying changes.
