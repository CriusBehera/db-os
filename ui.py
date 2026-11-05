"""Shared look and helpers used by every app in The DB OS."""
from decimal import Decimal

import mysql.connector
import pandas as pd
import streamlit as st

import db

CREDITS = "Made by <b>Crius Behera</b> · Sponsored by <b>Nuera Core AI</b>, <b>Crius Software Solutions</b>"

# Gradient for each app's banner
GRADIENTS = {
    "os": "linear-gradient(135deg, #0F172A 0%, #312E81 55%, #6366F1 100%)",
    "students": "linear-gradient(135deg, #6366F1 0%, #8B5CF6 55%, #EC4899 100%)",
    "weather": "linear-gradient(135deg, #0EA5E9 0%, #14B8A6 60%, #22C55E 100%)",
    "ai": "linear-gradient(135deg, #7C3AED 0%, #C026D3 50%, #F97316 100%)",
}

CSS = """
<style>
.block-container { padding-top: 2.2rem; max-width: 1250px; }
.hero {
    padding: 1.8rem 2rem; border-radius: 20px; margin-bottom: 1.2rem; color: #fff;
    box-shadow: 0 12px 32px -14px rgba(15, 23, 42, .55);
}
.hero h1 { color: #fff; margin: 0; padding: 0; font-size: 2.1rem; }
.hero p  { margin: .35rem 0 0; opacity: .9; font-size: 1.05rem; }
.hero .tag {
    display: inline-block; font-size: .75rem; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; padding: .2rem .6rem; border-radius: 999px;
    background: rgba(255,255,255,.18); margin-bottom: .6rem;
}
.brand { text-align: center; margin: 2.2rem 0 1.4rem; }
.brand .logo {
    width: 68px; height: 68px; border-radius: 20px; margin: 0 auto .8rem;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.7rem; font-weight: 800; color: #fff;
    background: linear-gradient(135deg, #312E81, #6366F1 60%, #14B8A6);
    box-shadow: 0 10px 28px -10px rgba(99, 102, 241, .7);
}
.brand h1 { margin: 0; padding: 0; font-size: 2.1rem; }
.brand p  { margin: .3rem 0 0; opacity: .65; }
.tile-icon {
    width: 56px; height: 56px; border-radius: 16px; display: flex; align-items: center;
    justify-content: center; font-size: 1.8rem; margin-bottom: .6rem;
}
.muted { opacity: .65; font-size: .92rem; }
.credits { text-align: center; opacity: .6; font-size: .82rem; margin: 2rem 0 .5rem; }
.side-brand { font-weight: 800; font-size: 1.15rem; margin: 0 0 .2rem; }
.side-brand span { color: #6366F1; }
</style>
"""


def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle, app="os", tag=None):
    tag_html = f"<div class='tag'>{tag}</div>" if tag else ""
    st.markdown(
        f"<div class='hero' style='background:{GRADIENTS[app]}'>{tag_html}"
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def page_header(title, subtitle):
    st.title(title, anchor=False)
    st.markdown(f"<p class='muted'>{subtitle}</p>", unsafe_allow_html=True)


def credits():
    st.markdown(f"<div class='credits'>{CREDITS}</div>", unsafe_allow_html=True)


def to_df(rows, columns=None):
    """DataFrame with MySQL DECIMAL values turned into normal numbers for charts."""
    df = pd.DataFrame(rows, columns=columns)
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


def flash(message, icon="✅"):
    """Show a toast after the next rerun (toasts are lost when st.rerun() runs)."""
    st.session_state.flash = (message, icon)


def show_flash():
    if "flash" in st.session_state:
        message, icon = st.session_state.pop("flash")
        st.toast(message, icon=icon)


def sql_playground(examples, tables_help):
    """Pick an example query, edit it, and see the result (read-only)."""
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    i = c1.selectbox("Example", range(len(examples)),
                     format_func=lambda i: f"{i + 1}. {examples[i]['title']}")
    with c2.popover("Tables", icon=":material/table_chart:", width="stretch"):
        st.markdown(tables_help)
    example = examples[i]

    with st.container(border=True):
        st.info(example["explain"], icon=":material/lightbulb:")
        sql = st.text_area("SQL — edit it, then press ⌘/Ctrl + Enter to run", example["sql"],
                           height=210, key=f"sql_{example['app']}_{i}")
    try:
        columns, rows = db.run_select(sql)
        with st.container(border=True):
            st.caption(f"✅ {len(rows)} row(s)")
            st.dataframe(to_df(rows, columns), width="stretch", hide_index=True)
    except ValueError as e:
        st.warning(str(e))
    except mysql.connector.Error as e:
        st.error(f"SQL error: {e.msg}")
