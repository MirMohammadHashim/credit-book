import os
from functools import lru_cache

import boto3
import pymysql
from flask import Flask, jsonify

app = Flask(__name__)

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ.get("DB_NAME", "creditbook")
DB_USER = os.environ.get("DB_USER", "admin")


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
