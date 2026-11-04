"""Sign in, create account and change password, with strict password rules."""
import re

import streamlit as st

import db
import ui

# Passwords containing any of these are among the first an attacker would try
COMMON_PARTS = (
    "password", "passw0rd", "qwerty", "123456", "654321", "abcdef", "abc123", "admin",
    "welcome", "letmein", "iloveyou", "football", "monkey", "sunshine", "princess", "dragon",
)
USERNAME_RULE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def password_checks(password, username=""):
    """Every rule a password must pass, as (passed, description) pairs."""
    lowered = password.lower()
    return [
        (len(password) >= 8, "At least 8 characters"),
        (bool(re.search(r"[A-Z]", password)), "An uppercase letter (A–Z)"),
        (bool(re.search(r"[a-z]", password)), "A lowercase letter (a–z)"),
        (bool(re.search(r"\d", password)), "A number (0–9)"),
        (bool(re.search(r"[^A-Za-z0-9]", password)), "A symbol (! @ # $ % …)"),
        (" " not in password, "No spaces"),
        (not username or username.lower() not in lowered, "Doesn't contain your username"),
        (not any(part in lowered for part in COMMON_PARTS), "No common words like “password”"),
    ]


def strength(checks):
    """0–100 score and a label, from how many rules pass."""
    passed = sum(ok for ok, _ in checks)
    score = round(100 * passed / len(checks))
    label = "Weak" if score < 60 else "Okay" if score < 100 else "Strong"
    return score, label


def show_checklist(checks):
    score, label = strength(checks)
    st.progress(score, text=f"Password strength: **{label}**")
    left, right = st.columns(2)
    for n, (ok, text) in enumerate(checks):
        (left if n % 2 == 0 else right).markdown(
            f":{'green' if ok else 'gray'}[{'✓' if ok else '○'} {text}]")


def new_password_inputs(username, key):
    """Password + confirm boxes with the live checklist. Returns the password if valid."""
    password = st.text_input("Password", type="password", key=f"{key}_pw",
                             placeholder="Make it strong")
    confirm = st.text_input("Confirm password", type="password", key=f"{key}_confirm")
    checks = password_checks(password, username)
    if password:
        checks.append((password == confirm, "Both passwords match"))
        show_checklist(checks)
    return password if password and all(ok for ok, _ in checks) else None


def sign_in_page():
    _, mid, _ = st.columns([1, 1.35, 1])
    with mid:
        st.markdown(
            "<div class='brand'><div class='logo'>DB</div><h1>The DB OS</h1>"
            "<p>Student Board &nbsp;·&nbsp; Weather Station</p></div>",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            login_tab, register_tab = st.tabs(["Sign in", "Create account"])

            with login_tab:
                with st.form("login", border=False):
                    username = st.text_input("Username", placeholder="your username")
                    password = st.text_input("Password", type="password", placeholder="••••••••")
                    if st.form_submit_button("Sign in", type="primary", width="stretch"):
                        user, error = db.authenticate(username.strip(), password)
                        if user:
                            st.session_state.user = user
                            ui.flash(f"Welcome back, {user['username']}!", "👋")
                            st.rerun()
                        else:
                            st.error(error)
                st.caption(f"🔒 {db.MAX_ATTEMPTS} wrong passwords lock the account for "
                           f"{db.LOCK_MINUTES} minutes.")

            with register_tab:
                username = st.text_input("Username", key="reg_user",
                                         placeholder="3–20 letters, numbers or _").strip()
                if username and not USERNAME_RULE.match(username):
                    st.error("Usernames are 3–20 characters: letters, numbers and _ only.")
                password = new_password_inputs(username, "reg")
                ready = bool(password) and bool(USERNAME_RULE.match(username))
                if st.button("Create account", type="primary", width="stretch",
                             disabled=not ready):
                    if db.create_user(username, password):
                        st.success("Account created! Switch to **Sign in**.")
                    else:
                        st.error("That username is already taken.")
        ui.credits()


def account_page():
    user = st.session_state.user
    ui.page_header("Account", "Your profile and password.")
    left, right = st.columns([1, 1.6])
    with left, st.container(border=True):
        st.subheader("👤 Profile", anchor=False)
        st.markdown(f"**Username:** {user['username']}")
        st.markdown(f"**Member since:** {user['created_at']:%d %B %Y}")
    with right, st.container(border=True):
        st.subheader("🔑 Change password", anchor=False)
        current = st.text_input("Current password", type="password", key="cur_pw")
        new = new_password_inputs(user["username"], "chg")
        if st.button("Update password", type="primary", disabled=not (current and new)):
            if db.change_password(user["id"], current, new):
                for k in ("cur_pw", "chg_pw", "chg_confirm"):
                    st.session_state.pop(k, None)
                ui.flash("Password updated", "🔑")
                st.rerun()
            else:
                st.error("Your current password is wrong.")
