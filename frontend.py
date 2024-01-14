from flask import Flask, render_template, request, redirect, url_for, session
import secrets
import requests

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

API_BASE_URL = "http://localhost:5001/gevs"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # API request to check login
        api_url = f"{API_BASE_URL}/login"
        payload = {"email": email, "password": password}
        
        response = requests.post(api_url, json=payload)

        if response.status_code == 200 and response.json().get("status") == "success":
            session["email"] = email
            return redirect(url_for("dashboard"))
        else:
            error_message = "Invalid email or password. Please try again."
            return render_template("login.html", error_message=error_message)

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
            return redirect(url_for("dashboard"))
        else:
            error_message = response.json().get("message", "Registration failed. Please try again.")
            return render_template("register.html", error_message=error_message)

    return render_template("register.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)
