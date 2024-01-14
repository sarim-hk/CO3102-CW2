from flask import Flask, request, jsonify, session, redirect, url_for, render_template
import database
import argon2
from argon2.exceptions import VerifyMismatchError
import requests

app = Flask(__name__)

# Database setup
with database.Database() as db:
    db._create_tables()
    db._populate_uvc_codes()
    db._populate_other_tables()

@app.route("/gevs/login", methods=["POST"])
def login():
    data = request.get_json()
    request_email = data.get("email")
    request_password = data.get("password")

    # Check commissioner login
    with database.Database() as db:
        saved_password = db.get_commissioner_login(request_email)

    if saved_password and request_password:
        try:
            argon2.verify_password(saved_password, request_password.encode())
            return jsonify({"status": "success", "account": "commissioner"})
        except VerifyMismatchError:
            pass

    # Check voter login
    with database.Database() as db:
        saved_password = db.get_login(request_email)

    if saved_password and request_password:
        try:
            argon2.verify_password(saved_password, request_password.encode())
            return jsonify({"status": "success", "account": "voter"})
        except VerifyMismatchError:
            return jsonify({"status": "failed"}), 401
    else:
        return jsonify({"status": "failed"}), 400

@app.route("/gevs/register", methods=["POST"])
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

@app.route("/gevs/constituency/<constituency_name>", methods=["GET"])
def get_constituency_results(constituency_name):
    with database.Database() as db:
        results = db.get_constituency_results(constituency_name)

    if results:
        return jsonify({
            "constituency": constituency_name,
            "results": [{"candidate": result[0], "party": result[1], "vote_count": result[2]} for result in results]
        })
    else:
        return jsonify({"status": "failed", "message": "Failed to fetch constituency results"}), 500

@app.route("/gevs/results", methods=["GET"])
def get_election_results():
    with database.Database() as db:
        seat_results = db.get_seats_by_party()

    if seat_results:
        winner = max(seat_results, key=lambda x: x["seat"])
        seats_formatted = [{"party": result["party"], "seat": result["seat"]} for result in seat_results]

        response_data = {
            "status": "Completed",
            "winner": winner["party"],
            "seats": seats_formatted
        }
        return jsonify(response_data)
    else:
        return jsonify({"status": "Ongoing"}), 200

@app.route("/gevs/candidates", methods=["GET"])
def get_candidates():
    with database.Database() as db:
        candidates = db.get_all_candidates()

    if candidates:
        return jsonify({"status": "success", "candidates": candidates})
    else:
        return jsonify({"status": "failed", "message": "Failed to fetch candidates"}), 500

@app.route("/gevs/constituencies", methods=["GET"])
def get_constituencies():
    with database.Database() as db:
        constituencies = db.get_constituencies()

    if constituencies:
        return jsonify({"status": "success", "constituencies": constituencies})
    else:
        return jsonify({"status": "failed", "message": "Failed to fetch constituencies"}), 500

@app.route("/gevs/vote", methods=["POST"])
def vote():
    data = request.get_json()
    voter_email = session.get("email")
    candidate_id = data.get("candidate_id")

    if not voter_email:
        return jsonify({"status": "failed", "message": "User not logged in"}), 401

    with database.Database() as db:
        # Check if the voter has already voted
        if db.has_voter_voted(voter_email):
            return jsonify({"status": "failed", "message": "Voter has already voted"}), 400

        # Cast the vote
        if db.cast_vote(voter_email, candidate_id):
            return jsonify({"status": "success", "message": "Vote submitted successfully"})
        else:
            return jsonify({"status": "failed", "message": "Failed to submit vote"}), 500

@app.route("/gevs/check_vote_status", methods=["GET"])
def check_vote_status():
    data = request.get_json()
    voter_email = data.get("email")

    if not voter_email:
        return jsonify({"status": "failed", "message": "Email not provided"}), 400

    with database.Database() as db:
        has_voted = db.has_voter_voted(voter_email)

    return jsonify({"status": "success", "has_voted": has_voted})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
