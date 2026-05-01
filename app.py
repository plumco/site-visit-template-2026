import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ─────────────────────────────────────────
# 1. PAGE CONFIG & CSS
# ─────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Huliot West Zone – Site Visit Analytics",
    page_icon="📊"
)

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 8px 18px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 2. GOOGLE SHEETS CONNECTION
# ─────────────────────────────────────────
@st.cache_resource
def init_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)

client = init_connection()

# ── Paste your Google Sheet URL here ──
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"

# ─────────────────────────────────────────
# 3. LOAD DATA  (refreshes every 5 minutes)
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(
            f"❌ Cannot open Google Sheet. "
            f"Make sure it is shared with your service-account email.\n\nError: {e}"
        )
        return pd.DataFrame(), pd.DataFrame()

    worksheets = spreadsheet.worksheets()
    visit_frames = []
    master_df    = pd.DataFrame()

    for ws in worksheets:
        title    = ws.title.lower()
        raw_data = ws.get_all_values()

        if not raw_data or len(raw_data) < 2:
            continue

        # Deduplicate column headers
        raw_headers = [str(h).strip() for h in raw_data[0]]
        seen, headers = {}, []
        for h in raw_headers:
            if h in seen:
                seen[h] += 1
                headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                headers.append(h)

        df = pd.DataFrame(raw_data[1:], columns=headers)

        if "master" in title:
            master_df = df
            continue

        if any(skip in title for skip in ["setting", "config", "associate"]):
            continue

        if not df.empty and ("Site Name" in df.columns or "Visit ID" in df.columns):
            df["Source Sheet"] = ws.title
            visit_frames.append(df)

    visits_df = (
        pd.concat(visit_frames, ignore_index=True) if visit_frames else pd.DataFrame()
    )
    return visits_df, master_df


# ─────────────────────────────────────────
# 4. HELPER FUNCTIONS
# ─────────────────────────────────────────
def get_visit_status(row):
    is_report = str(row.get("Is Report Visit?", "")).strip().lower()
    sub_date  = str(row.get("Report Submitted Date", "")).strip()
    if is_report in ["no", "false", "n/a"]:
        return "Technical (NA)"
    if sub_date and sub_date.lower() not in ["nan", "none", ""]:
        return "Submitted"
    return "Pending"


def calc_floors(series):
    total = 0
    for val in series:
        try:
            total += int(val)
        except Exception:
            total += 1 if str(val).strip() else 0
    return total


def safe_col(df, options):
    for o in options:
        if o in df.columns:
            return o
    return None


def multiselect_filter(df, column, label, key):
    """Returns filtered df based on a selectbox (All + unique values)."""
    if column not in df.columns:
        return df
    choices = ["All"] + sorted(df[column].astype(str).unique().tolist())
    selected = st.selectbox(label, choices, key=key)
    if selected != "All":
        df = df[df[column].astype(str) == selected]
    return df


# ─────────────────────────────────────────
# 5. LOAD  +  EARLY-EXIT IF EMPTY
# ─────────────────────────────────────────
with st.spinner("Syncing data from Google Sheets …"):
    visits_df, master_df = load_data()

# ─────────────────────────────────────────
# 6. PAGE HEADER
# ─────────────────────────────────────────
st.title("📊 Huliot West Zone – Site Visit Analytics")
st.caption("Live data · refreshes every 5 minutes · Pune | Mumbai | Ahmedabad")
st.markdown("---")

# ─────────────────────────────────────────
# 7. TABS
# ─────────────────────────────────────────
tab_visits, tab_master, tab_exec = st.tabs([
    "📋 Visit Analytics",
    "📁 Master Projects",
    "💼 Executive Dashboard",
])


