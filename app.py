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
    st.rerun()


# ---------- DB OS home screen ----------

def app_tile(col, icon, app, title, text, stats, page):
    with col, st.container(border=True):
        st.markdown(f"<div class='tile-icon' style='background:{ui.GRADIENTS[app]}'>{icon}</div>",
                    unsafe_allow_html=True)
        st.subheader(title, anchor=False)
        st.markdown(f"<p class='muted'>{text}</p>", unsafe_allow_html=True)
        for c, (label, value) in zip(st.columns(len(stats)), stats):
            c.metric(label, value)
        if st.button(f"Open {title}", type="primary", icon=":material/arrow_forward:",
                     width="stretch", key=f"open_{app}"):
            st.switch_page(page)


def os_home():
    user = st.session_state.user
    now = datetime.now()
    part = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    ui.hero(f"Good {part}, {user['username']}",
            f"{now:%A, %d %B %Y} · Choose an app to open.", "os", tag="The DB OS")

    info = db.system_info()
    left, right = st.columns(2)
    app_tile(left, "🎓", "students", "Student Board",
             "Manage student records, marks and grades, with class statistics and charts.",
             [("Students", info["students"]), ("Classes", len(db.class_stats()))],
             PAGES["board"])
    app_tile(right, "🌦️", "weather", "Weather Station",
             "Real daily weather for cities around the world, fetched live and stored in MySQL.",
             [("Cities", info["cities"]), ("Days of data", f"{info['weather']:,}")],
             PAGES["weather"])

    with st.container(border=True):
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        c1.markdown(f"<div style='display:flex;gap:1rem;align-items:center'>"
                    f"<div class='tile-icon' style='background:{ui.GRADIENTS['ai']};margin:0'>✨</div>"
                    "<div><b style='font-size:1.15rem'>Nuera Core AI</b><br>"
                    "<span class='muted'>Ask questions in plain English. It writes the SQL, "
                    "reads both apps' data and explains the answer.</span></div></div>",
                    unsafe_allow_html=True)
        if c2.button("Ask Nuera AI", type="primary", icon=":material/auto_awesome:",
                     width="stretch"):
            st.switch_page(PAGES["ai"])

    with st.container(border=True):
        st.subheader("🖥️ System", anchor=False)
        total = sum(info[k] for k in ("users", "students", "cities", "weather"))
        items = [("Status", "🟢 Online"), ("MySQL", info["version"].split("-")[0]),
                 ("Database", info["db"]), ("Users", info["users"]), ("Total rows", f"{total:,}")]
        for c, (label, value) in zip(st.columns(len(items)), items):
            c.caption(label)
            c.markdown(f"**{value}**")
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
    "board": ("🎓 Student Board", [p[3] for p in student_board.PAGES], "weather", "🌦️ Weather Station"),
    "weather": ("🌦️ Weather Station", [p[3] for p in weather_station.PAGES], "board", "🎓 Student Board"),
}


def sidebar(current_path):
    app = current_path.split("-")[0] if current_path.split("-")[0] in APPS else None
    with st.sidebar:
        st.markdown("<div class='side-brand'>💠 The DB <span>OS</span></div>",
                    unsafe_allow_html=True)
        st.page_link(PAGES[""], label="Home")
        st.page_link(PAGES["ai"], label="Ask Nuera AI")
        if app:
            name, paths, other, other_name = APPS[app]
            st.caption(name)
            for path in paths:
                st.page_link(PAGES[path])
            st.divider()
            st.page_link(PAGES[other], label=f"Switch to {other_name}", icon=":material/swap_horiz:")
        st.page_link(PAGES["account"])
        st.space("small")
        with st.container(border=True):
            st.markdown(f"**{st.session_state.user['username']}**")
            st.caption(f"Signed in · auto sign-out after {SESSION_MINUTES} min idle")
            if st.button("Sign out", icon=":material/logout:", width="stretch"):
                sign_out()
        st.markdown(f"<div class='credits' style='margin-top:1rem'>{ui.CREDITS}</div>",
                    unsafe_allow_html=True)


def main():
    user = st.session_state.user
    if user and time.time() - st.session_state.get("last_active", time.time()) > SESSION_MINUTES * 60:
        sign_out(f"Signed out after {SESSION_MINUTES} minutes of inactivity.")
    st.session_state.last_active = time.time()

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
