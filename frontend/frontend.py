from flask import Flask, render_template, request, redirect, url_for, session
import requests
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "secret"

FASTAPI_URL = "http://127.0.0.1:8000"
LOGIN_ENDPOINT = f"{FASTAPI_URL}/auth/login"

DB_FILE = "users.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # so we can access columns by name
    return conn 

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_or_user_id = request.form.get("email_or_user_id", "").strip()
        password = request.form.get("password", "").strip()

        if not email_or_user_id or not password:
            return render_template("login.html", error="Please enter both username and password")

        payload = {"email_or_user_id": email_or_user_id, "password": password}
        print("Payload -> backend:", payload)

        try:
            resp = requests.post(LOGIN_ENDPOINT, json=payload, timeout=5)
            print("Backend response:", resp.status_code, resp.text)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("user_id"):
                    session["user"] = data.get("user_id")
                    session["user_id"] = data.get("id")
                    return redirect(url_for("homepage"))
                else:
                    return render_template("login.html", error="Invalid credentials")
            else:
                return render_template("login.html", error=f"Login failed ({resp.status_code}): {resp.text}")
        except requests.RequestException as e:
            return render_template("login.html", error=f"Backend unreachable: {e}")

    return render_template("login.html")


@app.route("/homepage")
def homepage():
    # Check that the user is logged in
    if "user" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]  # user_id stored during login
    transactions = []

    # Call FastAPI endpoint using user_id
    try:
        # Endpoint expects numeric user_id
        res = requests.get(f"{FASTAPI_URL}/transactions/{user_id}", timeout=5)
        res.raise_for_status()
        data = res.json()
        transactions = data.get("transactions", [])
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Could not fetch transactions: {e}")

    return render_template("homepage.html", user=user_id, transactions=transactions)





@app.route("/detect_fraud")
def detect_fraud():
    username = session.get("username")
    res = requests.post(f"{FASTAPI_URL}/predict_fraud/{username}")
    predictions = res.json().get("predictions", [])
    return render_template("fraud_results.html", predictions=predictions)


@app.route("/chatbot")
def chatbot():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("chatbot.html")

@app.route("/chatbot_api", methods=["POST"])
def chatbot_api():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    message = data.get("message", "")
    user_id = session["user"]
    
    # Call backend chatbot API
    try:
        chatbot_payload = {"message": message, "user_id": user_id}
        backend_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
        
        resp = requests.post(f"{backend_url}/chatbot/message", 
                           json=chatbot_payload, timeout=10)
        
        if resp.status_code == 200:
            result = resp.json()
            return jsonify({"response": result.get("response", "No response")})
        else:
            return jsonify({"response": f"Backend error: {resp.status_code}"})
            
    except requests.RequestException as e:
        return jsonify({"response": f"Connection error: {str(e)}"})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"})



@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, debug=True)
