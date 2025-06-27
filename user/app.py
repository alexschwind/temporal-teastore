from flask import Flask, request, jsonify, abort
import os
import pickle
from threading import Lock
import hashlib

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

lock = Lock()

def find_by_id(items, id):
    return next((item for item in items if item.id == id), None)

app = Flask(__name__)

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