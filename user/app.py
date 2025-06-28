from flask import Flask, request, jsonify, abort
import os
import pickle
from threading import Lock

app = Flask(__name__)
app.is_ready = False

class User:
    def __init__(self, id: str, username: str, password: str, realname: str, email: str):
        self.id = id
        self.username = username
        self.password = password
        self.realname = realname
        self.email = email

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "realname": self.realname,
            "email": self.email,
            "password": self.password,
        }
    
USERS_FILE = "users.pkl"

# Load persisted data if available
try:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "rb") as f:
            users = pickle.load(f)
    else:
        users = [
            User("1", "alice", "pass123", "Alice Smith", "alice@example.com"),
            User("2", "bob", "secret", "Bob Jones", "bob@example.com"),
            User("3", "user2", "password", "Testuser", "test@email.com")
        ]

        # Save initial state
        with open(USERS_FILE, "wb") as f:
            pickle.dump(users, f)
    app.is_ready = True
except:
    app.is_ready = False

lock = Lock()

def find_by_id(items, id):
    return next((item for item in items if item.id == id), None)

@app.route("/api/users/<id>", methods=["GET"])
def get_user(id):
    with lock:
        user = find_by_id(users, id)
    if user:
        return jsonify(user.to_dict())
    abort(404)

@app.route("/api/users/username/<username>", methods=["GET"])
def get_user_by_name(username):
    with lock:
        user = next((item for item in users if item.username == username), None)
    if user:
        return jsonify(user.to_dict())
    abort(404)

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