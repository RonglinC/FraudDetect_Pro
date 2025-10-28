from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import requests

app = Flask(__name__)
app.secret_key = "secure_bank_ui"

# backend base url
BACKEND_URL = "http://localhost:8000"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Server-side authentication against backend /auth/login
        try:
            resp = requests.post(
                f"{BACKEND_URL}/auth/login",
                json={"username": username, "password": password},
                timeout=5,
            )
        except requests.RequestException as e:
            return render_template("login.html", error=f"Backend unreachable: {e}")

        if resp.status_code == 200:
            data = resp.json()
            session["user"] = data.get("username")
            session["user_id"] = data.get("user_id")
            session["token"] = data.get("token")
            return redirect(url_for("select_algorithm"))
        else:
            try:
                detail = resp.json().get("detail")
            except Exception:
                detail = resp.text or "Invalid username or password."
            return render_template("login.html", error=detail)
    return render_template("login.html")

@app.route("/select", methods=["GET", "POST"])
def select_algorithm():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        session["algorithm"] = request.form["algorithm"]
        return redirect(url_for("result"))

    return render_template("select.html", username=session["user"])

@app.route("/result")
def result():
    if "algorithm" not in session:
        return redirect(url_for("select_algorithm"))

    algorithm = session["algorithm"]
    # Mock prediction result (you can connect to your ML model here)
    result = random.choice(["Fraudulent Transaction", "Legitimate Transaction"])
    confidence = round(random.uniform(80, 99.9), 2)

    return render_template("result.html", algorithm=algorithm, result=result, confidence=confidence)

@app.route("/exit")
def exit():
    session.clear()
    return render_template("exit.html")


@app.route("/my_transactions")
def my_transactions():
    # server-side call to backend protected endpoint using stored token
    if "token" not in session:
        return redirect(url_for("login"))
    headers = {"Authorization": f"Bearer {session['token']}"}
    try:
        resp = requests.get(f"{BACKEND_URL}/auth/me/transactions", headers=headers, timeout=5)
    except requests.RequestException as e:
        return render_template("select.html", username=session.get("user"), error=f"Backend error: {e}")

    if resp.status_code == 200:
        txns = resp.json()
        # Render a simple template or return JSON; templates not added so return JSON for now
        return jsonify(txns)
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        return render_template("select.html", username=session.get("user"), error=detail)

if __name__ == "__main__":
    app.run(debug=True)
