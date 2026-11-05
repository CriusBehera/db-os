"""Nuera Core AI assistant: answers questions about the database by writing SQL.

How one question is answered:
  1. Nuera reads the table layout + your question and replies with up to 3
     read-only SQL queries (or a direct answer if no data is needed).
  2. The queries run through db.run_select (same safety checks as the SQL
     playground). If one fails, Nuera gets the error once to fix it.
  3. Nuera reads the results and writes the answer.
"""
import json
import re
from datetime import date

import mysql.connector
import pandas as pd
import requests
import streamlit as st

import db
import ui

MAX_QUERIES = 3
MAX_ROWS_SENT = 50  # rows per query sent to the AI (it sees a sample, you see everything)

SCHEMA = """
students(id, name, roll_no, class_name, email, marks DECIMAL 0-100, added_by -> users.id, created_at)
users(id, username, created_at)            -- never select password_hash
cities(id, name, country, latitude, longitude)
weather(id, city_id -> cities.id, date, temp_max °C, temp_min °C, rainfall_mm, wind_kmh)
                                            -- one row per city per day, about the last 30 days
Grades used in the app: A+ >= 90, A >= 80, B >= 70, C >= 50, otherwise Fail.
""".strip()

PLAN_PROMPT = """You are Nuera Core AI, the assistant inside "The DB OS" (a school project by
Crius Behera). You answer questions about a MySQL 8 database by writing SQL.

Tables:
{schema}

Today is {today}.

Reply with ONLY a JSON object, no code fences, in one of these two shapes:
  {{"queries": ["SELECT ...", "SELECT ..."]}}   -> when the question needs data (1 to {max_q} queries)
  {{"answer": "..."}}                          -> greetings, SQL explanations, or questions about you

Rules for queries:
- MySQL syntax, read-only: SELECT or WITH only, one statement each, no semicolons.
- Never use INSERT, UPDATE, DELETE, SET, INTO, or the password_hash column.
- Add ORDER BY and LIMIT 50 (or less) to queries that return many rows.
- Round averages with ROUND(x, 1). Join cities to show city names, not ids.
- For "analyse" or "summary" questions, use up to {max_q} queries that cover different angles.
{extra}
Conversation so far:
{history}

User: {question}"""

ANSWER_PROMPT = """You are Nuera Core AI inside "The DB OS". Answer the user's question using ONLY
the query results below. Write in friendly, clear Markdown:
- Start with the direct answer in one or two sentences (bold the key numbers or names).
- Then add 2 to 4 short bullet-point insights if they are useful.
- If a result is empty, say no matching data was found.
- Don't show the SQL or talk about JSON. Keep it under 200 words unless asked for detail.

Conversation so far:
{history}

User: {question}

Query results:
{results}"""


class AIError(Exception):
    pass


def ask_nuera(prompt):
    """Send one prompt to Nuera Core AI. Returns (text, tokens used)."""
    cfg = st.secrets["nuera"]
    try:
        r = requests.post(
            cfg["url"],
            json={"email": cfg["email"], "platform": cfg.get("platform", "w"), "prompt": prompt},
            timeout=120,
        )
        data = r.json()
    except requests.RequestException:
        raise AIError("Couldn't reach Nuera Core AI. Check your internet connection.")
    except ValueError:
        raise AIError(f"Nuera Core AI sent an unexpected reply (HTTP {r.status_code}).")
    if r.status_code != 200:
        raise AIError(f"Nuera Core AI: {data.get('error', f'HTTP {r.status_code}')}")
    return data.get("text", ""), data.get("usage", {}).get("total_token_count", 0)


