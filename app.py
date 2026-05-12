import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, time as dtime
import os

# ── Config ────────────────────────────────────────────────────────────────────
FUSION_FALL   = "data_ai/facility_usage_fall_2023.csv"
FUSION_SPRING = "data_ai/facility_usage_spring_2024.csv"
LOG_FILE    = "data_ai/fitness_traffic.csv"
os.makedirs("data_ai", exist_ok=True)

CAMPUSES   = ["Turlock", "Stockton"]
DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIER_ORDER = ["Drop-in (1)", "Occasional (2–5)", "Regular (6–20)", "Committed (21–50)", "Super User (51+)"]
CAMPUS_COLORS = {"Turlock": "#1a7fe0", "Stockton": "#e05c1a"}

# ── Fusion Innosoft helpers ───────────────────────────────────────────────────
@st.cache_data
def load_fusion():
    fall = pd.read_csv(FUSION_FALL).rename(columns={"Access Count": "fall_visits"})
    spr  = pd.read_csv(FUSION_SPRING).rename(columns={"Access Count": "spring_visits"})
    fall = fall[["Name", "Gender", "fall_visits"]].dropna(subset=["Name"])
    spr  = spr[["Name", "Gender", "spring_visits"]].dropna(subset=["Name"])
    merged = fall.merge(spr, on="Name", how="outer", suffixes=("_fall", "_spr"))
    merged["Gender"]        = merged["Gender_fall"].combine_first(merged["Gender_spr"])
    merged["fall_visits"]   = merged["fall_visits"].fillna(0).astype(int)
    merged["spring_visits"] = merged["spring_visits"].fillna(0).astype(int)
    merged["total_visits"]  = merged["fall_visits"] + merged["spring_visits"]
    merged["in_both"]       = (merged["fall_visits"] > 0) & (merged["spring_visits"] > 0)
    return merged[["Name", "Gender", "fall_visits", "spring_visits", "total_visits", "in_both"]]


def assign_tier(visits):
    if visits == 1:   return "Drop-in (1)"
    if visits <= 5:   return "Occasional (2–5)"
    if visits <= 20:  return "Regular (6–20)"
    if visits <= 50:  return "Committed (21–50)"
    return "Super User (51+)"


# ── Traffic log helpers ───────────────────────────────────────────────────────
def load_log():
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"]      = pd.to_datetime(df["date"]).dt.date
        if "campus" not in df.columns:
            df["campus"] = "Turlock"
        return df
    return pd.DataFrame(columns=["timestamp", "day_of_week", "hour", "date", "visitors", "campus"])


def save_log(df):
    df.to_csv(LOG_FILE, index=False)