# ═══════════════════════════════════════════════════════
# TAB 1 · VISIT ANALYTICS
# ═══════════════════════════════════════════════════════
with tab_visits:

    if visits_df.empty:
        st.warning("No visit log data found in the sheet.")
        st.stop()

    # Pre-process
    visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)
    visits_df["Month"]  = (
        pd.to_datetime(visits_df["Date of Visit"], errors="coerce")
        .dt.strftime("%b %Y")
        .fillna("Unknown")
    )

    # ── Filters ──────────────────────────────────────
    st.subheader("Filters")
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)

    with fc1:
        filtered_v = multiselect_filter(visits_df.copy(), "Source Sheet", "Sheet",      "f_sheet")
    with fc2:
        filtered_v = multiselect_filter(filtered_v,       "Month",        "Month",      "f_month")
    with fc3:
        filtered_v = multiselect_filter(filtered_v,       "Status",       "Status",     "f_status")
    with fc4:
        filtered_v = multiselect_filter(filtered_v,       "Associate ID", "Associate",  "f_assoc")
    with fc5:
        filtered_v = multiselect_filter(filtered_v,       "Site Name",    "Site Name",  "f_site")

    # ── KPIs ─────────────────────────────────────────
    total_visits = len(filtered_v)
    pending      = len(filtered_v[filtered_v["Status"] == "Pending"])
    submitted    = len(filtered_v[filtered_v["Status"] == "Submitted"])
    tech_na      = len(filtered_v[filtered_v["Status"] == "Technical (NA)"])

    sub_df = filtered_v[filtered_v["Status"] == "Submitted"]
    floors_col = "FloorsVisited" if "FloorsVisited" in sub_df.columns else "Floors Visited"
    total_floors = calc_floors(sub_df.get(floors_col, pd.Series(dtype=str)))

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Visits",    total_visits)
    k2.metric("Pending Reports", pending)
    k3.metric("Technical (NA)",  tech_na)
    k4.metric("Submitted",       submitted)
    k5.metric("Floors Covered",  total_floors)

    st.markdown("---")

    # ── Charts ───────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        st.markdown("##### Visits Per Month")
        month_counts = (
            filtered_v["Month"].value_counts()
            .rename_axis("Month").reset_index(name="Visits")
        )
        fig_month = px.bar(
            month_counts, x="Month", y="Visits",
            color_discrete_sequence=["#185FA5"]
        )
        fig_month.update_layout(margin=dict(t=10, b=10), height=280)
        st.plotly_chart(fig_month, use_container_width=True)

    with ch2:
        st.markdown("##### Visit Status Breakdown")
        status_counts = (
            filtered_v["Status"].value_counts()
            .rename_axis("Status").reset_index(name="Count")
        )
        fig_status = px.pie(
            status_counts, names="Status", values="Count", hole=0.45,
            color_discrete_sequence=["#0F6E56", "#BA7517", "#888780"]
        )
        fig_status.update_layout(margin=dict(t=10, b=10), height=280)
        st.plotly_chart(fig_status, use_container_width=True)

    # ── Top Sites bar ─────────────────────────────────
    st.markdown("##### Top Sites by Visit Count")
    site_counts = (
        filtered_v["Site Name"].value_counts().nlargest(8)
        .rename_axis("Site Name").reset_index(name="Visits")
    )
    fig_sites = px.bar(
        site_counts, x="Visits", y="Site Name", orientation="h",
        color_discrete_sequence=["#1D9E75"]
    )
    fig_sites.update_layout(
        yaxis={"categoryorder": "total ascending"},
        margin=dict(t=10, b=10), height=300
    )
    st.plotly_chart(fig_sites, use_container_width=True)

    # ── Records Table ────────────────────────────────
    st.subheader("Visit Records")
    display_cols = [
        c for c in [
            "Source Sheet", "Visit ID", "Site Name", "Tower Name",
            "FloorsVisited", "Floors Visited", "Associate ID",
            "Date of Visit", "Status", "Report Submitted Date", "Comment"
        ]
        if c in filtered_v.columns
    ]
    st.dataframe(filtered_v[display_cols].astype(str), use_container_width=True)


