"""The DB OS — Student Board + Weather Station on Streamlit and MySQL.

Run with:  streamlit run app.py
"""
import time
from datetime import datetime

import mysql.connector
import streamlit as st

import ai
import auth
import db
import student_board
import ui
import weather_station

st.set_page_config(page_title="The DB OS", page_icon="💠", layout="wide")
ui.apply_style()

SESSION_MINUTES = 30  # sign out automatically after this long with no clicks

if "user" not in st.session_state:
    st.session_state.user = None


def sign_out(message=None):
    st.session_state.user = None
    if message:
        ui.flash(message, "🔒")
    if auth.google_identity():
        st.logout()  # also clears the Google cookie, or Google would sign you straight back in
    st.rerun()


def google_sign_in():
    """Turn a verified Google sign-in into a DB OS session (find or create the account)."""
    profile = auth.google_identity()
    if profile and not st.session_state.user:
        st.session_state.user = db.google_user(profile["email"], profile.get("name", ""))
        ui.flash(f"Signed in with Google as {st.session_state.user['username']}", "👋")


# ---------- DB OS home screen ----------

def app_tile(col, icon, app, title, text, stats, page):
    with col, ui.card(f"tile_{app}"):
        st.markdown(f"<div class='tile'><div class='tile-icon' style='background:{ui.GRADIENTS[app]}'>"
                    f"{icon}</div><h3>{title}</h3><p>{text}</p></div>", unsafe_allow_html=True)
        ui.stats(stats)
        st.space("small")
        if st.button(f"Open {title}", type="primary", icon=":material/arrow_forward:",
                     width="stretch", key=f"open_{app}"):
            st.switch_page(page)


def os_home():
    user = st.session_state.user
    now = datetime.now()
    part = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    ui.hero(f"Good {part}, {user['username']} 👋",
            f"{now:%A, %d %B %Y}. Pick an app to open, or ask Nuera AI about your data.",
            "os", tag="The DB OS")

    info = db.system_info()
    st.markdown("<div class='section'>Apps</div>", unsafe_allow_html=True)
    left, mid, right = st.columns(3)
    app_tile(left, "🎓", "students", "Student Board",
             "Student records, marks and grades, with class statistics and charts.",
             [("Students", info["students"]), ("Classes", len(db.class_stats()))],
             PAGES["board"])
    app_tile(mid, "🌦️", "weather", "Weather Station",
             "Real daily weather for cities worldwide, fetched live and stored in MySQL.",
             [("Cities", info["cities"]), ("Days of data", f"{info['weather']:,}")],
             PAGES["weather"])
    app_tile(right, "✨", "ai", "Nuera AI",
             "Ask questions in plain English. It writes the SQL and explains the answer.",
             [("Model", "Nuera"), ("Mode", "Safe")],
             PAGES["ai"])

    st.markdown("<div class='section' style='margin-top:1.2rem'>System</div>", unsafe_allow_html=True)
    with ui.card("system"):
        total = sum(info[k] for k in ("users", "students", "cities", "weather"))
        ui.stats([("Status", "🟢 Online"), ("MySQL", info["version"].split("-")[0]),
                  ("Database", info["db"]), ("Users", info["users"]), ("Total rows", f"{total:,}")])
    ui.credits()


# ---------- Pages and sidebar ----------

def build_pages():
    pages = {
        "": st.Page(os_home, title="Home", icon=":material/home:", default=True),
        "account": st.Page(auth.account_page, title="Account", icon=":material/person:",
                           url_path="account"),
        "ai": st.Page(ai.assistant_page, title="Nuera AI", icon=":material/auto_awesome:",
                      url_path="ai"),
    }
    for module in (student_board, weather_station):
        for func, title, icon, path in module.PAGES:
            pages[path] = st.Page(func, title=title, icon=icon, url_path=path)
    return pages


PAGES = build_pages()
APPS = {
    "board": ("Student Board", [p[3] for p in student_board.PAGES], "weather", "Weather Station"),
    "weather": ("Weather Station", [p[3] for p in weather_station.PAGES], "board", "Student Board"),
}


def nav_link(path, current, label=None, icon=None):
    """Sidebar link; the page you are on gets the highlighted nav_active style."""
    box = st.container(key=f"nav_active_{path or 'home'}") if path == current else st.container()
    with box:
        st.page_link(PAGES[path], label=label, icon=icon)


def sidebar(current_path):
    app = current_path.split("-")[0] if current_path.split("-")[0] in APPS else None
    user = st.session_state.user
    with st.sidebar:
        st.markdown("<div class='sb-brand'><div class='sb-logo'>DB</div>"
                    "<div><b>The DB OS</b><small>Student Board · Weather Station</small></div></div>",
                    unsafe_allow_html=True)
        nav_link("", current_path, "Home")
        nav_link("ai", current_path, "Nuera AI")
        if app:
            name, paths, other, other_name = APPS[app]
            st.markdown(f"<div class='sb-label'>{name}</div>", unsafe_allow_html=True)
            for path in paths:
                nav_link(path, current_path)
            st.markdown("<div class='sb-label'>Switch</div>", unsafe_allow_html=True)
            nav_link(other, current_path, other_name, ":material/swap_horiz:")
        st.markdown("<div class='sb-label'>You</div>", unsafe_allow_html=True)
        nav_link("account", current_path)
        with st.container(key="sb_user"):
            st.markdown(f"<div class='sb-user'><div class='avatar'>{user['username'][0].upper()}</div>"
                        f"<div><b>{user['username']}</b><small>Auto sign-out after "
                        f"{SESSION_MINUTES} min idle</small></div></div>", unsafe_allow_html=True)
            st.space("small")
            if st.button("Sign out", icon=":material/logout:", width="stretch"):
                sign_out()
        st.markdown(f"<div class='sb-credits'>{ui.CREDITS}</div>", unsafe_allow_html=True)


def main():
    user = st.session_state.user
    if user and time.time() - st.session_state.get("last_active", time.time()) > SESSION_MINUTES * 60:
        sign_out(f"Signed out after {SESSION_MINUTES} minutes of inactivity.")
    st.session_state.last_active = time.time()
    google_sign_in()
    user = st.session_state.user

    # Every page is registered (hidden) so links like /weather-city work; the
    # sidebar shows only the pages of the app you are in.
    current = st.navigation(list(PAGES.values()), position="hidden")
    ui.show_flash()
    if not user:
        auth.sign_in_page()
        return
    sidebar(current.url_path)
    current.run()


try:
    main()
except mysql.connector.Error as e:
    st.error(f"Database error: {e}")
    st.info("Check that MySQL is running and .streamlit/secrets.toml is correct.")
