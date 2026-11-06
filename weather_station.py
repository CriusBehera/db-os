"""Weather Station — real daily weather from Open-Meteo, stored in MySQL."""
import altair as alt
import pandas as pd
import streamlit as st

import db
import ui
import weather
from sql_examples import EXAMPLES

OFFLINE = "Couldn't reach the weather service. Check your internet."


def weather_icon(row):
    if row["rainfall_mm"] >= 10:
        return "🌧️"
    if row["rainfall_mm"] > 0:
        return "🌦️"
    return "☀️" if row["temp_max"] >= 30 else "⛅"


# ---------- Pages ----------

def home():
    ui.hero("Weather Station", "Live readings from every city you track, saved in MySQL.",
            "weather", tag="App 2")
    cities = db.get_cities()
    df = ui.to_df(db.all_weather())
    if df.empty:
        st.info("No weather saved yet. Open **City weather** and add a city.")
        return
    df["date"] = pd.to_datetime(df["date"])
    latest = ui.to_df(db.latest_weather())
    totals = df.groupby("city")["rainfall_mm"].sum()
    hottest = latest.loc[latest["temp_max"].idxmax()]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📍 Cities", len(cities))
    m2.metric("📅 Days stored", f"{len(df):,}")
    m3.metric("🔥 Hottest today", hottest["city"], f"{hottest['temp_max']:.1f} °C",
              delta_color="off", delta_arrow="off")
    m4.metric("💧 Wettest (30 days)", totals.idxmax(), f"{totals.max():.0f} mm",
              delta_color="off", delta_arrow="off")

    left, right = st.columns([1, 1.25])
    with left, ui.card():
        top = st.columns([1.2, 1], vertical_alignment="center")
        top[0].subheader("🌍 Today", anchor=False)
        if top[1].button("Refresh all", icon=":material/refresh:", width="stretch"):
            refresh_all(cities)
        latest.insert(0, " ", latest.apply(weather_icon, axis=1))
        st.dataframe(
            latest[[" ", "city", "temp_max", "temp_min", "rainfall_mm"]],
            column_config={
                " ": st.column_config.TextColumn(" ", width=36),
                "city": "City",
                "temp_max": st.column_config.NumberColumn("High", format="%.1f °C"),
                "temp_min": st.column_config.NumberColumn("Low", format="%.1f °C"),
                "rainfall_mm": st.column_config.NumberColumn("Rain", format="%.1f mm"),
            },
            hide_index=True, width="stretch",
        )
    with right, ui.card():
        st.subheader("🌡️ Average high by city", anchor=False)
        avg = df.groupby("city", as_index=False)["temp_max"].mean()
        bars = alt.Chart(avg).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
            y=alt.Y("city:N", sort="-x", title=None),
            x=alt.X("temp_max:Q", title="°C"),
            color=alt.Color("temp_max:Q", scale=alt.Scale(scheme="orangered"), legend=None),
            tooltip=["city", alt.Tooltip("temp_max", title="Avg high °C", format=".1f")],
        )
        labels = bars.mark_text(align="left", dx=4, fontWeight=600).encode(
            text=alt.Text("temp_max:Q", format=".1f"))
        st.altair_chart((bars + labels).properties(height=300), width="stretch")

    with ui.card():
        st.subheader("📈 Daily highs, all cities", anchor=False)
        picked = st.pills("Cities", sorted(df["city"].unique()), selection_mode="multi",
                          default=sorted(df["city"].unique()), label_visibility="collapsed")
        lines = alt.Chart(df[df["city"].isin(picked or [])]).mark_line(
            strokeWidth=2.2, interpolate="monotone").encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("temp_max:Q", title="°C", scale=alt.Scale(zero=False)),
            color=alt.Color("city:N", title="City"),
            tooltip=["city", alt.Tooltip("date:T", format="%d %b"),
                     alt.Tooltip("temp_max", title="High °C")],
        ).properties(height=320)
        st.altair_chart(lines, width="stretch")


def refresh_all(cities):
    bar = st.progress(0, text="Fetching weather…")
    try:
        for n, c in enumerate(cities, 1):
            db.save_weather(c["id"], weather.fetch_daily(float(c["latitude"]),
                                                         float(c["longitude"])))
            bar.progress(n / len(cities), text=f"Updated {c['name']}")
        ui.flash(f"Updated {len(cities)} cities", "🔄")
        st.rerun()
    except OSError:
        st.error(OFFLINE)


