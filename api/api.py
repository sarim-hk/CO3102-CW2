from flask import Flask, request, jsonify
import database
import sqlite3
import argon2

app = Flask(__name__)

with database.Database() as db:
    db._create_tables()
    db._populate_uvc_codes()

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    request_email = data.get("email")
    request_password = data.get("password")

    with database.Database() as db:
        saved_password = db.get_login(request_email)

    if saved_password and request_password:
        if argon2.verify_password(saved_password, request_password.encode()):
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "failed"}), 401
    else:
        return jsonify({"status": "failed"}), 400

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name")
    dob = data.get("dob")
    uvc = data.get("uvc")
    constituency_id = data.get("constituency_id")

    # Hash the password using argon2
    hashed_password = argon2.hash_password(password.encode())

    with database.Database() as db:
        # Check if the email is already registered
        if db.is_email_registered(email):
            return jsonify({"status": "failed", "message": "Email already registered"}), 400

        # Check if the UVC is valid and not used
        if not db.is_uvc_valid(uvc):
            return jsonify({"status": "failed", "message": "Invalid or already used UVC"}), 400

        # Register the voter
        voter_id = db.register_voter(email, full_name, dob, hashed_password, uvc, constituency_id)

    if voter_id:
        return jsonify({"status": "success", "voter_id": voter_id})
    else:
        return jsonify({"status": "failed", "message": "Registration failed"}), 500
            

"""
@app.route("/gevs/constituency/<constituency_name>", methods=["GET"])
def get_constituency_vote_count(constituency_name):
    if constituency_name in constituency_data:
        return jsonify({"constituency": constituency_name, "result": constituency_data[constituency_name]})
    else:
        return jsonify({"error": "Constituency not found"}), 404

# Endpoint to return the election result by listing all MP seats won across all electoral districts for every political party
@app.route("/gevs/results", methods=["GET"])
def get_election_results():
    return jsonify(results_data)
"""

if __name__ == "__main__":
    app.run(debug=True, port=5001)