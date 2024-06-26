from flask import Flask, request, jsonify
from flask_cors import cross_origin
import database
import argon2
from argon2.exceptions import VerifyMismatchError

app = Flask(__name__)

# Setup db init stuff
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

    hashed_password = argon2.hash_password(password.encode())

    with database.Database() as db:
        if db.is_email_registered(email):
            return jsonify({"status": "failed", "message": "Email already registered"}), 400

        if not db.is_uvc_valid(uvc):
            return jsonify({"status": "failed", "message": "Invalid or already used UVC"}), 400

        voter_id = db.register_voter(email, full_name, dob, hashed_password, uvc, constituency_id)

    if voter_id:
        return jsonify({"status": "success", "voter_id": voter_id})
    else:
        return jsonify({"status": "failed", "message": "Registration failed"}), 500

@app.route("/gevs/constituency/<constituency_name>", methods=["GET"])
@cross_origin(origin='http://127.0.0.1:5000', headers=['Content-Type', 'Authorization'])
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
        max_seat_count = max(result["seat"] for result in seat_results)
        winning_party = next((result["party"] for result in seat_results if result["seat"] == max_seat_count), "")
        
        # Check if thers a tie
        if list(result["seat"] for result in seat_results).count(max_seat_count) > 1:
            winner = "Hung Parliament"
        else:
            winner = winning_party
        
        seats_formatted = [{"party": result["party"], "seat": result["seat"]} for result in seat_results]

        response_data = {
            "status": "Completed",
            "winner": winner,
            "seats": seats_formatted
        }
        return jsonify(response_data)
    else:
        return jsonify({"status": "Ongoing"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5001)