def log_entry(entry_date, entry_time, visitors, campus):
    dt  = datetime.combine(entry_date, entry_time)
    df  = load_log()
    row = {
        "timestamp":   dt,
        "day_of_week": dt.strftime("%A"),
        "hour":        dt.hour,
        "date":        dt.date(),
        "visitors":    int(visitors),
        "campus":      campus,
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_log(df)


def fmt_hour(h):
    return datetime(2000, 1, 1, int(h)).strftime("%I:00 %p")


def analytics_charts(log, label=""):
    """Render hourly bar, day-of-week bar, heatmap, and daily trend for a subset of the log."""
    if log.empty:
        st.info(f"No entries logged yet{' for ' + label if label else ''}.")
        return

    hourly  = log.groupby("hour")["visitors"].sum()
    dow_agg = log.groupby("day_of_week")["visitors"].sum()
    color   = CAMPUS_COLORS.get(label, "#555")

    # Heatmap
    pivot = log.groupby(["day_of_week", "hour"])["visitors"].sum().reset_index()
    ptbl  = pivot.pivot(index="day_of_week", columns="hour", values="visitors").fillna(0)
    ptbl  = ptbl.reindex([d for d in DAYS_ORDER if d in ptbl.index])
    for h in range(24):
        if h not in ptbl.columns:
            ptbl[h] = 0
    ptbl    = ptbl[sorted(ptbl.columns)]
    hlabels = [datetime(2000, 1, 1, h).strftime("%-I %p") for h in sorted(ptbl.columns)]
    fig_heat = px.imshow(ptbl, x=hlabels, color_continuous_scale="YlOrRd",
                         labels=dict(x="Hour", y="Day", color="Visitors"),
                         title=f"Heatmap{' — ' + label if label else ''}")
    fig_heat.update_layout(height=300, margin=dict(t=50, b=10))
    st.plotly_chart(fig_heat, use_container_width=True)

    cl, cr = st.columns(2)
    with cl:
        h_df = hourly.reset_index()
        h_df.columns = ["hour", "visitors"]
        h_df["label"] = h_df["hour"].apply(fmt_hour)
        fig_h = px.bar(h_df, x="label", y="visitors", title="By Hour",
                       labels={"label": "Hour", "visitors": "Visitors"})
        fig_h.update_traces(marker_color=color)
        fig_h.update_layout(xaxis_tickangle=-45, height=320)
        st.plotly_chart(fig_h, use_container_width=True)

    with cr:
        dow_df = dow_agg.reset_index()
        dow_df.columns = ["day_of_week", "visitors"]
        dow_df["day_of_week"] = pd.Categorical(dow_df["day_of_week"], categories=DAYS_ORDER, ordered=True)
        dow_df = dow_df.sort_values("day_of_week")
        fig_d = px.bar(dow_df, x="day_of_week", y="visitors", title="By Day of Week",
                       labels={"day_of_week": "Day", "visitors": "Visitors"})
        fig_d.update_traces(marker_color=color)
        fig_d.update_layout(height=320)
        st.plotly_chart(fig_d, use_container_width=True)

    daily_df = log.groupby("date")["visitors"].sum().reset_index().sort_values("date")
    fig_trend = px.line(daily_df, x="date", y="visitors", markers=True,
                        title=f"Daily Trend{' — ' + label if label else ''}",
                        labels={"date": "Date", "visitors": "Visitors"})
    fig_trend.update_traces(line_color=color, marker_color=color)
    fig_trend.update_layout(height=300)
    st.plotly_chart(fig_trend, use_container_width=True)

    i1, i2 = st.columns(2)
    i1.success(f"**Peak:** {fmt_hour(hourly.idxmax())} on **{dow_agg.idxmax()}s** — schedule extra staff.")
    i2.info(f"**Quietest:** {fmt_hour(hourly.idxmin())} on **{dow_agg.idxmin()}s** — ideal for maintenance.")


# ── Page ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RecFlow App",
    page_icon="🏋️",
    layout="wide",
)

# ── Sidebar — campus selector ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📍 Campus")
    campus_view = st.radio(
        "View",
        ["Both Campuses", "Turlock", "Stockton"],
        index=0,
    )
    st.divider()
    st.caption("Powered by Fusion Innosoft\nCal State East Bay Recreation")

st.title("🏋️ Fitness Center Foot Traffic Tracker")
if campus_view == "Both Campuses":
    st.caption("Showing data for **Turlock** and **Stockton** campuses")
else:
    st.caption(f"Showing data for **{campus_view}** campus")

