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


@app.route("/api/customers", methods=["POST"])
@login_required
def add_customer():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()

    if not name or len(name) > 100:
        return jsonify({"error": "Name is required (up to 100 characters)"}), 400
    if len(phone) > 20:
        return jsonify({"error": "Phone is too long"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO customers (user_id, name, phone) VALUES (%s, %s, %s)",
                (g.user_id, name, phone or None),
            )
            new_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    return jsonify({"id": new_id, "name": name}), 201


@app.route("/api/customers", methods=["GET"])
@login_required
def list_customers():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, phone FROM customers WHERE user_id = %s ORDER BY name",
                (g.user_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return jsonify([{"id": r[0], "name": r[1], "phone": r[2]} for r in rows])


from datetime import date
from decimal import Decimal, InvalidOperation


def owns_customer(cur, customer_id):
    cur.execute(
        "SELECT id FROM customers WHERE id = %s AND user_id = %s",
        (customer_id, g.user_id),
    )
    return cur.fetchone() is not None


@app.route("/api/customers/<int:customer_id>/entries", methods=["POST"])
@login_required
def add_entry(customer_id):
    data = request.get_json(silent=True) or {}
    entry_type = str(data.get("type", ""))
    note = str(data.get("note", "")).strip()

    try:
        amount = Decimal(str(data.get("amount", "")))
    except InvalidOperation:
        return jsonify({"error": "Amount must be a number"}), 400
    if (
        not amount.is_finite()
        or amount <= 0
        or amount > Decimal("99999999.99")
        or amount.as_tuple().exponent < -2
    ):
        return jsonify({"error": "Amount must be positive, up to 2 decimals"}), 400
    if entry_type not in ("credit", "payment"):
        return jsonify({"error": "Type must be credit or payment"}), 400
    if len(note) > 255:
        return jsonify({"error": "Note is too long"}), 400
    try:
        entry_date = date.fromisoformat(
            str(data.get("entry_date") or date.today().isoformat())
        )
    except ValueError:
        return jsonify({"error": "Date must look like 2026-11-22"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if not owns_customer(cur, customer_id):
                return jsonify({"error": "Customer not found"}), 404
            cur.execute(
                "INSERT INTO entries (customer_id, amount, type, note, entry_date) "
                "VALUES (%s, %s, %s, %s, %s)",
                (customer_id, amount, entry_type, note or None, entry_date),
            )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Entry added"}), 201


@app.route("/api/customers/<int:customer_id>/entries", methods=["GET"])
@login_required
def list_entries(customer_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if not owns_customer(cur, customer_id):
                return jsonify({"error": "Customer not found"}), 404
            cur.execute(
                "SELECT id, amount, type, note, entry_date FROM entries "
                "WHERE customer_id = %s ORDER BY entry_date DESC, id DESC",
                (customer_id,),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COALESCE(SUM(CASE WHEN type = 'credit' THEN amount "
                "ELSE -amount END), 0) FROM entries WHERE customer_id = %s",
                (customer_id,),
            )
            balance = cur.fetchone()[0]
    finally:
        conn.close()
    entries = [
        {
            "id": r[0],
            "amount": str(r[1]),
            "type": r[2],
            "note": r[3],
            "entry_date": r[4].isoformat(),
        }
        for r in rows
    ]
    return jsonify({"balance": str(balance), "entries": entries})


@app.route("/api/summary")
@login_required
def summary():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id, c.name, c.phone, "
                "COALESCE(SUM(CASE WHEN e.type = 'credit' THEN e.amount "
                "ELSE -e.amount END), 0) AS balance "
                "FROM customers c LEFT JOIN entries e ON e.customer_id = c.id "
                "WHERE c.user_id = %s "
                "GROUP BY c.id, c.name, c.phone ORDER BY balance DESC",
                (g.user_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return jsonify(
        [{"id": r[0], "name": r[1], "phone": r[2], "balance": str(r[3])} for r in rows]
    )
