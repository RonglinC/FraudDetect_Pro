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

run:
	$(UVICORN) app.main:app --reload --port 8000 --app-dir $(BACKEND)

health:
	curl http://127.0.0.1:8000/healthz

score:
	curl -X POST http://127.0.0.1:8000/score \
	  -H "Content-Type: application/json" \
	  -d '{"event_id":"t1","user_id":"u1","geo":{"country":"CA"},"previous_failed_logins":2,"additional_metadata":{"home_country":"US"}}'

clean:
	rm -rf $(VENV) $(BACKEND)/fraud.db
