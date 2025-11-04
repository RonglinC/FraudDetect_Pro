# FraudDetect_Pro API Endpoints & Testing Guide

## Backend API Endpoints (Port 8000)

### Authentication
```bash
# Login
curl -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email_or_user_id":"alice","password":"Passw0rd!"}'

# Response: {"user_id":"alice","success":true}

# List algorithms (legacy endpoint on auth router)
curl http://127.0.0.1:8000/auth/algorithms
# Response: {"algorithms":["logreg","xgboost"]}
```

### Health Check
```bash
curl http://127.0.0.1:8000/healthz
# Response: {"status":"ok"}
```

### ML Model Management
```bash
# List available algorithms
curl http://127.0.0.1:8000/algorithms
# Response: {"algorithms":["ann","svm","knn"],"available":["ann","svm"],"active":"ann"}

# Train a specific model (ANN, SVM, or KNN)
curl -X POST http://127.0.0.1:8000/train/ann
curl -X POST http://127.0.0.1:8000/train/svm
curl -X POST http://127.0.0.1:8000/train/knn
# Response: {"status":"success","algorithm":"ann","metrics":{...}}

# Select active algorithm
curl -X POST http://127.0.0.1:8000/select/ann
curl -X POST http://127.0.0.1:8000/select/svm
curl -X POST http://127.0.0.1:8000/select/knn
# Response: {"status":"success","active_algorithm":"ann","message":"ANN is now the active algorithm"}

# Get model metrics (uses active algorithm by default)
curl http://127.0.0.1:8000/metrics
# Response: {"accuracy":0.9995,"precision":0.8681,"recall":0.8061,"f1_score":0.8360,...}

# Get metrics for specific algorithm
curl "http://127.0.0.1:8000/metrics?algorithm=ann"
curl "http://127.0.0.1:8000/metrics?algorithm=svm"
curl "http://127.0.0.1:8000/metrics?algorithm=knn"
```

### Fraud Scoring
```bash
# Score with active algorithm (low-risk example)
curl -X POST http://127.0.0.1:8000/score \
  -H 'Content-Type: application/json' \
  -d '{
    "Time": 10000,
    "V1": 0, "V2": 0, "V3": 0, "V4": 0, "V5": 0,
    "V6": 0, "V7": 0, "V8": 0, "V9": 0, "V10": 0,
    "V11": 0, "V12": 0, "V13": 0, "V14": 0, "V15": 0,
    "V16": 0, "V17": 0, "V18": 0, "V19": 0, "V20": 0,
    "V21": 0, "V22": 0, "V23": 0, "V24": 0, "V25": 0,
    "V26": 0, "V27": 0, "V28": 0,
    "Amount": 123.45
  }'
# Response: {"score":0.0011,"decision":"allow","algorithm":"ann","confidence":0.9989,"model_version":"v1.0"}

# Score with specific algorithm (borderline example)
curl -X POST "http://127.0.0.1:8000/score?algorithm=svm" \
  -H 'Content-Type: application/json' \
  -d '{
    "Time": 20000,
    "V1": 0.5, "V2": -0.3, "V3": 0.1, "V4": 0.2, "V5": -0.4,
    "V6": 0.1, "V7": 0.0, "V8": 0.2, "V9": -0.1, "V10": 0.3,
    "V11": -0.2, "V12": 0.1, "V13": 0.0, "V14": -2.2, "V15": 0.3,
    "V16": -0.5, "V17": 0.2, "V18": 0.1, "V19": -0.2, "V20": 0.0,
    "V21": 0.1, "V22": -0.3, "V23": 0.2, "V24": -0.1, "V25": 0.0,
    "V26": 0.2, "V27": -0.2, "V28": 0.1,
    "Amount": 500.00
  }'

# High-risk transaction example
curl -X POST http://127.0.0.1:8000/score \
  -H 'Content-Type: application/json' \
  -d '{
    "Time": 30000,
    "V1": 1.5, "V2": -2.5, "V3": 3.0, "V4": -1.2, "V5": 2.1,
    "V6": -2.0, "V7": 1.8, "V8": -1.5, "V9": 2.4, "V10": -1.1,
    "V11": 2.0, "V12": -1.3, "V13": 1.7, "V14": -5.0, "V15": 1.2,
    "V16": -2.2, "V17": 1.1, "V18": -1.0, "V19": 2.0, "V20": -2.3,
    "V21": 1.0, "V22": -1.1, "V23": 2.2, "V24": -2.1, "V25": 1.3,
    "V26": -1.7, "V27": 2.0, "V28": -1.4,
    "Amount": 2500.00
  }'
```

**Decision Thresholds:**
- `score < 0.25` → **allow**
- `0.25 ≤ score < 0.60` → **challenge**
- `score ≥ 0.60` → **block**

---

## Frontend Endpoints (Port 5050)

### Direct Browser Access
```bash
# Login page
open http://127.0.0.1:5050/

# Homepage (after login)
open http://127.0.0.1:5050/homepage

# Chatbot (after login)
open http://127.0.0.1:5050/chatbot

# Logout
open http://127.0.0.1:5050/logout
```

