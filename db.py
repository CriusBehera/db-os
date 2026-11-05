"""Database helpers: connection, password hashing, users and students."""
import hashlib
import hmac
import os
import re

import mysql.connector
import streamlit as st


MAX_ATTEMPTS = 5   # wrong passwords before the account is locked
LOCK_MINUTES = 5


def get_connection():
    """Open a MySQL connection using settings from .streamlit/secrets.toml."""
    cfg = st.secrets["mysql"]
    options = dict(
        host=cfg["host"],
        port=int(cfg.get("port", 3306)),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        use_pure=True,  # pure-Python driver still supports TiDB's mysql_native_password login
    )
    if cfg.get("ssl_ca"):  # cloud databases need an encrypted (TLS) connection
        options.update(ssl_ca=cfg["ssl_ca"], ssl_verify_cert=True)
    return mysql.connector.connect(**options)


def run_query(sql, params=(), fetch=False):
    """Run one SQL statement. Returns rows (as dicts) when fetch=True."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ---------- Passwords (never store plain text) ----------

def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + ":" + digest.hex()


def check_password(password, stored):
    salt_hex, digest_hex = stored.split(":")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


# ---------- Users ----------

def create_user(username, password):
    """Returns True on success, False if the username is taken."""
    try:
        run_query(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, hash_password(password)),
        )
        return True
    except mysql.connector.IntegrityError:
        return False


def authenticate(username, password):
    """Check a login. Returns (user, None) on success or (None, error message).

    After MAX_ATTEMPTS wrong passwords in a row the account is locked for
    LOCK_MINUTES, so nobody can keep guessing passwords.
    """
    rows = run_query(
        "SELECT id, username, password_hash, failed_attempts, created_at, "
        "TIMESTAMPDIFF(SECOND, NOW(), locked_until) AS locked_for "
        "FROM users WHERE username = %s",
        (username,),
        fetch=True,
    )
    if not rows:
        return None, "Wrong username or password."
    user = rows[0]

    if user["locked_for"] and user["locked_for"] > 0:
        minutes = -(-user["locked_for"] // 60)  # round up
        return None, f"Too many wrong passwords. Account locked — try again in {minutes} min."

    if not check_password(password, user["password_hash"]):
        attempts = user["failed_attempts"] + 1
        if attempts >= MAX_ATTEMPTS:
            run_query(
                "UPDATE users SET failed_attempts = 0, "
                "locked_until = NOW() + INTERVAL %s MINUTE WHERE id = %s",
                (LOCK_MINUTES, user["id"]),
            )
            return None, f"Too many wrong passwords. Account locked for {LOCK_MINUTES} minutes."
        run_query("UPDATE users SET failed_attempts = %s WHERE id = %s", (attempts, user["id"]))
        left = MAX_ATTEMPTS - attempts
        return None, f"Wrong username or password. {left} attempt(s) left before lock."

    run_query("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = %s",
              (user["id"],))
    user.pop("password_hash")  # never keep the hash in the session
    user.pop("locked_for")
    return user, None


def change_password(user_id, current, new):
    """Returns True if the current password was right and the new one is saved."""
    rows = run_query("SELECT password_hash FROM users WHERE id = %s", (user_id,), fetch=True)
    if not rows or not check_password(current, rows[0]["password_hash"]):
        return False
    run_query("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(new), user_id))
    return True


def system_info():
    """MySQL version and row counts for the DB OS home screen."""
    return run_query(
        "SELECT VERSION() AS version, DATABASE() AS db, "
        "(SELECT COUNT(*) FROM users) AS users, (SELECT COUNT(*) FROM students) AS students, "
        "(SELECT COUNT(*) FROM cities) AS cities, (SELECT COUNT(*) FROM weather) AS weather",
        fetch=True,
    )[0]


# ---------- Students (CRUD) ----------

def add_student(name, roll_no, class_name, email, marks, user_id):
    run_query(
        "INSERT INTO students (name, roll_no, class_name, email, marks, added_by) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (name, roll_no, class_name, email, marks, user_id),
    )


def get_students(search=""):
    like = f"%{search}%"
    return run_query(
        "SELECT id, name, roll_no, class_name, email, marks FROM students "
        "WHERE name LIKE %s OR roll_no LIKE %s OR class_name LIKE %s ORDER BY id",
        (like, like, like),
        fetch=True,
    )


def update_student(student_id, name, roll_no, class_name, email, marks):
    run_query(
        "UPDATE students SET name=%s, roll_no=%s, class_name=%s, email=%s, marks=%s WHERE id=%s",
        (name, roll_no, class_name, email, marks, student_id),
    )


def delete_student(student_id):
    run_query("DELETE FROM students WHERE id = %s", (student_id,))


def class_stats():
    return run_query(
        "SELECT class_name, COUNT(*) AS students, ROUND(AVG(marks), 2) AS avg_marks, "
        "MAX(marks) AS top_marks FROM students GROUP BY class_name ORDER BY class_name",
        fetch=True,
    )


# ---------- Cities and weather ----------

def get_cities():
    return run_query("SELECT * FROM cities ORDER BY name", fetch=True)


def add_city(name, country, lat, lon):
    """Returns True on success, False if the city is already there."""
    try:
        run_query(
            "INSERT INTO cities (name, country, latitude, longitude) VALUES (%s, %s, %s, %s)",
            (name, country, lat, lon),
        )
        return True
    except mysql.connector.IntegrityError:
        return False


def delete_city(city_id):
    run_query("DELETE FROM cities WHERE id = %s", (city_id,))


def save_weather(city_id, rows):
    """Insert daily rows; days already stored are updated (upsert)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO weather (city_id, date, temp_max, temp_min, rainfall_mm, wind_kmh) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE temp_max=VALUES(temp_max), temp_min=VALUES(temp_min), "
            "rainfall_mm=VALUES(rainfall_mm), wind_kmh=VALUES(wind_kmh)",
            [(city_id, *r) for r in rows if None not in r],
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def latest_weather():
    """The most recent day stored for every city."""
    return run_query(
        "SELECT c.name AS city, w.date, w.temp_max, w.temp_min, w.rainfall_mm "
        "FROM weather w JOIN cities c ON c.id = w.city_id "
        "WHERE w.date = (SELECT MAX(w2.date) FROM weather w2 WHERE w2.city_id = w.city_id) "
        "ORDER BY c.name",
        fetch=True,
    )


