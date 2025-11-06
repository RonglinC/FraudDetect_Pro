from flask import Flask, render_template, request, redirect, url_for, session
import requests
import os

app = Flask(__name__)
app.secret_key = "secret"

FASTAPI_URL = "http://127.0.0.1:8000"
LOGIN_ENDPOINT = f"{FASTAPI_URL}/auth/login"

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
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]

    res = requests.get(f"{FASTAPI_URL}/transactions/{username}")
    if res.status_code == 200:
        transactions = res.json()["transactions"]
    else:
        transactions = []
    return render_template("homepage.html", username=username, transactions=transactions)

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
    
    # Here you can call your AI or logic
    bot_response = f"Echo: {message}"  # placeholder logic

    return jsonify({"response": bot_response})



@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, debug=True)
