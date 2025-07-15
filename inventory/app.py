import random
import os
import pickle
import requests
from flask import Flask, jsonify, request
from threading import Lock

app = Flask(__name__)
app.is_ready = False

STOCKS_FILE = "stocks.pkl"
stocks: dict[str, int] = {}

RESERVATIONS_FILE = "reservations.pkl"
reservations = {}

try:
    if os.path.exists(STOCKS_FILE):
        with open(STOCKS_FILE, "rb") as f:
            stocks = pickle.load(f)
    else:
        # init stock randomly
        counter = 5
        while counter > 0:
            try:
                response = requests.get("http://product:5000/api/products")
                response.raise_for_status()
                products = response.json()
                for p in products:
                    id = str(p.get("id"))
                    quantity = random.randint(0, 100)
                    stocks[id] = quantity
                break
            except Exception:
                counter -= 1
                continue
        # Save initial state
        with open(STOCKS_FILE, "wb") as f:
            pickle.dump(stocks, f)

    if os.path.exists(STOCKS_FILE):
        with open(STOCKS_FILE, "rb") as f:
            reservations = pickle.load(f)
    else:
        with open(STOCKS_FILE, "wb") as f:
            pickle.dump(reservations, f)
    
    app.is_ready = True
except:
    app.is_ready = False
    
lock = Lock()

@app.route("/api/inventory/<product_id>", methods=["GET"])
def get_stock(product_id):
    with lock:
        stock = stocks.get(product_id, 0)
    return jsonify({"product_id": product_id, "stock": stock})

@app.route("/api/inventory/check_and_reserve", methods=["POST"])
def check_and_reserve():
    data = request.get_json()
    product_ids = data.get("product_ids")
    quantities = data.get("quantities")
    reservation_id = data.get("reservation_id")

    if not reservation_id:
        return jsonify({"error": "reservation_id is required"}), 400

    if not isinstance(product_ids, list) or not isinstance(quantities, list):
        return jsonify({"error": "product_ids and quantities must be lists"}), 400
    
    if len(product_ids) != len(quantities):
        return jsonify({"error": "product_ids and quantities must be the same length"}), 400

    with lock:
        if reservation_id in reservations:
            # Already reserved — idempotent success
            return jsonify({"success": True, "reserved": reservations[reservation_id]}), 200
        # Check availability
        for product_id, quantity in zip(product_ids, quantities):
            if stocks.get(product_id, 0) < quantity:
                return jsonify({"success": False, "product_id": product_id, "available": stocks.get(product_id, 0)}), 500

        # Reserve stock
        for product_id, qty in zip(product_ids, quantities):
            stocks[product_id] -= qty

        reservations[reservation_id] = {
            "product_ids": product_ids,
            "quantities": quantities,
            "status": "active"
        }

        with open(STOCKS_FILE, "wb") as f:
            pickle.dump(stocks, f)

        with open(RESERVATIONS_FILE, "wb") as f:
            pickle.dump(reservations, f)

    return jsonify({"success": True, "reserved": dict(zip(product_ids, quantities))}), 200

@app.route("/api/inventory/release", methods=["POST"])
def release_stock():
    data = request.get_json()
    reservation_id = data.get("reservation_id")

    if not reservation_id:
        return jsonify({"error": "reservation_id is required"}), 400

    with lock:
        reservation = reservations.get(reservation_id)
        if not reservation or reservation["status"] == "released":
            return jsonify({"success": True, "message": "Already released or unknown"}), 200
        
        for product_id, qty in zip(reservation["product_ids"], reservation["quantities"]):
            stocks[product_id] = stocks.get(product_id, 0) + qty

        reservation["status"] = "released"

        with open(STOCKS_FILE, "wb") as f:
            pickle.dump(stocks, f)

        with open(RESERVATIONS_FILE, "wb") as f:
            pickle.dump(reservations, f)

    return jsonify({"success": True, "restored": reservation}), 200

@app.route("/healthz")
def healthz():
    if lock.acquire(timeout=2):  # try for 1 second
        try:
            return jsonify(status="alive"), 200
        finally:
            lock.release()
    else:
        return jsonify(status="locked"), 500

@app.route("/ready")
def ready():
    if not app.is_ready:
        return jsonify(status="not ready"), 503
    else:
        with lock:
            return jsonify(status="ready"), 200