### Frontend API (used by JavaScript in browser)
```bash
# Chatbot API (requires authenticated session)
curl -X POST http://127.0.0.1:5050/chatbot_api \
  -H 'Content-Type: application/json' \
  -H 'Cookie: session=YOUR_SESSION_COOKIE' \
  -d '{"message":"Hello"}'
# Response: {"response":"Echo: Hello"}
```

**Note:** The chatbot currently echoes messages. This will be enhanced to call backend ML endpoints.

---

## Commands to Run the System

### 1. Start Backend (Terminal 1)
```bash
cd /Users/ronglinchen/FraudDetect_Pro
make run
```
Or manually:
```bash
backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000 --reload
```

### 2. Start Frontend (Terminal 2)
```bash
cd /Users/ronglinchen/FraudDetect_Pro
PORT=5050 backend/.venv/bin/python frontend/frontend.py
```
Or with explicit BACKEND_URL:
```bash
BACKEND_URL=http://127.0.0.1:8000 PORT=5050 backend/.venv/bin/python frontend/frontend.py
```

### 3. Create/Seed Database (if needed)
```bash
cd backend
../backend/.venv/bin/python create_user_db.py
cd ..
```


## Quick Test Workflow

### Step 1: Verify Backend Health
```bash
curl http://127.0.0.1:8000/healthz
# Expected: {"status":"ok"}
```

### Step 2: Verify Frontend is Up
```bash
curl -I http://127.0.0.1:5050/
# Expected: HTTP/1.1 200 OK
```

### Step 3: Test Login via API
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email_or_user_id":"alice","password":"Passw0rd!"}'
# Expected: {"user_id":"alice","success":true}
```

### Step 4: Check Available Algorithms
```bash
curl http://127.0.0.1:8000/algorithms
# Expected: {"algorithms":["ann","svm","knn"],"available":["ann","svm"],"active":"ann"}
```

### Step 5: Get ANN Metrics
```bash
curl http://127.0.0.1:8000/metrics
# Expected: Full metrics JSON with accuracy, precision, recall, etc.
```

### Step 6: Score a Transaction
```bash
curl -X POST http://127.0.0.1:8000/score \
  -H 'Content-Type: application/json' \
  -d '{"Time":10000,"V1":0,"V2":0,"V3":0,"V4":0,"V5":0,"V6":0,"V7":0,"V8":0,"V9":0,"V10":0,"V11":0,"V12":0,"V13":0,"V14":0,"V15":0,"V16":0,"V17":0,"V18":0,"V19":0,"V20":0,"V21":0,"V22":0,"V23":0,"V24":0,"V25":0,"V26":0,"V27":0,"V28":0,"Amount":123.45}'
# Expected: {"score":0.0011,"decision":"allow","algorithm":"ann","confidence":0.9989,"model_version":"v1.0"}
```

### Step 7: Train and Switch to SVM
```bash
# Train SVM
curl -X POST http://127.0.0.1:8000/train/svm
# Expected: {"status":"success","algorithm":"svm","metrics":{...}}

# Select SVM as active
curl -X POST http://127.0.0.1:8000/select/svm
# Expected: {"status":"success","active_algorithm":"svm","message":"SVM is now the active algorithm"}

# Score with SVM
curl -X POST http://127.0.0.1:8000/score \
  -H 'Content-Type: application/json' \
  -d '{"Time":10000,"V1":0,"V2":0,"V3":0,"V4":0,"V5":0,"V6":0,"V7":0,"V8":0,"V9":0,"V10":0,"V11":0,"V12":0,"V13":0,"V14":0,"V15":0,"V16":0,"V17":0,"V18":0,"V19":0,"V20":0,"V21":0,"V22":0,"V23":0,"V24":0,"V25":0,"V26":0,"V27":0,"V28":0,"Amount":123.45}'
```

---

## Frontend Usage

**What Frontend Currently Uses:**
- `POST /auth/login` - user authentication
- Chatbot currently echoes messages (placeholder)

**What Frontend Will Use (for chatbot integration):**
- `GET /algorithms` - show algorithm choices to user
- `POST /select/{algorithm}` - when user picks algorithm via chat
- `POST /score` - check transactions through conversation
- `GET /metrics` - display model performance stats

---

## Makefile Commands

```bash
# Install dependencies
make install

# Run backend server
make run

# Health check
make health

# Get metrics
make metrics

# Train models
make train-ann
make train-svm
make train-knn
make train-all

# Score with specific algorithms
make score-ann
make score-with-svm
make score-with-knn

# Select active algorithm
make select-ann
make select-svm
make select-knn

# Get algorithm-specific metrics
make metrics-svm
make metrics-knn

# Run EDA
make eda
```


## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill process if needed
kill -9 <PID>
```

### Frontend won't start
```bash
# Check if port 5050 is in use
lsof -i :5050
# Kill process if needed
kill -9 <PID>
```

### "Model not loaded" error
```bash
# Train the model first
curl -X POST http://127.0.0.1:8000/train/ann
```

### Database "no such table: users"
```bash
# Recreate database
cd backend
../backend/.venv/bin/python create_user_db.py
cd ..
```

