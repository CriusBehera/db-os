"""Student Board — student records, marks and class statistics."""
import altair as alt
import mysql.connector
import streamlit as st

import db
import ui
from sql_examples import EXAMPLES

GRADES = ["A+", "A", "B", "C", "Fail"]
GRADE_COLORS = ["#6366F1", "#8B5CF6", "#14B8A6", "#F59E0B", "#EF4444"]

STUDENT_COLUMNS = {
    "id": None,  # hidden
    "name": st.column_config.TextColumn("Name"),
    "roll_no": st.column_config.TextColumn("Roll no"),
    "class_name": st.column_config.TextColumn("Class"),
    "email": st.column_config.TextColumn("Email"),
    "marks": st.column_config.ProgressColumn("Marks", min_value=0, max_value=100, format="%.0f"),
    "grade": st.column_config.TextColumn("Grade"),
}


def grade(marks):
    for cutoff, letter in [(90, "A+"), (80, "A"), (70, "B"), (50, "C")]:
        if marks >= cutoff:
            return letter
    return "Fail"


def students_df():
    df = ui.to_df(db.get_students())
    if not df.empty:
        df["grade"] = df["marks"].map(grade)
    return df


def class_avg_chart(df):
    avg = df.groupby("class_name", as_index=False)["marks"].mean()
    bars = alt.Chart(avg).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=48).encode(
        x=alt.X("class_name:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("marks:Q", title="Average marks", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("class_name:N", legend=None),
        tooltip=[alt.Tooltip("class_name", title="Class"),
                 alt.Tooltip("marks", title="Average", format=".1f")],
    )
    labels = bars.mark_text(dy=-10, fontWeight=600).encode(text=alt.Text("marks:Q", format=".1f"))
    return (bars + labels).properties(height=300)


# ---------- Pages ----------

def home():
    ui.hero("Student Board", "Records, marks and class performance at a glance.",
            "students", tag="App 1")
    df = students_df()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Students", len(df), border=True)
    m2.metric("Average marks", f"{df['marks'].mean():.1f}" if len(df) else "—", border=True)
    if len(df):
        top = df.loc[df["marks"].idxmax()]
        m3.metric("Top scorer", top["name"], f"{top['marks']:.0f} marks", delta_color="off",
                  delta_arrow="off", border=True)
        m4.metric("Pass rate", f"{(df['marks'] >= 50).mean():.0%}", border=True)
    else:
        m3.metric("Top scorer", "—", border=True)
        m4.metric("Pass rate", "—", border=True)

    if df.empty:
        st.info("No students yet. Add one from **Add student**.")
        return
    left, right = st.columns([1.1, 1])
    with left, st.container(border=True):
        st.subheader("🏆 Top 5 students", anchor=False)
        st.dataframe(df.nlargest(5, "marks")[["name", "class_name", "marks", "grade"]],
                     column_config=STUDENT_COLUMNS, hide_index=True, width="stretch")
    with right, st.container(border=True):
        st.subheader("📊 Average by class", anchor=False)
        st.altair_chart(class_avg_chart(df).properties(height=200), width="stretch")


def student_form(key, student=None):
    """Shared form for add and edit. Returns the values, or None if not submitted."""
    s = student or {}
    with st.form(key, clear_on_submit=student is None, border=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name", s.get("name", ""), placeholder="Full name")
        roll_no = c2.text_input("Roll no", s.get("roll_no", ""), placeholder="e.g. 105")
        class_name = c1.text_input("Class", s.get("class_name", ""), placeholder="e.g. 10A")
        email = c2.text_input("Email", s.get("email") or "", placeholder="optional")
        marks = st.slider("Marks", 0.0, 100.0, float(s.get("marks", 0)), step=0.5)
        label = "Add student" if student is None else "Save changes"
        if st.form_submit_button(label, type="primary", icon=":material/save:"):
            if not name.strip() or not roll_no.strip() or not class_name.strip():
                st.error("Name, roll no and class are required.")
                return None
            return name.strip(), roll_no.strip(), class_name.strip(), email.strip(), marks
    return None


def all_students():
    ui.page_header("All students", "Search, filter and export every student record.")
    df = students_df()
    if df.empty:
        st.info("No students yet. Add one from **Add student**.")
        return

    with st.container(border=True):
        c1, c2 = st.columns([1, 1.4])
        search = c1.text_input("Search", placeholder="🔍  Name, roll no or email",
                               label_visibility="collapsed")
        classes = c2.pills("Class", sorted(df["class_name"].unique()), selection_mode="multi",
                           label_visibility="collapsed")
        if search:
            text = df[["name", "roll_no", "email"]].fillna("").agg(" ".join, axis=1)
            df = df[text.str.contains(search, case=False, regex=False)]
        if classes:
            df = df[df["class_name"].isin(classes)]

        st.dataframe(df, column_config=STUDENT_COLUMNS, hide_index=True, width="stretch",
                     height=min(38 * len(df) + 40, 560))
        c1, c2 = st.columns([3, 1])
        c1.caption(f"Showing {len(df)} student(s)")
        c2.download_button("Download CSV", df.drop(columns="id").to_csv(index=False),
                           "students.csv", "text/csv", icon=":material/download:",
                           width="stretch")


def add_student():
    ui.page_header("Add student", "Create a new student record.")
    with st.container(border=True):
        values = student_form("add")
    if values:
        try:
            db.add_student(*values, st.session_state.user["id"])
            st.toast(f"Added {values[0]}", icon="✅")
        except mysql.connector.IntegrityError:
            st.error("A student with that roll no already exists.")


@st.dialog("Delete student?")
def confirm_delete(student):
    st.write(f"This permanently removes **{student['name']}** (roll no {student['roll_no']}).")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", width="stretch"):
        st.rerun()
    if c2.button("Delete", type="primary", icon=":material/delete:", width="stretch"):
        db.delete_student(student["id"])
        ui.flash(f"Deleted {student['name']}", "🗑️")
        st.rerun()


def edit_student():
    ui.page_header("Edit student", "Update marks and details, or remove a record.")
    students = db.get_students()
    if not students:
        st.info("No students yet.")
        return
    labels = {f"{s['roll_no']} — {s['name']} ({s['class_name']})": s for s in students}
    student = labels[st.selectbox("Student", labels)]

    with st.container(border=True):
        values = student_form(f"edit_{student['id']}", student)
    if values:
        try:
            db.update_student(student["id"], *values)
            ui.flash(f"Saved changes to {values[0]}")
            st.rerun()
        except mysql.connector.IntegrityError:
            st.error("Another student already has that roll no.")

    if st.button("Delete this student", icon=":material/delete:"):
        confirm_delete(student)


def statistics():
    ui.page_header("Statistics", "How each class is doing, calculated live with SQL.")
    stats = db.class_stats()
    if not stats:
        st.info("Add some students first.")
        return
    stats_df = ui.to_df(stats)
    df = students_df()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Students", len(df), border=True)
    m2.metric("Classes", len(stats_df), border=True)
    m3.metric("School average", f"{df['marks'].mean():.1f}", border=True)
    m4.metric("Pass rate", f"{(df['marks'] >= 50).mean():.0%}", border=True)

    left, right = st.columns([1.4, 1])
    with left, st.container(border=True):
        st.subheader("Average by class", anchor=False)
        st.altair_chart(class_avg_chart(df), width="stretch")
    with right, st.container(border=True):
        st.subheader("Grades", anchor=False)
        counts = df["grade"].value_counts().reindex(GRADES, fill_value=0).reset_index()
        donut = alt.Chart(counts).mark_arc(innerRadius=70, cornerRadius=6, padAngle=0.02).encode(
            theta="count:Q",
            color=alt.Color("grade:N", sort=GRADES, title="Grade",
                            scale=alt.Scale(domain=GRADES, range=GRADE_COLORS)),
            tooltip=["grade", "count"],
        ).properties(height=300)
        st.altair_chart(donut, width="stretch")

    with st.container(border=True):
        st.subheader("Marks distribution", anchor=False)
        hist = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("marks:Q", bin=alt.Bin(step=10, extent=[0, 100]), title="Marks"),
            y=alt.Y("count():Q", title="Students"),
            tooltip=[alt.Tooltip("count():Q", title="Students")],
        ).properties(height=220)
        st.altair_chart(hist, width="stretch")

    with st.container(border=True):
        st.subheader("Class summary", anchor=False)
        st.dataframe(
            stats_df,
            column_config={
                "class_name": "Class",
                "students": "Students",
                "avg_marks": st.column_config.ProgressColumn("Average", min_value=0,
                                                             max_value=100, format="%.1f"),
                "top_marks": st.column_config.NumberColumn("Top", format="%.0f"),
            },
            hide_index=True, width="stretch",
        )


def sql():
    ui.page_header("Student SQL", "Practise SQL on the students and users tables.")
    ui.sql_playground(
        [e for e in EXAMPLES if e["app"] == "students"],
        "**students** — id, name, roll_no, class_name, email, marks, added_by, created_at\n\n"
        "**users** — id, username, created_at",
    )


PAGES = [
    (home, "Overview", ":material/space_dashboard:", "board"),
    (all_students, "All students", ":material/groups:", "board-students"),
    (add_student, "Add student", ":material/person_add:", "board-add"),
    (edit_student, "Edit student", ":material/edit:", "board-edit"),
    (statistics, "Statistics", ":material/bar_chart:", "board-stats"),
    (sql, "SQL playground", ":material/terminal:", "board-sql"),
]
