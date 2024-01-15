from flask import Flask, render_template, request, redirect, url_for, session
from api import database
import secrets
import requests

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

API_BASE_URL = "http://localhost:5001/gevs"

@app.before_request
def before_request():
    if request.endpoint and "dashboard" in request.endpoint and not session.get("email"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # API request to check login
        api_url = f"{API_BASE_URL}/login"
        payload = {"email": email, "password": password}
        response = requests.post(api_url, json=payload)

        if response.json().get("status") == "success":
            session["email"] = email
            if response.json().get("account") == "voter":
                return redirect(url_for("voter_dashboard"))
            elif response.json().get("account") == "commissioner":
                return redirect(url_for("commissioner_dashboard"))
        else:
            error_message = "Invalid email or password. Please try again."
            return render_template("login.html", error_message=error_message)

    elif request.method == "GET":
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        full_name = request.form["full_name"]
        dob = request.form["dob"]
        uvc = request.form["uvc"]
        constituency_id = request.form["constituency_id"]

        # API request to register
        api_url = f"{API_BASE_URL}/register"
        payload = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "dob": dob,
            "uvc": uvc,
            "constituency_id": constituency_id
        }

        response = requests.post(api_url, json=payload)

        if response.json().get("status") == "success":
            session["email"] = email
            return redirect(url_for("login"))
        else:
            error_message = response.json().get("message", "Registration failed. Please try again.")
            return render_template("register.html", error_message=error_message)

    elif request.method == "GET":
        with database.Database(database_file="api/database.db") as db:
            constituencies = db.get_constituencies()

        return render_template("register.html", constituencies=constituencies)

@app.route("/voter_dashboard", methods=["GET", "POST"])
def voter_dashboard():
    success_message, error_message = None, None
    email = session.get("email")

    with database.Database(database_file="api/database.db") as db:
        constituency_candidates = db.get_all_candidates()
        has_voted = db.has_voter_voted(email)
        voter_constituency = db.get_voter_constituency(email)

    if request.method == "POST":
        candidate_id = request.form.get("candidate")

        with database.Database(database_file="api/database.db") as db:
            if db.cast_vote(email, candidate_id):
                success_message = "Vote submitted successfully!"
            else:
                error_message = "Failed to submit vote."

    return render_template("voter_dashboard.html", email=email, has_voted=has_voted,
                           constituency_candidates=constituency_candidates, voter_constituency=voter_constituency,
                           success_message=success_message, error_message=error_message)

@app.route("/commissioner_dashboard", methods=["GET", "POST"])
def commissioner_dashboard():
    email = session.get("email")
    return render_template("commissioner_dashboard.html", email=email)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
