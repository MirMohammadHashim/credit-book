import datetime
import os
import re
from functools import lru_cache, wraps

import bcrypt
import boto3
import jwt
import pymysql
from flask import Flask, g, jsonify, request

app = Flask(__name__)

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ.get("DB_NAME", "creditbook")
DB_USER = os.environ.get("DB_USER", "admin")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@lru_cache(maxsize=None)
def get_secret(name):
    ssm = boto3.client("ssm", region_name=REGION)
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=get_secret("/creditbook/db_password"),
        database=DB_NAME,
        connect_timeout=5,
    )


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Login required"}), 401
        token = header[len("Bearer "):]
        try:
            payload = jwt.decode(
                token, get_secret("/creditbook/jwt_secret"), algorithms=["HS256"]
            )
        except jwt.InvalidTokenError:
            return jsonify({"error": "Login required"}), 401
        g.user_id = payload["user_id"]
        return f(*args, **kwargs)

    return wrapper


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/db-check")
def db_check():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
    finally:
        conn.close()
    return jsonify({"db": "ok", "users": count})


@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not EMAIL_PATTERN.match(email) or len(email) > 255:
        return jsonify({"error": "Enter a valid email"}), 400
    if len(password) < 8 or len(password.encode()) > 72:
        return jsonify({"error": "Password must be 8 to 72 characters"}), 400

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
                    (email, password_hash),
                )
            except pymysql.err.IntegrityError:
                return jsonify({"error": "Email already registered"}), 409
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Account created"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    wrong = (jsonify({"error": "Wrong email or password"}), 401)
    if len(password.encode()) > 72:
        return wrong

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None or not bcrypt.checkpw(password.encode(), row[1].encode()):
        return wrong

    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    token = jwt.encode(
        {"user_id": row[0], "exp": expires},
        get_secret("/creditbook/jwt_secret"),
        algorithm="HS256",
    )
    return jsonify({"token": token})


@app.route("/api/me")
@login_required
def me():
    return jsonify({"user_id": g.user_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