tab1, tab2, tab3 = st.tabs([
    "📥 Daily Traffic Log",
    "📊 Fusion Innosoft Analytics",
    "🗂️ Data",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Daily Traffic Log  (first tab)
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    full_log = load_log()

    # ── Log entry form ────────────────────────────────────────────────────────
    st.subheader("Log a Visitor Entry")

    log_campus = campus_view if campus_view != "Both Campuses" else "Turlock"

    qc1, qc2 = st.columns([3, 1])
    with qc1:
        if st.button("⚡ Quick Log — Right Now (1 visitor)", type="primary", use_container_width=True):
            now = datetime.now()
            log_entry(now.date(), now.time(), 1, log_campus)
            st.success(f"Logged 1 visitor at {now.strftime('%I:%M %p')} · **{log_campus}**")
            st.rerun()
    with qc2:
        if campus_view == "Both Campuses":
            log_campus = st.selectbox("Campus", CAMPUSES, key="quick_campus")

    st.divider()
    st.markdown("**Log a specific entry:**")
    c1, c2, c3 = st.columns(3)
    with c1:
        entry_date = st.date_input("Date", value=date.today())
        visitors   = st.number_input("Visitors", min_value=1, max_value=500, value=1)
    with c2:
        entry_hour   = st.selectbox("Hour", list(range(24)), format_func=fmt_hour, index=datetime.now().hour)
        entry_minute = st.selectbox("Minute", [0, 15, 30, 45], format_func=lambda m: f":{m:02d}")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        form_campus = st.selectbox("Campus", CAMPUSES,
                                   index=CAMPUSES.index(log_campus) if log_campus in CAMPUSES else 0)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Log Entry", use_container_width=True):
            log_entry(entry_date, dtime(entry_hour, entry_minute), visitors, form_campus)
            ts_str = datetime(2000, 1, 1, entry_hour, entry_minute).strftime("%I:%M %p")
            st.success(f"Logged **{visitors}** visitor(s) at **{ts_str}** on **{entry_date.strftime('%A, %B %d')}** · **{form_campus}**")
            st.rerun()

    st.divider()

    # ── Analytics ─────────────────────────────────────────────────────────────
    if campus_view == "Both Campuses":
        t_log = full_log[full_log["campus"] == "Turlock"]
        s_log = full_log[full_log["campus"] == "Stockton"]

        # ── Comparison KPIs ───────────────────────────────────────────────────
        st.subheader("Campus Comparison")

        t_total = int(t_log["visitors"].sum()) if not t_log.empty else 0
        s_total = int(s_log["visitors"].sum()) if not s_log.empty else 0
        t_today = int(t_log[t_log["date"] == date.today()]["visitors"].sum()) if not t_log.empty else 0
        s_today = int(s_log[s_log["date"] == date.today()]["visitors"].sum()) if not s_log.empty else 0

        kl, km, kr = st.columns(3)
        kl.metric("Total Visitors — Turlock",  f"{t_total:,}")
        km.metric("Total Visitors — Stockton", f"{s_total:,}")
        kr.metric("Combined Total", f"{t_total + s_total:,}")
        kl.metric("Today — Turlock",  t_today)
        km.metric("Today — Stockton", s_today)

        # ── Comparison overlay charts ─────────────────────────────────────────
        if not t_log.empty or not s_log.empty:
            st.subheader("Side-by-Side Comparison")

            # Hourly comparison
            t_hourly = t_log.groupby("hour")["visitors"].sum().reset_index().rename(columns={"visitors": "Turlock"}) if not t_log.empty else pd.DataFrame(columns=["hour", "Turlock"])
            s_hourly = s_log.groupby("hour")["visitors"].sum().reset_index().rename(columns={"visitors": "Stockton"}) if not s_log.empty else pd.DataFrame(columns=["hour", "Stockton"])
            h_comp = pd.DataFrame({"hour": range(24)})
            h_comp = h_comp.merge(t_hourly, on="hour", how="left").merge(s_hourly, on="hour", how="left").fillna(0)
            h_comp["label"] = h_comp["hour"].apply(fmt_hour)
            fig_hcomp = go.Figure()
            fig_hcomp.add_bar(x=h_comp["label"], y=h_comp.get("Turlock", [0]*24),  name="Turlock",  marker_color=CAMPUS_COLORS["Turlock"])
            fig_hcomp.add_bar(x=h_comp["label"], y=h_comp.get("Stockton", [0]*24), name="Stockton", marker_color=CAMPUS_COLORS["Stockton"])
            fig_hcomp.update_layout(barmode="group", title="Visitors by Hour — Both Campuses",
                                     xaxis_tickangle=-45, height=350,
                                     legend=dict(orientation="h", y=-0.3))
            st.plotly_chart(fig_hcomp, use_container_width=True)

            # Day-of-week comparison
            t_dow = t_log.groupby("day_of_week")["visitors"].sum().reset_index().rename(columns={"visitors": "Turlock"}) if not t_log.empty else pd.DataFrame(columns=["day_of_week", "Turlock"])
            s_dow = s_log.groupby("day_of_week")["visitors"].sum().reset_index().rename(columns={"visitors": "Stockton"}) if not s_log.empty else pd.DataFrame(columns=["day_of_week", "Stockton"])
            d_comp = pd.DataFrame({"day_of_week": DAYS_ORDER})
            d_comp = d_comp.merge(t_dow, on="day_of_week", how="left").merge(s_dow, on="day_of_week", how="left").fillna(0)
            fig_dcomp = go.Figure()
            fig_dcomp.add_bar(x=d_comp["day_of_week"], y=d_comp.get("Turlock", [0]*7),  name="Turlock",  marker_color=CAMPUS_COLORS["Turlock"])
            fig_dcomp.add_bar(x=d_comp["day_of_week"], y=d_comp.get("Stockton", [0]*7), name="Stockton", marker_color=CAMPUS_COLORS["Stockton"])
            fig_dcomp.update_layout(barmode="group", title="Visitors by Day — Both Campuses",
                                     height=350, legend=dict(orientation="h", y=-0.3))
            st.plotly_chart(fig_dcomp, use_container_width=True)

            # Daily trend overlay
            all_dates = pd.concat([
                t_log.groupby("date")["visitors"].sum().reset_index().assign(Campus="Turlock"),
                s_log.groupby("date")["visitors"].sum().reset_index().assign(Campus="Stockton"),
            ]) if not t_log.empty or not s_log.empty else pd.DataFrame()
            if not all_dates.empty:
                fig_trend = px.line(all_dates.sort_values("date"), x="date", y="visitors",
                                    color="Campus", markers=True,
                                    color_discrete_map=CAMPUS_COLORS,
                                    title="Daily Trend — Both Campuses",
                                    labels={"date": "Date", "visitors": "Visitors"})
                fig_trend.update_layout(height=320, legend=dict(orientation="h", y=-0.25))
                st.plotly_chart(fig_trend, use_container_width=True)

            # Individual heatmaps
            hl, hr = st.columns(2)
            with hl:
                st.markdown(f"**Turlock Heatmap**")
                if not t_log.empty:
                    analytics_charts(t_log, "Turlock")
                else:
                    st.info("No Turlock data yet.")
            with hr:
                st.markdown(f"**Stockton Heatmap**")
                if not s_log.empty:
                    analytics_charts(s_log, "Stockton")
                else:
                    st.info("No Stockton data yet.")
        else:
            st.info("No log entries yet. Start with the Quick Log button above.")

    else:
        # Single campus view
        filtered = full_log[full_log["campus"] == campus_view]
        if filtered.empty:
            st.info(f"No entries logged for **{campus_view}** yet. Use the form above to start tracking.")
        else:
            total   = int(filtered["visitors"].sum())
            today_v = int(filtered[filtered["date"] == date.today()]["visitors"].sum()) if date.today() in filtered["date"].values else 0
            hourly  = filtered.groupby("hour")["visitors"].sum()
            dow_agg = filtered.groupby("day_of_week")["visitors"].sum()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Visitors", f"{total:,}")
            m2.metric("Today", today_v)
            m3.metric("Busiest Hour", fmt_hour(hourly.idxmax()))
            m4.metric("Busiest Day",  dow_agg.idxmax())

            analytics_charts(filtered, campus_view)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Fusion Innosoft Analytics
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    df = load_fusion()

    if campus_view != "Both Campuses":
        st.info(
            f"The current Fusion Innosoft export covers both campuses combined. "
            f"Campus-specific breakdowns will be available once separate exports are provided per location.",
            icon="ℹ️"
        )

    fall_df = df[df["fall_visits"]   > 0]
    spr_df  = df[df["spring_visits"] > 0]

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_unique  = len(df)
    fall_unique   = len(fall_df)
    spr_unique    = len(spr_df)
    returning     = int(df["in_both"].sum())
    fall_total    = int(df["fall_visits"].sum())
    spr_total     = int(df["spring_visits"].sum())
    pct_change    = round((spr_total - fall_total) / fall_total * 100, 1)
    pct_returning = round(returning / total_unique * 100, 1)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Unique Members (All Year)",           f"{total_unique:,}")
    k2.metric("Total Visits — Fall 2023",            f"{fall_total:,}")
    k3.metric("Total Visits — Spring 2024",          f"{spr_total:,}", delta=f"{pct_change:+}% vs Fall")
    k4.metric("Returning Members (Both Semesters)",  f"{returning:,}", delta=f"{pct_returning}% of all")

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Semester Comparison")
        fig_sem = go.Figure()
        fig_sem.add_bar(name="Total Visits",   x=["Fall 2023", "Spring 2024"], y=[fall_total, spr_total],   marker_color="#e05c1a")
        fig_sem.add_bar(name="Unique Members", x=["Fall 2023", "Spring 2024"], y=[fall_unique, spr_unique], marker_color="#1a7fe0")
        fig_sem.update_layout(barmode="group", height=340, title="Visits & Members by Semester",
                              legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig_sem, use_container_width=True)

    with col_b:
        st.subheader("Gender Breakdown by Semester")
        gender_rows = []
        for sem, sdf, vcol in [("Fall 2023", fall_df, "fall_visits"), ("Spring 2024", spr_df, "spring_visits")]:
            for gender, grp in sdf.groupby("Gender"):
                gender_rows.append({"Semester": sem, "Gender": gender, "Members": len(grp)})
        gdf = pd.DataFrame(gender_rows)
        gdf = gdf[gdf["Gender"].isin(["Male", "Female"])]
        fig_g = px.bar(gdf, x="Semester", y="Members", color="Gender", barmode="group",
                       color_discrete_map={"Male": "#4b8bbe", "Female": "#e07b54"},
                       title="Members by Gender", height=340)
        fig_g.update_layout(legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig_g, use_container_width=True)

    st.divider()
    st.subheader("Member Engagement Tiers")

    tier_rows = []
    for sem, sdf, vcol in [("Fall 2023", fall_df, "fall_visits"), ("Spring 2024", spr_df, "spring_visits")]:
        sdf = sdf.copy()
        sdf["tier"] = sdf[vcol].apply(assign_tier)
        for tier, grp in sdf.groupby("tier"):
            tier_rows.append({"Semester": sem, "Tier": tier, "Members": len(grp)})
    tier_df = pd.DataFrame(tier_rows)
    tier_df["Tier"] = pd.Categorical(tier_df["Tier"], categories=TIER_ORDER, ordered=True)
    tier_df = tier_df.sort_values("Tier")
    fig_tier = px.bar(tier_df, x="Tier", y="Members", color="Semester", barmode="group",
                      color_discrete_map={"Fall 2023": "#e05c1a", "Spring 2024": "#1a7fe0"},
                      title="Members per Engagement Tier", height=360)
    fig_tier.update_layout(legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig_tier, use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Visit Frequency Distribution")
        fig_hist = go.Figure()
        fig_hist.add_histogram(x=fall_df["fall_visits"].clip(upper=80),   name="Fall 2023",   marker_color="#e05c1a", opacity=0.75, nbinsx=30)
        fig_hist.add_histogram(x=spr_df["spring_visits"].clip(upper=80),  name="Spring 2024", marker_color="#1a7fe0", opacity=0.75, nbinsx=30)
        fig_hist.update_layout(barmode="overlay", height=340,
                               title="How Often Do Members Visit? (capped at 80)",
                               xaxis_title="Visits per Semester", yaxis_title="Members",
                               legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_d:
        st.subheader("Top 15 Most Active Members")
        top = df.nlargest(15, "total_visits")[["Name", "Gender", "fall_visits", "spring_visits", "total_visits"]]
        top.columns = ["Name", "Gender", "Fall 2023", "Spring 2024", "Total"]
        st.dataframe(top.reset_index(drop=True), use_container_width=True, height=340)

    st.divider()
    st.subheader("Member Retention")
    new_spring   = int((df["fall_visits"] == 0).sum())
    lost_members = int((df["spring_visits"] == 0).sum())
    ri1, ri2, ri3 = st.columns(3)
    ri1.success(f"**{returning:,}** members visited **both semesters**")
    ri2.info(f"**{new_spring:,}** new members joined in **Spring 2024**")
    ri3.warning(f"**{lost_members:,}** Fall members did **not return** in Spring")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Data
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    full_log = load_log()

    st.subheader("Traffic Log")

    # Campus filter for the table
    view_campus = st.selectbox("Filter by campus", ["All Campuses"] + CAMPUSES, key="data_campus_filter")
    display_log = full_log if view_campus == "All Campuses" else full_log[full_log["campus"] == view_campus]

    if display_log.empty:
        st.info("No log entries yet.")
    else:
        st.download_button("⬇️ Download Log CSV",
                           display_log.to_csv(index=False).encode(), "traffic_log.csv", "text/csv")
        st.dataframe(display_log.sort_values("timestamp", ascending=False).reset_index(drop=True),
                     use_container_width=True)
        with st.expander("⚠️ Delete All Log Entries"):
            st.warning("Permanently removes all manually logged check-ins.")
            if st.button("Confirm Delete", type="secondary"):
                save_log(pd.DataFrame(columns=["timestamp", "day_of_week", "hour", "date", "visitors", "campus"]))
                st.success("Log cleared.")
                st.rerun()

    st.divider()
    st.subheader("Fusion Innosoft Raw Data")
    fusion = load_fusion()
    st.dataframe(fusion, use_container_width=True)
    st.download_button("⬇️ Download Processed Fusion Data",
                       fusion.to_csv(index=False).encode(), "fusion_processed.csv", "text/csv")

    st.divider()
    st.subheader("Import Historical Check-ins")
    st.caption("CSV columns: `date` (YYYY-MM-DD), `time` (HH:MM), `visitors` (optional), `campus` (Turlock or Stockton, optional — defaults to Turlock)")
    uploaded = st.file_uploader("Choose CSV", type="csv")
    if uploaded:
        try:
            imp = pd.read_csv(uploaded)
            st.dataframe(imp.head(), use_container_width=True)
            if st.button("Import"):
                existing = load_log()
                rows = []
                for _, row in imp.iterrows():
                    dt = pd.to_datetime(f"{row['date']} {row['time']}")
                    rows.append({
                        "timestamp":   dt,
                        "day_of_week": dt.strftime("%A"),
                        "hour":        dt.hour,
                        "date":        dt.date(),
                        "visitors":    int(row.get("visitors", 1)),
                        "campus":      str(row.get("campus", "Turlock")),
                    })
                save_log(pd.concat([existing, pd.DataFrame(rows)], ignore_index=True))
                st.success(f"Imported {len(rows)} records.")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
