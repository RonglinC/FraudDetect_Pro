PYTHON_DEPS=pandas numpy matplotlib
eda:
	$(VENV)/bin/python backend/eda/eda.py
PY=python3
BACKEND=backend
VENV=$(BACKEND)/.venv
PIP=$(VENV)/bin/pip
PYTHON=$(VENV)/bin/python
UVICORN=$(VENV)/bin/uvicorn

.PHONY: default venv install run health score clean

default: run

venv:
	$(PY) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip

install: venv
	$(PIP) install -r $(BACKEND)/requirements.txt
	$(PIP) install $(PYTHON_DEPS)

run:
	$(UVICORN) app.main:app --reload --port 8000 --app-dir $(BACKEND)

health:
	curl http://127.0.0.1:8000/healthz


# Legacy score endpoint (POC)
score:
		curl -X POST http://127.0.0.1:8000/score \
			-H "Content-Type: application/json" \
			-d '{"event_id":"t1","user_id":"u1","geo":{"country":"CA"},"previous_failed_logins":2,"additional_metadata":{"home_country":"US"}}'

# ANN scoring endpoint (minimal dummy payload)
score-ann:
		curl -X POST http://127.0.0.1:8000/score \
			-H "Content-Type: application/json" \
			-d '{"Time":0,"Amount":1.0,"V1":0.1,"V2":0.2,"V3":0.3,"V4":0.4,"V5":0.5,"V6":0.6,"V7":0.7,"V8":0.8,"V9":0.9,"V10":1.0,"V11":1.1,"V12":1.2,"V13":1.3,"V14":1.4,"V15":1.5,"V16":1.6,"V17":1.7,"V18":1.8,"V19":1.9,"V20":2.0,"V21":2.1,"V22":2.2,"V23":2.3,"V24":2.4,"V25":2.5,"V26":2.6,"V27":2.7,"V28":2.8}'

# ANN metrics endpoint
metrics:
		curl -X GET http://127.0.0.1:8000/metrics

clean:
	rm -rf $(VENV) $(BACKEND)/fraud.db

# --- PoC auth demo targets ---
register-poc:
	@curl -sS -X POST http://127.0.0.1:8000/register \
	  -H "Content-Type: application/json" \
	  -d '{"email":"demo@example.com","phone":"555-0100","password":"secret","home_country":"US"}' \
	  -w '\nstatus:%{http_code}\n'

login-poc:
	@curl -sS -X POST http://127.0.0.1:8000/login \
	  -H "Content-Type: application/json" \
	  -d '{"email_or_user_id":"demo@example.com","password":"secret","geo_country":"US"}' \
	  -w '\nstatus:%{http_code}\n'

algorithms:
	@curl -sS http://127.0.0.1:8000/algorithms -w '\nstatus:%{http_code}\n'

# --- EDA target ---
eda:
	$(VENV)/bin/python backend/eda/eda.py
