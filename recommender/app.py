from flask import Flask, jsonify, request
import os
import pickle
from threading import Lock

app = Flask(__name__)

DATA_FILE = "recommendations.pkl"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as f:
        recommendations = pickle.load(f)
else:
    recommendations = []
    with open(DATA_FILE, "wb") as f:
        pickle.dump(recommendations, f)

lock = Lock()

@app.route("/api/recommendations", methods=["GET"])
def get_recommendations():
    with lock:
        num_recommendations = min(request.args.get("num", 3, type=int), len(recommendations))
        recommended = recommendations[:num_recommendations]
    return jsonify(recommended)

@app.route("/api/recommendations", methods=["POST"])
def set_recommendations():
    data = request.get_json()

    if not isinstance(data, list):
        return jsonify({"error": "Request body must be a JSON list"}), 400

    with lock:
        global recommendations
        recommendations = data
        with open(DATA_FILE, "wb") as f:
            pickle.dump(recommendations, f)

    return jsonify({"success": True, "count": len(recommendations)}), 200