def city_weather():
    ui.page_header("City weather", "Daily highs, lows, rain and wind for one city.", "weather", "🌤️")
    cities = db.get_cities()

    c1, c2, c3 = st.columns([2.2, 1, 1], vertical_alignment="bottom")
    by_label = {f"{c['name']}, {c['country']}": c for c in cities}
    city = by_label[c1.selectbox("City", by_label)] if cities else None

    with c2.popover("Add city", icon=":material/add_location:", width="stretch"):
        with st.form("add_city", clear_on_submit=True, border=False):
            name = st.text_input("City name", placeholder="e.g. Cuttack, Tokyo, Paris")
            if st.form_submit_button("Find and add", type="primary") and name.strip():
                try:
                    found = weather.find_city(name.strip())
                    if not found:
                        st.error("City not found.")
                    elif db.add_city(*found):
                        new = next(c for c in db.get_cities() if c["name"] == found[0])
                        db.save_weather(new["id"], weather.fetch_daily(found[2], found[3]))
                        ui.flash(f"Added {found[0]} with 30 days of weather", "📍")
                        st.rerun()
                    else:
                        st.warning(f"{found[0]} is already in the list.")
                except OSError:
                    st.error(OFFLINE)

    if not city:
        st.info("No cities yet. Use **Add city** to add one.")
        return

    if c3.button("Refresh", icon=":material/refresh:", width="stretch"):
        try:
            rows = weather.fetch_daily(float(city["latitude"]), float(city["longitude"]))
            db.save_weather(city["id"], rows)
            st.toast(f"Saved {len(rows)} days for {city['name']}", icon="🔄")
        except OSError:
            st.error(OFFLINE)

    rows = db.get_weather(city["id"])
    if not rows:
        st.info("No weather saved for this city yet. Click **Refresh**.")
        return
    df = ui.to_df(rows)
    df["date"] = pd.to_datetime(df["date"])
    latest = df.iloc[-1]
    hottest = df.loc[df["temp_max"].idxmax()]

    m1, m2, m3, m4 = st.columns(4)
    change = latest["temp_max"] - df.iloc[-2]["temp_max"] if len(df) > 1 else None
    m1.metric(f"{weather_icon(latest)} Today's high", f"{latest['temp_max']:.1f} °C",
              f"{change:+.1f}° vs yesterday" if change is not None else None,
              delta_color="off", chart_data=df["temp_max"].tolist(), chart_type="area")
    m2.metric("🌙 Today's low", f"{latest['temp_min']:.1f} °C",
              chart_data=df["temp_min"].tolist(), chart_type="area")
    m3.metric(f"💧 Rain, {len(df)} days", f"{df['rainfall_mm'].sum():.0f} mm",
              f"{(df['rainfall_mm'] > 0).sum()} rainy days", delta_color="off",
              delta_arrow="off", chart_data=df["rainfall_mm"].tolist(), chart_type="bar")
    m4.metric("🔥 Hottest day", f"{hottest['temp_max']:.1f} °C",
              f"on {hottest['date']:%d %b}", delta_color="off", delta_arrow="off")

    with ui.card():
        st.subheader("Temperature", anchor=False)
        base = alt.Chart(df).encode(x=alt.X("date:T", title=None))
        band = base.mark_area(opacity=0.18, color="#14B8A6").encode(
            y=alt.Y("temp_min:Q", title="°C", scale=alt.Scale(zero=False)), y2="temp_max:Q")
        high = base.mark_line(color="#F97316", strokeWidth=2.5, point=True).encode(
            y="temp_max:Q",
            tooltip=[alt.Tooltip("date:T", format="%d %b"),
                     alt.Tooltip("temp_max", title="High °C"),
                     alt.Tooltip("temp_min", title="Low °C")])
        low = base.mark_line(color="#3B82F6", strokeWidth=2.5, point=True).encode(y="temp_min:Q")
        st.altair_chart((band + high + low).properties(height=320), width="stretch")
        st.markdown("<span class='muted'>🟠 High &nbsp;&nbsp; 🔵 Low</span>",
                    unsafe_allow_html=True)

    left, right = st.columns(2)
    with left, ui.card():
        st.subheader("Rainfall", anchor=False)
        rain = alt.Chart(df).mark_bar(color="#3B82F6", cornerRadiusTopLeft=3,
                                      cornerRadiusTopRight=3).encode(
            x=alt.X("date:T", title=None), y=alt.Y("rainfall_mm:Q", title="mm"),
            tooltip=[alt.Tooltip("date:T", format="%d %b"), alt.Tooltip("rainfall_mm", title="mm")],
        ).properties(height=240)
        st.altair_chart(rain, width="stretch")
    with right, ui.card():
        st.subheader("Wind", anchor=False)
        wind = alt.Chart(df).mark_area(
            line={"color": "#14B8A6"}, color="#14B8A6", opacity=0.3, interpolate="monotone"
        ).encode(
            x=alt.X("date:T", title=None), y=alt.Y("wind_kmh:Q", title="km/h"),
            tooltip=[alt.Tooltip("date:T", format="%d %b"), alt.Tooltip("wind_kmh", title="km/h")],
        ).properties(height=240)
        st.altair_chart(wind, width="stretch")

    c1, c2 = st.columns([3, 1])
    with c1.expander("Raw data"):
        st.dataframe(df, hide_index=True, width="stretch")
    if c2.button(f"Remove {city['name']}", icon=":material/delete:", width="stretch"):
        confirm_remove_city(city)


@st.dialog("Remove city?")
def confirm_remove_city(city):
    st.write(f"This removes **{city['name']}** and all of its saved weather.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", width="stretch"):
        st.rerun()
    if c2.button("Remove", type="primary", icon=":material/delete:", width="stretch"):
        db.delete_city(city["id"])  # its weather rows go too (ON DELETE CASCADE)
        ui.flash(f"Removed {city['name']}", "🗑️")
        st.rerun()


def sql():
    ui.page_header("SQL playground", "Practise SQL on the cities and weather tables.", "weather", "🧮")
    ui.sql_playground(
        [e for e in EXAMPLES if e["app"] == "weather"],
        "**cities** — id, name, country, latitude, longitude\n\n"
        "**weather** — id, city_id, date, temp_max, temp_min, rainfall_mm, wind_kmh",
    )


PAGES = [
    (home, "Overview", ":material/public:", "weather"),
    (city_weather, "City weather", ":material/partly_cloudy_day:", "weather-city"),
    (sql, "SQL playground", ":material/terminal:", "weather-sql"),
]
