from flask import Flask, jsonify
from flask_cors import CORS
from db import db  # import db from db.py

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": [
    "http://localhost:5173",
    "https://python-frontend-9vgt.onrender.com"
]}})

# Import and register auth blueprint
from auth import auth_bp
app.register_blueprint(auth_bp, url_prefix="/auth")

# Import and register inventory blueprint
from inventory_routes import inventory_bp
app.register_blueprint(inventory_bp, url_prefix="/electronics")

@app.route("/test-db")
def test_db():
    try:
        collections = db.list_collection_names()
        return jsonify({
            "message": "Connected to MongoDB!",
            "database": db.name,
            "collections": collections
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