# ═══════════════════════════════════════════════════════
# TAB 2 · MASTER PROJECTS
# ═══════════════════════════════════════════════════════
with tab_master:

    if master_df.empty:
        st.warning("No Master sheet found in the spreadsheet.")
        st.stop()

    col_state = safe_col(master_df, ["STATE", "State"])
    col_dist  = safe_col(master_df, ["DISTRICT / CITY", "DISTRICT", "District"])
    col_stat  = safe_col(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
    col_tech  = safe_col(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
    col_sale  = safe_col(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
    col_distr = safe_col(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])
    col_ong   = safe_col(master_df, ["VISIT ONGOING", "Visit Ongoing"])

    # ── Filters ──────────────────────────────────────
    st.subheader("Filters")
    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    filtered_m = master_df.copy()

    cols_map = {
        mc1: (col_state, "State",       "m_state"),
        mc2: (col_dist,  "District",    "m_dist"),
        mc3: (col_stat,  "Proj Status", "m_stat"),
        mc4: (col_tech,  "Tech Person", "m_tech"),
        mc5: (col_sale,  "Sales",       "m_sale"),
        mc6: (col_distr, "Distributor", "m_distr"),
    }
    for col_widget, (col_name, label, key) in cols_map.items():
        if col_name:
            with col_widget:
                filtered_m = multiselect_filter(filtered_m, col_name, label, key)

    # ── KPIs ─────────────────────────────────────────
    total_proj   = len(filtered_m)
    active_proj  = 0
    if col_ong:
        active_proj = len(
            filtered_m[filtered_m[col_ong].astype(str).str.lower().isin(["yes", "y", "ongoing"])]
        )
    unique_states = filtered_m[col_state].nunique() if col_state else 0

    teams_set = set()
    if col_tech: teams_set.update(filtered_m[col_tech].dropna().astype(str))
    if col_sale: teams_set.update(filtered_m[col_sale].dropna().astype(str))
    team_count = len([x for x in teams_set if x.strip() and x.lower() not in ["nan", "none", ""]])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Projects",         total_proj)
    k2.metric("Active / Ongoing",       active_proj)
    k3.metric("States Covered",         unique_states)
    k4.metric("Tech + Sales Personnel", team_count)

    st.markdown("---")

    # ── Charts ───────────────────────────────────────
    mc1, mc2 = st.columns(2)

    with mc1:
        st.markdown("##### Projects by State")
        if col_state:
            state_c = (
                filtered_m[col_state].value_counts()
                .rename_axis("State").reset_index(name="Count")
            )
            fig_state = px.bar(
                state_c, x="State", y="Count",
                color_discrete_sequence=["#1D9E75"]
            )
            fig_state.update_layout(margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig_state, use_container_width=True)

    with mc2:
        st.markdown("##### Project Status Distribution")
        if col_stat:
            stat_c = (
                filtered_m[col_stat].value_counts()
                .rename_axis("Status").reset_index(name="Count")
            )
            fig_pstat = px.pie(
                stat_c, names="Status", values="Count", hole=0.45,
                color_discrete_sequence=["#185FA5", "#1D9E75", "#EF9F27", "#888780"]
            )
            fig_pstat.update_layout(margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig_pstat, use_container_width=True)

    # ── Full Table ────────────────────────────────────
    st.subheader("Master Projects Directory")
    st.dataframe(filtered_m.astype(str), use_container_width=True)


# ═══════════════════════════════════════════════════════
# TAB 3 · EXECUTIVE DASHBOARD
# ═══════════════════════════════════════════════════════
with tab_exec:

    if visits_df.empty:
        st.warning("No data available for the Executive Dashboard.")
        st.stop()

    # Month filter
    st.subheader("Multi-Month Associate Performance")
    all_months = ["All Time"] + sorted(visits_df["Month"].dropna().unique().tolist())
    sel_month  = st.selectbox("Select Month", all_months, key="exec_month")

    df_exec = visits_df.copy()
    if sel_month != "All Time":
        df_exec = df_exec[df_exec["Month"] == sel_month]

    # ── KPIs ─────────────────────────────────────────
    tot_tower  = len(df_exec)
    tot_sites  = df_exec["Site Name"].nunique() if "Site Name" in df_exec.columns else 0
    tot_sent   = len(df_exec[df_exec["Status"] == "Submitted"])
    tot_pend   = len(df_exec[df_exec["Status"] == "Pending"])

    ek1, ek2, ek3, ek4 = st.columns(4)
    ek1.metric("🏢 Tower Visits",     tot_tower)
    ek2.metric("📍 Site Visits",      tot_sites)
    ek3.metric("📄 Reports Sent",     tot_sent)
    ek4.metric("⏱️ Pending Reports",  tot_pend)

    st.markdown("---")

    # ── Executive Charts ─────────────────────────────
    ec1, ec2 = st.columns(2)

    with ec1:
        st.markdown("##### Reports Sent to Client by Associate")
        sent_data = (
            df_exec[df_exec["Status"] == "Submitted"]["Associate ID"]
            .value_counts().rename_axis("Associate ID").reset_index(name="Reports")
        )
        if not sent_data.empty:
            fig_sent = px.bar(
                sent_data, x="Reports", y="Associate ID", orientation="h",
                color_discrete_sequence=["#185FA5"]
            )
            fig_sent.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(t=10, b=10), height=300
            )
            st.plotly_chart(fig_sent, use_container_width=True)
        else:
            st.info("No submitted reports for this period.")

    with ec2:
        st.markdown("##### Tower Visits by Associate")
        tower_data = (
            df_exec["Associate ID"]
            .value_counts().rename_axis("Associate ID").reset_index(name="Tower Visits")
        )
        if not tower_data.empty:
            fig_tower = px.bar(
                tower_data, x="Tower Visits", y="Associate ID", orientation="h",
                color_discrete_sequence=["#1D9E75"]
            )
            fig_tower.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(t=10, b=10), height=300
            )
            st.plotly_chart(fig_tower, use_container_width=True)
        else:
            st.info("No tower visit data for this period.")

    # ── Top 5 Sites ───────────────────────────────────
    if "Site Name" in df_exec.columns:
        st.markdown("##### Top 5 Sites Visited")
        top_sites = df_exec["Site Name"].value_counts().head(5)
        cols = st.columns(5)
        for i, (site, count) in enumerate(top_sites.items()):
            cols[i].metric(f"#{i+1}", site, f"{count} visits")
        st.markdown("---")

    # ── Associate Performance Table ───────────────────
    st.markdown("##### Detailed Associate Performance")

    rows = []
    for assoc, grp in df_exec.groupby("Associate ID"):
        floors_col = "FloorsVisited" if "FloorsVisited" in grp.columns else "Floors Visited"
        floor_visits = calc_floors(grp.get(floors_col, pd.Series(dtype=str)))
        site_visits  = grp["Site Name"].nunique() if "Site Name" in grp.columns else 0

        rep_col  = grp.get("Is Report Visit?", pd.Series([""] * len(grp))).astype(str).str.lower().str.strip()
        mark_yes = len(rep_col[rep_col.isin(["yes", "y", "true"])])
        sugg_no  = len(rep_col[rep_col.isin(["no", "n", "false"])])

        pending = len(grp[grp["Status"] == "Pending"])
        sent    = len(grp[grp["Status"] == "Submitted"])

        rows.append({
            "Associate ID":  assoc,
            "Floor Visits":  floor_visits,
            "Site Visits":   site_visits,
            "Mark (Yes)":    mark_yes,
            "Sugg (No)":     sugg_no,
            "Pending":       pending,
            "Sent":          sent,
            "Backlog":       pending,
            "Grand Total":   len(grp),
        })

    if rows:
        perf_df = pd.DataFrame(rows)
        agg_row = pd.DataFrame([{
            "Associate ID": "TEAM AGGREGATE",
            **{c: perf_df[c].sum() for c in perf_df.columns if c != "Associate ID"}
        }])
        perf_df = pd.concat([perf_df, agg_row], ignore_index=True)
        st.dataframe(perf_df.astype(str), use_container_width=True)
    else:
        st.info("No performance data for this period.")
