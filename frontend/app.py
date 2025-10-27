from flask import Flask, render_template, request, redirect, url_for, session
import random

app = Flask(__name__)
app.secret_key = "secure_bank_ui"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Dummy authentication — replace with MySQL query if needed
        if username == "admin" and password == "password":
            session["user"] = username
            return redirect(url_for("select_algorithm"))
        else:
            return render_template("login.html", error="Invalid username or password.")
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

if __name__ == "__main__":
    app.run(debug=True)
