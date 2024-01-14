from flask import Flask, render_template, request, redirect, url_for, session
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

        response = requests.get(f"{API_BASE_URL}/constituencies")
        print(response)
        if response.json().get("status") == "success":
            constituencies = response.json().get("constituencies")

        return render_template("register.html", constituencies=constituencies)

@app.route("/voter_dashboard", methods=["GET", "POST"])
def voter_dashboard():
    email = session.get("email")

    response = requests.get(f"{API_BASE_URL}/candidates")
    if response.json().get("status") == "success":
        constituency_candidates = response.json().get("candidates")
    else:
        constituency_candidates = None

    api_url = f"{API_BASE_URL}/check_vote_status"
    payload = {"email": email}
    response = requests.get(api_url, json=payload)

    if response.json().get("status") == "success":
        has_voted = response.json().get("has_voted")
    else:
        has_voted = None

    api_url = f"{API_BASE_URL}/voter_constituency"
    payload = {"voter_id": email}
    response = requests.get(api_url, json=payload)
    
    if response.json().get("status") == "success":
        voter_constituency = response.json().get("voter_constituency")
    else:
        voter_constituency = None

    return render_template("voter_dashboard.html", email=email, has_voted=has_voted, constituency_candidates=constituency_candidates, voter_constituency=voter_constituency)

@app.route("/commissioner_dashboard", methods=["GET", "POST"])
def commissioner_dashboard():
    email = session.get("email")
    return render_template("commissioner_dashboard.html", email=email)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