def parse_json(text):
    """Pull the first {...} object out of the AI's reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def history_text(messages, limit=6):
    lines = []
    for m in messages[-limit:]:
        who = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{who}: {m['content'][:500]}")
    return "\n".join(lines) or "(none)"


def run_queries(queries):
    results = []
    for sql in queries[:MAX_QUERIES]:
        try:
            columns, rows = db.run_select(sql)
            results.append({"sql": sql, "df": ui.to_df(rows, columns), "error": None})
        except (ValueError, mysql.connector.Error) as e:
            results.append({"sql": sql, "df": None, "error": getattr(e, "msg", str(e))})
    return results


def answer(question, messages):
    """Answer one question. Returns {"answer", "results", "tokens"}."""
    history = history_text(messages)
    plan_args = dict(schema=SCHEMA, today=date.today().isoformat(), max_q=MAX_QUERIES,
                     history=history, question=question)

    text, tokens = ask_nuera(PLAN_PROMPT.format(extra="", **plan_args))
    plan = parse_json(text)
    if not plan or not plan.get("queries"):
        reply = plan.get("answer") if plan else None
        return {"answer": reply or text, "results": [], "tokens": tokens}

    results = run_queries(plan["queries"])
    failed = [r for r in results if r["error"]]
    if failed:  # give the AI one chance to fix its SQL
        errors = "\n".join(f"- {r['sql']}\n  error: {r['error']}" for r in failed)
        extra = f"\nYour previous queries failed. Fix them:\n{errors}\n"
        text, more = ask_nuera(PLAN_PROMPT.format(extra=extra, **plan_args))
        tokens += more
        fixed = parse_json(text)
        if fixed and fixed.get("queries"):
            results = [r for r in results if not r["error"]] + run_queries(fixed["queries"])

    parts = []
    for n, r in enumerate(results, 1):
        if r["error"]:
            parts.append(f"Query {n} failed: {r['error']}")
        else:
            csv = r["df"].head(MAX_ROWS_SENT).to_csv(index=False)
            parts.append(f"Query {n} ({len(r['df'])} rows): {r['sql']}\n{csv}")
    text, more = ask_nuera(ANSWER_PROMPT.format(history=history, question=question,
                                                results="\n\n".join(parts)))
    return {"answer": text, "results": results, "tokens": tokens + more}


# ---------- Chat page ----------

SUGGESTIONS = [
    "🏆 Who are the top 5 students?",
    "📊 Analyse the student marks",
    "🌧️ Which city had the most rain?",
    "🌡️ Compare Delhi and London temperatures",
    "⚠️ Which students are at risk of failing?",
    "🔥 What was the hottest day in each city?",
]


def show_results(results):
    for n, r in enumerate(results, 1):
        label = f"🔍 Query {n}" + (" (failed)" if r["error"] else f" · {len(r['df'])} rows")
        with st.expander(label):
            st.code(r["sql"], language="sql")
            if r["error"]:
                st.error(r["error"])
                continue
            df = r["df"]
            st.dataframe(df, hide_index=True, width="stretch")
            numeric = df.select_dtypes("number").columns
            if len(df.columns) == 2 and len(numeric) == 1 and 1 < len(df) <= 30:
                st.bar_chart(df, x=df.columns[0], y=numeric[0], height=240)


def assistant_page():
    ui.hero("Nuera Core AI", "Ask questions about your students and weather. "
            "It writes the SQL, runs it on your database and explains the answer.",
            "ai", tag="AI assistant")
    if "nuera" not in st.secrets:
        st.warning("Add a `[nuera]` section to `.streamlit/secrets.toml` to turn on the assistant.")
        return

    messages = st.session_state.setdefault("ai_messages", [])
    question = st.chat_input("Ask about students, marks, cities or weather…")

    if not messages and not question:
        st.markdown("**Try asking:**")
        cols = st.columns(2)
        for n, text in enumerate(SUGGESTIONS):
            if cols[n % 2].button(text, width="stretch", key=f"suggest_{n}"):
                question = text.split(" ", 1)[1]

    for m in messages:
        with st.chat_message(m["role"], avatar="🧑‍🎓" if m["role"] == "user" else "✨"):
            st.markdown(m["content"])
            show_results(m.get("results", []))

    if question:
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="✨"):
            try:
                with st.status("Nuera is thinking…", expanded=False) as status:
                    status.update(label="Writing SQL and reading your database…")
                    reply = answer(question, messages)
                    status.update(label=f"Done · {reply['tokens']:,} tokens", state="complete")
            except AIError as e:
                st.error(str(e))
                return
            st.markdown(reply["answer"])
            show_results(reply["results"])
        messages += [{"role": "user", "content": question},
                     {"role": "assistant", "content": reply["answer"], "results": reply["results"]}]

    if messages:
        c1, c2 = st.columns([4, 1])
        c1.caption("Nuera only reads data: every query runs read-only, and password hashes are hidden.")
        if c2.button("Clear chat", icon=":material/delete_sweep:", width="stretch"):
            messages.clear()
            st.rerun()
    st.markdown("<div class='credits'>Powered by <b>Nuera Core AI</b> · ai.criusbehera.com</div>",
                unsafe_allow_html=True)
