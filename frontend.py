from flask import Flask, render_template, request, redirect, url_for, session
from api import database
import secrets
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.secret_key = secrets.token_hex(16)

API_BASE_URL = "http://localhost:5001/gevs"

@app.before_request
def before_request():
    if request.endpoint and "dashboard" in request.endpoint and not session.get("email"):
        return redirect(url_for("login"))

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

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
    email = session.get("email")
    with database.Database(database_file="api/database.db") as db:
        election_status = db.get_election_status()
        constituency_candidates = db.get_all_candidates()
        has_voted = db.has_voter_voted(email)
        voter_constituency = db.get_voter_constituency(email)

    if election_status == "NOTOPEN":
        return render_template("thanks.html", message="The election is not yet open. Come back when it is.")
    elif election_status == "CONCLUDED":
        return render_template("thanks.html", message="The election has concluded.")
    elif has_voted and election_status == "ONGOING":
        return render_template("thanks.html", message="Your vote has been submitted and the election is ongoing.")
    elif request.method == "POST":
        candidate_id = request.form.get("candidate")
        with database.Database(database_file="api/database.db") as db:
            if db.cast_vote(email, candidate_id):
                return render_template("thanks.html", message="Your vote has been submitted and the election is ongoing.")
    else:
        return render_template("voter_dashboard.html", email=email, constituency_candidates=constituency_candidates, voter_constituency=voter_constituency)

@app.route("/commissioner_dashboard", methods=["GET", "POST"])
def commissioner_dashboard():
    email = session.get("email")
    if request.method == "POST":
        new_status = request.form.get("new_status")
        with database.Database(database_file="api/database.db") as db:
            db.update_election_status(new_status)

    with database.Database(database_file="api/database.db") as db:
        election_status = db.get_election_status()
        constituencies = db.get_constituencies()
        print(election_status)

        election_results = None
        if election_status == "CONCLUDED":
            response = requests.get(f"{API_BASE_URL}/results")
            election_results = response.json()

    return render_template("commissioner_dashboard.html", email=email, election_status=election_status, election_results=election_results, constituencies=constituencies)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
