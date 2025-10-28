from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from db import db

auth_bp = Blueprint("auth", __name__)
users_collection = db["users"]

# ---------- Register ----------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"error": "Name and password are required"}), 400

    if users_collection.find_one({"name": name}):
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)
    users_collection.insert_one({"name": name, "password": hashed_pw})

    return jsonify({"message": "User registered successfully"}), 201


# ---------- Login ----------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"error": "Name and password are required"}), 400

    user = users_collection.find_one({"name": name})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    # ✅ return a token or flag so frontend knows user is logged in
    return jsonify({
        "message": f"Welcome, {name}!",
        "success": True,
        "user": {"name": name}
    }), 200
