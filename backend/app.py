from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

from api.admin_routes import admin_bp
from api.user_routes import user_bp
from api.auth_routes import auth_bp

# -------------------------------------------------
# APP
# -------------------------------------------------
app = Flask(__name__)

# 🔥 CORS (DEV İÇİN HER ŞEYE AÇIK)
CORS(app, resources={r"/*": {"origins": "*"}})

# -------------------------------------------------
# BLUEPRINTLER
# -------------------------------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)

# -------------------------------------------------
# DİZİNLER
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.route("/health")
def health():
    return jsonify({"status": "backend ayakta"})

# -------------------------------------------------
# FRONTEND SERVE
# -------------------------------------------------
@app.route("/")
def login_page():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route("/admin")
def admin_page():
    return send_from_directory(FRONTEND_DIR, "admin.html")

@app.route("/user")
def user_page():
    return send_from_directory(FRONTEND_DIR, "user.html")

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)

@app.route("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "images"), filename)

# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
