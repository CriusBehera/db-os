"""Sign in (username, email or Google), create account, account page, password rules."""
import re

import streamlit as st

import db
import firebase
import ui

# Passwords containing any of these are among the first an attacker would try
COMMON_PARTS = (
    "password", "passw0rd", "qwerty", "123456", "654321", "abcdef", "abc123", "admin",
    "welcome", "letmein", "iloveyou", "football", "monkey", "sunshine", "princess", "dragon",
)
USERNAME_RULE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_RULE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


AUTH_PANEL = f"""
<div class='auth-panel'>
  <div>
    <div class='sb-brand' style='padding:0'><div class='sb-logo'>DB</div>
      <div><b>The DB OS</b><small>v2 · Streamlit + MySQL</small></div></div>
    <h1>Your school data,<br><span>one place.</span></h1>
    <p class='lead'>One sign-in, two apps, and an AI that can read and explain your database.</p>
    <div class='feature'><div class='fi'>🎓</div><div><b>Student Board</b>
      <small>Records, grades, class statistics and charts</small></div></div>
    <div class='feature'><div class='fi'>🌦️</div><div><b>Weather Station</b>
      <small>Live weather for cities worldwide, stored in MySQL</small></div></div>
    <div class='feature'><div class='fi'>✨</div><div><b>Nuera Core AI</b>
      <small>Ask questions in plain English, get answers from your data</small></div></div>
  </div>
  <div class='auth-foot'>{ui.CREDITS}</div>
</div>
"""


def google_ready():
    """True when [auth] with a Google client is present in secrets."""
    try:
        return bool(st.secrets["auth"]["client_id"])
    except (KeyError, FileNotFoundError):
        return False


def google_identity():
    """The verified Google profile of this browser, or None if not signed in with Google."""
    try:
        if st.user.is_logged_in and st.user.get("email") and st.user.get("email_verified", True):
            return st.user
    except Exception:  # no [auth] configured
        pass
    return None


def mask(email):
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'*' * max(len(name) - 1, 2)}@{domain}"


