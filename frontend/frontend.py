# frontend/frontend.py
from flask import Flask, render_template, request, redirect, url_for, session
import requests

app = Flask(__name__, template_folder="templates")
app.secret_key = "secure_bank_ui"

BACKEND_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{BACKEND_URL}/auth/login"

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
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("homepage.html", user=session["user"])

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
    app.run(port=5000, debug=True)
