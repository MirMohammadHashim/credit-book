import os
import re
from functools import lru_cache

import bcrypt
import boto3
import pymysql
from flask import Flask, jsonify, request

app = Flask(__name__)

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ.get("DB_NAME", "creditbook")
DB_USER = os.environ.get("DB_USER", "admin")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@lru_cache(maxsize=1)
def get_db_password():
    ssm = boto3.client("ssm", region_name=REGION)
    response = ssm.get_parameter(Name="/creditbook/db_password", WithDecryption=True)
    return response["Parameter"]["Value"]


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=get_db_password(),
        database=DB_NAME,
        connect_timeout=5,
    )


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