def all_weather():
    """Every stored day for every city, for comparing cities."""
    return run_query(
        "SELECT c.name AS city, w.date, w.temp_max, w.temp_min, w.rainfall_mm, w.wind_kmh "
        "FROM weather w JOIN cities c ON c.id = w.city_id ORDER BY c.name, w.date",
        fetch=True,
    )


def get_weather(city_id):
    return run_query(
        "SELECT date, temp_max, temp_min, rainfall_mm, wind_kmh FROM weather "
        "WHERE city_id = %s ORDER BY date",
        (city_id,),
        fetch=True,
    )


# ---------- SQL playground ----------

# Words that change data or files. Blocked in the playground because some
# MySQL-compatible clouds (e.g. TiDB) don't enforce READ ONLY transactions.
WRITE_WORDS = re.compile(
    r"\b(insert|update|delete|replace|drop|alter|truncate|create|rename|grant|revoke|"
    r"load|lock|unlock|call|handler|set|into)\b",
    re.IGNORECASE,
)


def run_select(sql):
    """Run a read-only query typed by the user. Returns (columns, rows)."""
    sql = sql.strip().rstrip(";").strip()
    if not sql.lower().startswith(("select", "with", "show", "describe")):
        raise ValueError("Only SELECT, WITH, SHOW and DESCRIBE queries are allowed here.")
    if ";" in sql:
        raise ValueError("Run one query at a time (only one ; at the end).")
    word = WRITE_WORDS.search(sql)
    if word:
        raise ValueError(f"“{word.group(0).upper()}” changes data, so it isn't allowed here.")
    if "password_hash" in sql.lower():
        raise ValueError("Password hashes are private, so that column can't be queried.")
    conn = get_connection()
    try:
        try:
            conn.start_transaction(readonly=True)  # on real MySQL this also blocks writes
        except mysql.connector.Error:
            # TiDB rejects READ ONLY by default ("noop function"). The keyword
            # checks above and the rollback below still keep the data safe.
            conn.start_transaction()
        cur = conn.cursor()
        cur.execute(sql)
        columns, rows = list(cur.column_names), cur.fetchall()
        # SELECT * FROM users would still include the hash, so drop that column
        hidden = [i for i, c in enumerate(columns) if c.lower() == "password_hash"]
        for i in reversed(hidden):
            del columns[i]
            rows = [row[:i] + row[i + 1:] for row in rows]
        return columns, rows
    finally:
        conn.rollback()  # make sure nothing is ever saved from this box
        conn.close()
