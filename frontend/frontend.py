import sys
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
import sqlite3

# -----------------------------
# 1️⃣ Add backend folder to path
# -----------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

# -----------------------------
# 2️⃣ Import the chatbot
# -----------------------------
from app.chatbot_nlp import FraudDetectionChatbot

# -----------------------------
# 3️⃣ Initialize Flask & Chatbot
# -----------------------------
app = Flask(__name__)
app.secret_key = "secret"

chatbot = FraudDetectionChatbot()  # Global instance

FASTAPI_URL = "http://127.0.0.1:8000"
LOGIN_ENDPOINT = f"{FASTAPI_URL}/auth/login"
DB_FILE = "users.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------
# 4️⃣ Routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_or_user_id = request.form.get("email_or_user_id", "").strip()
        password = request.form.get("password", "").strip()

        if not email_or_user_id or not password:
            return render_template("login.html", error="Please enter both username and password")

        payload = {"email_or_user_id": email_or_user_id, "password": password}
        try:
            resp = requests.post(LOGIN_ENDPOINT, json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("user_id"):
                    username = data.get("user_id")
                    session["user"] = username
                    session["user_id"] = username
                    return redirect(url_for("homepage"))
                else:
                    return render_template("login.html", error="Invalid credentials")
            else:
                return render_template("login.html", error=f"Login failed ({resp.status_code})")
        except requests.RequestException as e:
            return render_template("login.html", error=f"Backend unreachable: {e}")

    return render_template("login.html")


@app.route("/homepage")
def homepage():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    transactions = []

    try:
        res = requests.get(f"{FASTAPI_URL}/homepage/transactions/{username}?limit=10", timeout=5)
        if res.status_code == 200:
            transactions = res.json()
    except requests.exceptions.RequestException:
        pass

    return render_template("homepage.html", user=username, transactions=transactions)


@app.route("/chatbot")
def chatbot_page():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("chatbot.html")


@app.route("/chatbot_api", methods=["POST"])
def chatbot_api():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    message = data.get("message", "").strip()
    user_id = session["user"]

    try:
        response_text = chatbot.process_message(user_id, message)
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"response": f"Error processing message: {str(e)}"})


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.clear()
    return redirect(url_for("login"))

# -----------------------------
# 5️⃣ Run app
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, debug=True)