def login_body():
    """Password check first, then the email must be verified (link from Firebase)."""
    state = st.session_state
    pending = state.get("pending")  # {"user": ..., "password": ...} after the password was right
    if not pending:
        with st.form("login", border=False):
            who = st.text_input("Username or email", placeholder="you@example.com or username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            if st.form_submit_button("Sign in", type="primary", width="stretch"):
                user, error = db.authenticate(who, password)
                if not user:
                    st.error(error)
                elif not firebase.ready():
                    st.error("Email verification isn't set up yet (add [firebase] to the secrets).")
                else:
                    state.pending = {"user": user, "password": password, "resend": True}
                    st.rerun()
        st.caption(f"🔒 {db.MAX_ATTEMPTS} wrong passwords lock the account for "
                   f"{db.LOCK_MINUTES} minutes. Your email must be verified to sign in.")
        return

    user = pending["user"]
    if not user["login_email"]:
        st.warning("Your account needs a verified email. Add yours and we'll send a link.")
        email = st.text_input("Email", key="pending_email", placeholder="you@example.com").strip()
        if st.button("Send verification link", type="primary", width="stretch",
                     disabled=not EMAIL_RULE.match(email)):
            error = db.add_login_email(user["id"], email)
            if error:
                st.error(error)
            else:
                pending["user"] = db.get_user("id", user["id"])
                st.rerun()
    else:
        status, error = firebase.check(user["login_email"], pending["password"], pending["resend"])
        pending["resend"] = False
        if status == "verified":
            state.pop("pending", None)
            state.user = db.get_user("id", user["id"])
            ui.flash(f"Welcome back, {user['username']}!", "👋")
            st.rerun()
        elif status == "error":
            st.error(firebase.explain(error))
        else:
            st.info(f"📧 Verify your email: we sent a link to **{mask(user['login_email'])}**. "
                    "Click it (check spam too), then press the button below.")
            if st.button("I've verified my email", type="primary", width="stretch"):
                st.rerun()
            if st.button("Resend link", width="stretch"):
                pending["resend"] = True
                st.rerun()
    if st.button("Cancel", key="pending_cancel", width="stretch"):
        state.pop("pending", None)
        st.rerun()


def sign_in_page():
    left, gap, right = st.columns([1.1, 0.12, 1])
    left.markdown(AUTH_PANEL, unsafe_allow_html=True)
    with right:
        st.markdown("<div class='auth-head'><h2>Welcome 👋</h2>"
                    "<p>Sign in with Google, your email or your username.</p></div>",
                    unsafe_allow_html=True)
        with ui.card("auth"):
            if google_ready():
                if st.button("Continue with Google", icon=":material/account_circle:",
                             width="stretch", key="google_btn"):
                    st.login()  # one provider in a flat [auth] section: no name needed
            else:
                st.button("Continue with Google", icon=":material/account_circle:",
                          width="stretch", disabled=True, key="google_btn",
                          help="Add an [auth] section to secrets.toml to turn this on.")
            st.markdown("<div class='or'><span>or</span></div>", unsafe_allow_html=True)

            login_tab, register_tab = st.tabs(["Sign in", "Create account"])

            with login_tab:
                login_body()

            with register_tab:
                username = st.text_input("Username", key="reg_user",
                                         placeholder="3–20 letters, numbers or _").strip()
                if username and not USERNAME_RULE.match(username):
                    st.error("Usernames are 3–20 characters: letters, numbers and _ only.")
                email = st.text_input("Email", key="reg_email", placeholder="you@example.com").strip()
                if email and not EMAIL_RULE.match(email):
                    st.error("That doesn't look like an email address.")
                password = new_password_inputs(username, "reg")
                ready = (bool(password) and bool(USERNAME_RULE.match(username))
                         and bool(EMAIL_RULE.match(email)))
                if st.button("Create account", type="primary", width="stretch",
                             disabled=not ready):
                    error = db.create_user(username, email, password)
                    if error:
                        st.error(error)
                    else:
                        sent = firebase.ready() and not firebase.register(email.lower(), password)
                        st.success("Account created! " + (
                            "We emailed you a verification link. Click it, then switch to **Sign in**."
                            if sent else "Switch to **Sign in**."))


def account_page():
    user = st.session_state.user
    ui.page_header("Account", "Your profile, sign-in methods and password.", "os", "👤")
    left, right = st.columns([1, 1.6])
    with left, ui.card():
        st.subheader("Profile", anchor=False)
        email = user.get("login_email")
        st.markdown(f"<div class='profile'><div class='avatar'>{user['username'][0].upper()}</div>"
                    f"<div><b>{user['username']}</b><small>{email or 'No email yet'}<br>Member since "
                    f"{user['created_at']:%d %B %Y}</small></div></div>", unsafe_allow_html=True)
        methods = [m for m, on in (("Password", user["has_password"]),
                                   ("Google", bool(email) and google_ready())) if on]
        ui.stats([("Sign in with", " + ".join(methods) or "—"), ("Lockout", f"{db.MAX_ATTEMPTS} tries")])

    with right:
        if not email:
            with ui.card("add_email"):
                st.subheader("Add your email", anchor=False)
                st.caption("Lets you sign in with your email, and with Google using the same address.")
                new_email = st.text_input("Email", key="add_email_box", placeholder="you@example.com")
                if st.button("Save email", type="primary",
                             disabled=not EMAIL_RULE.match(new_email.strip())):
                    error = db.add_login_email(user["id"], new_email)
                    if error:
                        st.error(error)
                    else:
                        st.session_state.user = db.get_user("id", user["id"])
                        ui.flash("Email saved", "📧")
                        st.rerun()

        with ui.card("password"):
            has_password = user["has_password"]
            st.subheader("Change password" if has_password else "Set a password", anchor=False)
            if not has_password:
                st.caption("You signed in with Google. Add a password to also sign in with your "
                           "username or email.")
            current = st.text_input("Current password", type="password", key="cur_pw") if has_password else None
            new = new_password_inputs(user["username"], "chg")
            ready = bool(new) and (bool(current) or not has_password)
            if st.button("Update password" if has_password else "Set password", type="primary",
                         disabled=not ready):
                done = (db.change_password(user["id"], current, new) if has_password
                        else db.set_first_password(user["id"], new))
                if done:
                    if has_password and user["login_email"] and firebase.ready():
                        firebase.change_password(user["login_email"], current, new)
                    for k in ("cur_pw", "chg_pw", "chg_confirm"):
                        st.session_state.pop(k, None)
                    st.session_state.user = db.get_user("id", user["id"])
                    ui.flash("Password saved", "🔑")
                    st.rerun()
                else:
                    st.error("Your current password is wrong.")
