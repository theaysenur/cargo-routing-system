# api/auth_routes.py
from flask import Blueprint, request, jsonify
from database.db import get_db_connection

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, role
        FROM users
        WHERE username = ? AND password = ?
    """, (username, password))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Kullanıcı adı veya şifre yanlış"}), 401

    return jsonify({
        "user_id": row[0],
        "role": row[1]
    })


# -------------------------------------------------
# REGISTER (SADECE USER)
# -------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json or {}

    full_name = (data.get("full_name") or "").strip()
    username  = (data.get("username") or "").strip()
    password  = (data.get("password") or "").strip()

    if not full_name or not username or not password:
        return jsonify({"error": "Tüm alanlar zorunlu"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # username kontrolü
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Bu kullanıcı adı zaten mevcut"}), 400

    cursor.execute("""
        INSERT INTO users (full_name, username, password, role)
        VALUES (?, ?, ?, 'USER')
    """, (full_name, username, password))

    conn.commit()
    conn.close()

    return jsonify({"message": "Kayıt başarılı"})
