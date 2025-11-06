# FraudDetect_Pro API Endpoints & Testing Guide

## Backend API Endpoints (Port 8000)

### Enhanced Chatbot API

#### Intelligent Conversation
```bash
# Main chatbot interaction with user data integration
curl -X POST http://127.0.0.1:8000/chatbot/message \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hello", "user_id": "alice"}'
# Response: Personalized greeting with account summary

curl -X POST http://127.0.0.1:8000/chatbot/message \
  -H 'Content-Type: application/json' \
  -d '{"message": "Show my account info", "user_id": "alice"}'
# Response: Comprehensive account information with stats

curl -X POST http://127.0.0.1:8000/chatbot/message \
  -H 'Content-Type: application/json' \
  -d '{"message": "My transactions", "user_id": "alice"}'
# Response: Recent transaction history with fraud indicators

curl -X POST http://127.0.0.1:8000/chatbot/message \
  -H 'Content-Type: application/json' \
  -d '{"message": "Check transaction for $500 at Amazon", "user_id": "alice"}'
# Response: ML-powered fraud analysis with decision

curl -X POST http://127.0.0.1:8000/chatbot/message \
  -H 'Content-Type: application/json' \
  -d '{"message": "Use SVM algorithm", "user_id": "alice"}'
# Response: Algorithm switched with performance metrics
```

#### User Data API
```bash
# Get comprehensive user information
curl -X GET http://127.0.0.1:8000/chatbot/user/alice/info

# Get user transaction history with filters
curl -X GET "http://127.0.0.1:8000/chatbot/user/alice/transactions?limit=10&include_fraud=true&min_amount=100"
# Response: [{"id":121,"txn_time":"2025-11-04T20:53:00","amount":455.88,...}]

# Get detailed fraud analysis for user
curl -X GET http://127.0.0.1:8000/chatbot/user/alice/fraud-summary
# Response: {"user":{...},"statistics":{...},"recent_fraud_cases":[],

# Get system-wide analytics
curl -X GET http://127.0.0.1:8000/chatbot/analytics/users-overview
# Response: {"system_overview":{...},"users":[...]}

# Session management
curl -X GET http://127.0.0.1:8000/chatbot/session/alice
curl -X DELETE http://127.0.0.1:8000/chatbot/session/alice
```

### Authentication
```bash
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

open http://127.0.0.1:5050/chatbot

# Logout
open http://127.0.0.1:5050/logout
```

```bash
curl -X POST http://127.0.0.1:5050/chatbot_api \
  -H 'Content-Type: application/json' \
  -H 'Cookie: session=YOUR_SESSION_COOKIE' \
  -d '{"message": "Hello"}'
# Response: Intelligent response with user data integration

# Example chatbot conversations:
# "Hello" → Personalized greeting with account summary
# "Show my account info" → Comprehensive user profile
# "My transactions" → Recent transaction history
# "Check transaction for $500 at Amazon" → ML fraud analysis
```

---

## Chatbot Conversation Examples

### 1. Personalized User Experience
```bash
# User greeting with account integration
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "alice"}'


### 2. Account Information
```bash
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show my account info", "user_id": "alice"}'

```

### 3. Transaction History
```bash
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "My transactions", "user_id": "alice"}'

```

### 4. Real-Time Fraud Detection
```bash
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Check transaction for $500 at Amazon", "user_id": "alice"}'

```

### 5. Algorithm Management
```bash
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Use SVM algorithm", "user_id": "alice"}'

```

---

## Commands to Run the System

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

---


```bash
curl http://127.0.0.1:8000/healthz
# Expected: {"status":"ok"}

# Test user data integration
curl -X GET "http://127.0.0.1:8000/chatbot/user/alice/info"
# Expected: User profile with transaction stats
```

```bash
# Personalized greeting
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "alice"}'

# Account information
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show my account info", "user_id": "alice"}'

# Transaction history
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "My transactions", "user_id": "alice"}'

# Fraud detection
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Check transaction for $500 at Amazon", "user_id": "alice"}'

# Algorithm switching
curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Use SVM algorithm", "user_id": "alice"}'
```

```bash
# Test user with fraud cases
curl -X GET "http://127.0.0.1:8000/chatbot/user/eve/fraud-summary"
# Shows fraud statistics and patterns

curl -X POST "http://127.0.0.1:8000/chatbot/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "eve"}'
# Will show fraud cases in account summary
```

---


```bash
# Install dependencies
make install

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

---


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

### Chatbot not responding intelligently
```bash
# Check user exists in database
curl -X GET "http://127.0.0.1:8000/chatbot/user/alice/info"
# Should return user profile, not 404
```

