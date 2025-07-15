from flask import Flask, jsonify, request
from datetime import datetime
import os
import pickle
from threading import Lock

app = Flask(__name__)
app.is_ready = False

class OrderItem:
    def __init__(self, id: str, product_id: str, order_id: str, quantity: int):
        self.id = id
        self.product_id = product_id
        self.order_id = order_id
        self.quantity = int(quantity)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "order_id": self.order_id,
            "quantity": self.quantity,
        }
            
class Order:
    def __init__(self, id: str, user_id: str, time: str, total_price_in_cents: int, address_name: str,
                 address1: str, address2: str, credit_card_company: str, credit_card_number: str, credit_card_expiry: str, shipping_workflow_id:str):
        self.id = id
        self.user_id = user_id
        self.time = time
        self.total_price_in_cents = int(total_price_in_cents)
        self.address_name = address_name
        self.address1 = address1
        self.address2 = address2
        self.credit_card_company = credit_card_company
        self.credit_card_number = credit_card_number
        self.credit_card_expiry = credit_card_expiry
        self.shipping_workflow_id = shipping_workflow_id
        self.shipping_done = False

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "time": self.time,
            "total_price_in_cents": self.total_price_in_cents,
            "address_name": self.address_name,
            "address1": self.address1,
            "address2": self.address2,
            "credit_card_company": self.credit_card_company,
            "credit_card_number": self.credit_card_number,
            "credit_card_expiry": self.credit_card_expiry,
            "shipping_workflow_id": self.shipping_workflow_id,
            "shipping_done": self.shipping_done
        }
    
ORDER_FILE = "orders.pkl"
ITEMS_FILE = "items.pkl"

try:
    if os.path.exists(ORDER_FILE):
        with open(ORDER_FILE, "rb") as f:
            orders = pickle.load(f)
    else:
        orders = [
            Order("1", "1", datetime.now().isoformat(), 12499, "Alice Smith", "123 Main St", "Apt 4", "Visa", "4111111111111111", "12/25", "1234"),
            Order("2", "2", datetime.now().isoformat(), 12499, "Bob Jones", "123 Main St", "Apt 4", "Visa", "4111111111111111", "12/25", "1234")
        ]

        # Save initial state
        with open(ORDER_FILE, "wb") as f:
            pickle.dump(orders, f)

    # Load persisted data if available
    if os.path.exists(ITEMS_FILE):
        with open(ITEMS_FILE, "rb") as f:
            order_items = pickle.load(f)
    else:
        order_items = [
            OrderItem("1", "1", "1", 1),
            OrderItem("2", "2", "1", 1),
            OrderItem("3", "2", "2", 1),
            OrderItem("4", "3", "2", 1),
            OrderItem("5", "5", "2", 3),
            OrderItem("6", "6", "2", 2),
            OrderItem("7", "7", "2", 3),
            OrderItem("8", "8", "2", 1),
        ]

        # Save initial state
        with open(ITEMS_FILE, "wb") as f:
            pickle.dump(order_items, f)

    app.is_ready = True
except:
    app.is_ready = False

lock = Lock()

@app.route("/api/orders/<user_id>", methods=["GET"])
def get_orders_by_user(user_id):
    with lock:
        user_orders = [order.to_dict() for order in orders if order.user_id == user_id]
    return jsonify(user_orders)

@app.route("/api/orderitems", methods=["GET"])
def get_order_items():
    with lock:
        items = [item.to_dict() for item in order_items]
    return jsonify(items)

@app.route("/api/orders/<order_id>/shipping_done", methods=["POST"])
def update_shipping_done(order_id):
    data = request.get_json()
    if "shipping_done" not in data:
        return jsonify({"error": "Missing field: shipping_done"}), 400

    # Look up the order
    with lock:
        for order in orders:
            if order.id == order_id:
                order.shipping_done = bool(data["shipping_done"])
                return jsonify(order.to_dict()), 200

    return jsonify({"error": "Order not found"}), 404

@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()

    required_fields = [
        "id", "user_id", "total_price_in_cents", "address_name", "address1", "address2",
        "credit_card_company", "credit_card_number", "credit_card_expiry", "shipping_workflow_id"
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    with lock:
        if any(order.id == data["id"] for order in orders):
            return jsonify({"error": "Order ID already exists"}), 409

        order = Order(
            id=data["id"],
            user_id=data["user_id"],
            time=datetime.now().isoformat(),
            total_price_in_cents=data["total_price_in_cents"],
            address_name=data["address_name"],
            address1=data["address1"],
            address2=data["address2"],
            credit_card_company=data["credit_card_company"],
            credit_card_number=data["credit_card_number"],
            credit_card_expiry=data["credit_card_expiry"],
            shipping_workflow_id=data["shipping_workflow_id"]
        )
        orders.append(order)

    return jsonify({"success": "Order created."}), 201

@app.route("/api/orderitems", methods=["POST"])
def create_order_item():
    data = request.get_json()

    required_fields = ["id", "product_id", "order_id", "quantity"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    with lock:
        if any(item.id == data["id"] for item in order_items):
            return jsonify({"error": "OrderItem ID already exists"}), 409

        item = OrderItem(
            id=data["id"],
            product_id=data["product_id"],
            order_id=data["order_id"],
            quantity=data["quantity"]
        )
        order_items.append(item)
    return jsonify(item.to_dict()), 200

@app.route("/healthz")
def healthz():
    if lock.acquire(timeout=1):  # try for 1 second
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