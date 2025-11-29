from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from model import train_user, verify_user_keystrokes

app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY_HERE"

# ---------------------------------------------------
# Database helpers
# ---------------------------------------------------
def get_db():
    conn = sqlite3.connect("project.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            attempts INTEGER DEFAULT 0,
            locked_until TEXT
        )
    """)

    # clicks table
    c.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # keystrokes table
    c.execute("""
        CREATE TABLE IF NOT EXISTS keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            key TEXT,
            press_time REAL,
            release_time REAL,
            dwell REAL,
            flight REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def create_default_user():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("1234"))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

init_db()
create_default_user()

# ---------------------------------------------------
# Utility: log click actions
# ---------------------------------------------------
def log_action(user_id, action):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clicks (user_id, action) VALUES (?, ?)",
        (user_id, action)
    )
    conn.commit()
    conn.close()

# ---------------------------------------------------
# Auth routes: register / login / logout
# ---------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            message = "Username and password are required."
            return render_template("register.html", message=message)

        hashed = generate_password_hash(password)

        conn = get_db()
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed)
            )
            conn.commit()
            user_id = c.lastrowid
            session["user_id"] = user_id
            conn.close()

            # بعد التسجيل نوجّه المستخدم لجمع بيانات الكيستروكس
            return redirect("/collect")

        except sqlite3.IntegrityError:
            conn.close()
            message = "Username already exists!"

    return render_template("register.html", message=message)

@app.route("/", methods=["GET", "POST"])
def login():
    message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, password, attempts, locked_until FROM users WHERE username=?",
            (username,)
        )
        user = cursor.fetchone()

        if not user:
            conn.close()
            return render_template("login.html", message="User not found!")

        user_id = user["id"]
        db_pass = user["password"]
        attempts = user["attempts"]
        locked_until = user["locked_until"]

        # Check lock
        if locked_until:
            locked_time = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
            if locked_time > datetime.now():
                conn.close()
                return render_template(
                    "login.html",
                    message=f"Account locked until {locked_time}"
                )

        # Check password
        if check_password_hash(db_pass, password):
            # reset attempts
            cursor.execute(
                "UPDATE users SET attempts=0, locked_until=NULL WHERE id=?",
                (user_id,)
            )
            conn.commit()
            conn.close()

            session["user_id"] = user_id
            log_action(user_id, "login_password_ok")

            # بعد نجاح الباسورد نوجهه لصفحة verify للـ keystroke
            return redirect("/verify_page")

        # wrong password
        attempts += 1
        log_action(user_id, "login_failed")

        if attempts >= 3:
            lock_time = (datetime.now() + timedelta(minutes=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            cursor.execute(
                "UPDATE users SET attempts=?, locked_until=? WHERE id=?",
                (attempts, lock_time, user_id)
            )
            message = "Too many attempts! Locked for 1 minute."
        else:
            cursor.execute(
                "UPDATE users SET attempts=? WHERE id=?",
                (attempts, user_id)
            )
            message = f"Wrong password! Attempts left: {3 - attempts}"

        conn.commit()
        conn.close()
        return render_template("login.html", message=message)

    return render_template("login.html", message=message)

@app.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id:
        log_action(user_id, "logout")
    session.clear()
    return redirect("/")

# ---------------------------------------------------
# Pages: collect / training / verify / dashboard
# ---------------------------------------------------
@app.route("/collect")
def collect_page():
    if "user_id" not in session:
        return redirect("/")
    return render_template("collect.html")

@app.route("/training")
def training_page():
    if "user_id" not in session:
        return redirect("/")
    return render_template("training.html")

@app.route("/verify_page")
def verify_page():
    if "user_id" not in session:
        return redirect("/")
    return render_template("verify.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# ---------------------------------------------------
# Keystroke logging APIs
# ---------------------------------------------------
@app.route("/log_keystroke", methods=["POST"])
def log_keystroke():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not logged in"})

    data = request.get_json() or {}
    user_id = session["user_id"]

    key = data.get("key")
    press_time = data.get("press_time")
    release_time = data.get("release_time")
    dwell = data.get("dwell")
    flight = data.get("flight")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO keystrokes (user_id, key, press_time, release_time, dwell, flight)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, key, press_time, release_time, dwell, flight))
    conn.commit()
    conn.close()

    return jsonify({"status": "saved"})

@app.route("/save_keystrokes", methods=["POST"])
def save_keystrokes():
    """تستخدم مع collect.html لو بترسل Array كاملة من الضغطات لمحاولة واحدة."""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not logged in"})

    strokes = request.get_json() or []
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    for k in strokes:
        cur.execute("""
            INSERT INTO keystrokes (user_id, key, press_time, release_time, dwell, flight)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            k.get("key"),
            k.get("press"),
            k.get("release"),
            k.get("dwell"),
            k.get("flight")
        ))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

# ---------------------------------------------------
# ML training & verification APIs
# ---------------------------------------------------
@app.route("/train_model", methods=["POST"])
def train_model_route():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Not logged in"})

    success = train_user(user_id)

    if success:
        log_action(user_id, "model_trained")
        return jsonify({"status": "success", "message": "Model trained successfully!"})
    return jsonify({"status": "error", "message": "Not enough samples!"})

@app.route("/verify_ml", methods=["POST"])
def verify_ml():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"valid": False, "message": "Not logged in"})

    data = request.get_json() or {}
    samples = data.get("samples", [])

    result = verify_user_keystrokes(user_id, samples)
    log_action(user_id, f"ml_verify_{'ok' if result else 'fail'}")

    # نحول النتيجة لـ bool عادي قبل الإرجاع
    return jsonify({"valid": bool(result)})

# ---------------------------------------------------
# Run App
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
