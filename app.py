import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="Huliot Site Visit Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# MODERN FRONTEND CSS
# =========================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #f3f6fb;
    }

    .block-container {
        padding-top: 1rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }

    section[data-testid="stSidebar"] {
        background: #0f172a;
    }

    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] select,
    section[data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #0f172a !important;
    }

    .hero-box {
        background: linear-gradient(135deg, #111827 0%, #1e3a8a 55%, #2563eb 100%);
        border-radius: 24px;
        padding: 28px 32px;
        color: white;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.25);
        margin-bottom: 22px;
    }

    .hero-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 6px;
        letter-spacing: -0.5px;
    }

    .hero-subtitle {
        font-size: 15px;
        color: #dbeafe;
    }

    .status-pill {
        display: inline-block;
        padding: 7px 14px;
        border-radius: 999px;
        background: rgba(255,255,255,0.16);
        color: #ffffff;
        font-size: 13px;
        font-weight: 600;
        margin-top: 16px;
    }

    div[data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 20px 18px;
        border-radius: 22px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
    }

    div[data-testid="metric-container"] label {
        color: #64748b !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-size: 30px !important;
        font-weight: 800 !important;
    }

    .chart-card {
        background: #ffffff;
        border-radius: 22px;
        border: 1px solid #e5e7eb;
        padding: 18px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
        margin-bottom: 18px;
    }

    .card-title {
        font-size: 18px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 2px;
    }

    .card-subtitle {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 10px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        margin-bottom: 16px;
    }

    .stTabs [data-baseweb="tab"] {
        background: #ffffff;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        padding: 10px 20px;
        font-weight: 700;
    }

    .stDataFrame {
        border-radius: 18px;
        overflow: hidden;
    }

    .sidebar-title {
        font-size: 22px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .sidebar-note {
        font-size: 12px;
        color: #cbd5e1 !important;
        margin-bottom: 18px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# GOOGLE SHEET CONNECTION
# =========================================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"

@st.cache_resource
def init_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(creds)

client = init_connection()

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def clean_headers(headers):
    seen = {}
    final_headers = []

    for i, header in enumerate(headers):
        header = str(header).strip()
        if not header:
            header = f"Blank Column {i + 1}"

        if header in seen:
            seen[header] += 1
            header = f"{header}_{seen[header]}"
        else:
            seen[header] = 0

        final_headers.append(header)

    return final_headers


def find_col(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None


def dropdown_values(series):
    values = (
        series.fillna("")
        .astype(str)
        .str.strip()
        .replace(["nan", "None", "none", "NaN"], "")
    )
    values = sorted([v for v in values.unique() if v])
    return ["All"] + values


def filter_df(df, col, value):
    if col and value != "All":
        return df[df[col].fillna("").astype(str).str.strip() == value]
    return df


def visit_status(row):
    is_report = str(row.get("Is Report Visit?", "")).strip().lower()
    submitted_date = str(row.get("Report Submitted Date", "")).strip().lower()

    if is_report in ["no", "false", "n/a", "na"]:
        return "Technical NA"

    if submitted_date and submitted_date not in ["nan", "none", ""]:
        return "Submitted"

    return "Pending"


def floor_total(df):
    floor_col = find_col(df, ["FloorsVisited", "Floors Visited", "Floor Visited", "Floors"])
    if not floor_col:
        return 0

    total = 0
    for value in df[floor_col]:
        value = str(value).strip()
        if not value:
            continue
        try:
            total += int(float(value))
        except Exception:
            total += 1
    return total


def plotly_layout(fig, height=390):
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#334155", size=13),
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    return fig


def bar_chart(data, x, y, color="#2563eb"):
    fig = px.bar(data, x=x, y=y, text=y)
    fig.update_traces(marker_color=color, textposition="outside", hovertemplate="%{x}<br>%{y}<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis_title="")
    return plotly_layout(fig)


def pie_chart(data, names, values):
    fig = px.pie(
        data,
        names=names,
        values=values,
        hole=0.62,
        color_discrete_sequence=["#2563eb", "#f97316", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"]
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return plotly_layout(fig)

# =========================================================
# LOAD GOOGLE SHEET DATA
# =========================================================
@st.cache_data(ttl=300, show_spinner="Loading dashboard data...")
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as error:
        st.error(f"Google Sheet opening error: {error}")
        return pd.DataFrame(), pd.DataFrame()

    visit_frames = []
    master_df = pd.DataFrame()

    for ws in spreadsheet.worksheets():
        title = ws.title.lower().strip()
        raw_data = ws.get_all_values()

        if not raw_data or len(raw_data) < 2:
            continue

        headers = clean_headers(raw_data[0])
        df = pd.DataFrame(raw_data[1:], columns=headers)
        df = df.dropna(how="all")

        if df.empty:
            continue

        if "master" in title:
            master_df = df.copy()
            continue

        if any(x in title for x in ["setting", "config", "associate"]):
            continue

        if "Site Name" in df.columns or "Visit ID" in df.columns:
            df["Source Sheet"] = ws.title
            visit_frames.append(df)

    visits_df = pd.concat(visit_frames, ignore_index=True) if visit_frames else pd.DataFrame()
    return visits_df, master_df

visits_df, master_df = load_data()

# =========================================================
# HERO HEADER
# =========================================================
st.markdown("""
<div class="hero-box">
    <div class="hero-title">🏗️ Huliot Site Visit Dashboard</div>
    <div class="hero-subtitle">Live analytics for site visits, pending reports, submitted reports, project status and team activity.</div>
    <div class="status-pill">Google Sheets Live Sync • Auto Refresh Every 5 Minutes</div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown('<div class="sidebar-title">Dashboard Filters</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-note">Use filters to check site-wise, person-wise and month-wise performance.</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3 = st.tabs(["📊 Visit Dashboard", "📈 Master Dashboard", "🧾 Data Table"])

# =========================================================
# VISIT DASHBOARD
# =========================================================
with tab1:
    if visits_df.empty:
        st.warning("No visit data found.")
    else:
        visits = visits_df.copy()

        site_col = find_col(visits, ["Site Name", "Project Name", "Site"])
        date_col = find_col(visits, ["Date of Visit", "Visit Date", "Date"])
        associate_col = find_col(visits, ["Associate ID", "Associate", "Technical Person", "Person Name"])
        tower_col = find_col(visits, ["Tower Name", "Tower", "Building"])

        visits["Status"] = visits.apply(visit_status, axis=1)

        if date_col:
            visits["Visit Date"] = pd.to_datetime(visits[date_col], errors="coerce", dayfirst=True)
            visits["Month"] = visits["Visit Date"].dt.strftime("%b %Y").fillna("Unknown")
        else:
            visits["Visit Date"] = pd.NaT
            visits["Month"] = "Unknown"

        with st.sidebar:
            st.markdown("---")
            st.subheader("Visit Filters")
            search = st.text_input("Search Visit")
            f_source = st.selectbox("Source Sheet", dropdown_values(visits["Source Sheet"]))
            f_month = st.selectbox("Month", dropdown_values(visits["Month"]))
            f_status = st.selectbox("Status", dropdown_values(visits["Status"]))
            f_site = st.selectbox("Site", dropdown_values(visits[site_col])) if site_col else "All"
            f_associate = st.selectbox("Associate", dropdown_values(visits[associate_col])) if associate_col else "All"

        filtered = visits.copy()
        filtered = filter_df(filtered, "Source Sheet", f_source)
        filtered = filter_df(filtered, "Month", f_month)
        filtered = filter_df(filtered, "Status", f_status)
        filtered = filter_df(filtered, site_col, f_site)
        filtered = filter_df(filtered, associate_col, f_associate)

        if search:
            search_cols = [c for c in [site_col, "Visit ID", "Comment", tower_col, associate_col] if c and c in filtered.columns]
            if search_cols:
                mask = filtered[search_cols].astype(str).apply(
                    lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
                )
                filtered = filtered[mask]

        total = len(filtered)
        submitted = len(filtered[filtered["Status"] == "Submitted"])
        pending = len(filtered[filtered["Status"] == "Pending"])
        technical_na = len(filtered[filtered["Status"] == "Technical NA"])
        floors = floor_total(filtered[filtered["Status"] == "Submitted"])
        rate = round((submitted / total) * 100, 1) if total else 0

        a, b, c, d, e = st.columns(5)
        a.metric("Total Visits", total)
        b.metric("Submitted", submitted)
        c.metric("Pending", pending)
        d.metric("Technical NA", technical_na)
        e.metric("Submit Rate", f"{rate}%")

        f, g = st.columns([1, 1])
        with f:
            st.metric("Submitted Floors", floors)
        with g:
            unique_sites = filtered[site_col].nunique() if site_col else 0
            st.metric("Active Sites", unique_sites)

        st.markdown("---")

        chart1, chart2 = st.columns(2)
        with chart1:
            st.markdown('<div class="chart-card"><div class="card-title">Monthly Visit Trend</div><div class="card-subtitle">Total visits grouped month-wise</div>', unsafe_allow_html=True)
            month_data = filtered.groupby("Month").size().reset_index(name="Visits")
            st.plotly_chart(bar_chart(month_data, "Month", "Visits", "#2563eb"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with chart2:
            st.markdown('<div class="chart-card"><div class="card-title">Report Status</div><div class="card-subtitle">Pending vs submitted vs technical NA</div>', unsafe_allow_html=True)
            status_data = filtered["Status"].value_counts().reset_index()
            status_data.columns = ["Status", "Count"]
            st.plotly_chart(pie_chart(status_data, "Status", "Count"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        chart3, chart4 = st.columns(2)
        with chart3:
            st.markdown('<div class="chart-card"><div class="card-title">Top Sites</div><div class="card-subtitle">Most visited sites</div>', unsafe_allow_html=True)
            if site_col:
                site_data = filtered[site_col].value_counts().head(10).reset_index()
                site_data.columns = ["Site", "Visits"]
                st.plotly_chart(bar_chart(site_data, "Site", "Visits", "#10b981"), use_container_width=True)
            else:
                st.info("Site column missing.")
            st.markdown('</div>', unsafe_allow_html=True)

        with chart4:
            st.markdown('<div class="chart-card"><div class="card-title">Associate Performance</div><div class="card-subtitle">Visit count by associate or technical person</div>', unsafe_allow_html=True)
            if associate_col:
                associate_data = filtered[associate_col].value_counts().head(10).reset_index()
                associate_data.columns = ["Associate", "Visits"]
                st.plotly_chart(bar_chart(associate_data, "Associate", "Visits", "#f97316"), use_container_width=True)
            else:
                st.info("Associate column missing.")
            st.markdown('</div>', unsafe_allow_html=True)

        st.subheader("Visit Details")
        required_cols = [
            "Source Sheet", "Visit ID", site_col, tower_col, associate_col,
            date_col, "Status", "Report Submitted Date", "FloorsVisited", "Floors Visited", "Comment"
        ]
        show_cols = []
        for col in required_cols:
            if col and col in filtered.columns and col not in show_cols:
                show_cols.append(col)

        st.dataframe(filtered[show_cols].astype(str), use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download Visit Data",
            filtered.astype(str).to_csv(index=False).encode("utf-8"),
            "visit_dashboard_data.csv",
            "text/csv",
            use_container_width=True
        )

# =========================================================
# MASTER DASHBOARD
# =========================================================
with tab2:
    if master_df.empty:
        st.warning("No master data found.")
    else:
        master = master_df.copy()

        col_project = find_col(master, ["PROJECT NAME", "Project Name", "SITE NAME", "Site Name"])
        col_state = find_col(master, ["STATE", "State"])
        col_city = find_col(master, ["DISTRICT / CITY", "DISTRICT", "District", "City"])
        col_status = find_col(master, ["STATUS OF PROJECT", "Status", "STATUS"])
        col_tech = find_col(master, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
        col_sales = find_col(master, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
        col_distributor = find_col(master, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])
        col_ongoing = find_col(master, ["VISIT ONGOING", "Visit Ongoing", "ONGOING"])

        with st.sidebar:
            st.markdown("---")
            st.subheader("Master Filters")
            m_search = st.text_input("Search Project")
            m_state = st.selectbox("State", dropdown_values(master[col_state])) if col_state else "All"
            m_city = st.selectbox("District / City", dropdown_values(master[col_city])) if col_city else "All"
            m_status = st.selectbox("Project Status", dropdown_values(master[col_status])) if col_status else "All"
            m_tech = st.selectbox("Technical Person", dropdown_values(master[col_tech])) if col_tech else "All"
            m_sales = st.selectbox("Sales Person", dropdown_values(master[col_sales])) if col_sales else "All"

        m_filtered = master.copy()
        m_filtered = filter_df(m_filtered, col_state, m_state)
        m_filtered = filter_df(m_filtered, col_city, m_city)
        m_filtered = filter_df(m_filtered, col_status, m_status)
        m_filtered = filter_df(m_filtered, col_tech, m_tech)
        m_filtered = filter_df(m_filtered, col_sales, m_sales)

        if m_search:
            mask = m_filtered.astype(str).apply(
                lambda row: row.str.contains(m_search, case=False, na=False).any(), axis=1
            )
            m_filtered = m_filtered[mask]

        total_projects = len(m_filtered)
        active_projects = 0
        if col_ongoing:
            active_projects = len(
                m_filtered[
                    m_filtered[col_ongoing]
                    .astype(str)
                    .str.lower()
                    .str.strip()
                    .isin(["yes", "y", "ongoing", "active"])
                ]
            )

        states = m_filtered[col_state].nunique() if col_state else 0
        cities = m_filtered[col_city].nunique() if col_city else 0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Total Projects", total_projects)
        p2.metric("Active Visits", active_projects)
        p3.metric("States", states)
        p4.metric("Cities", cities)

        st.markdown("---")

        m1, m2 = st.columns(2)
        with m1:
            st.markdown('<div class="chart-card"><div class="card-title">Projects by State</div><div class="card-subtitle">State-wise project distribution</div>', unsafe_allow_html=True)
            if col_state:
                data = m_filtered[col_state].value_counts().reset_index()
                data.columns = ["State", "Projects"]
                st.plotly_chart(bar_chart(data, "State", "Projects", "#2563eb"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with m2:
            st.markdown('<div class="chart-card"><div class="card-title">Project Status</div><div class="card-subtitle">Current project stage summary</div>', unsafe_allow_html=True)
            if col_status:
                data = m_filtered[col_status].value_counts().reset_index()
                data.columns = ["Status", "Projects"]
                st.plotly_chart(pie_chart(data, "Status", "Projects"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        m3, m4 = st.columns(2)
        with m3:
            st.markdown('<div class="chart-card"><div class="card-title">Technical Person Load</div><div class="card-subtitle">Project allocation by technical person</div>', unsafe_allow_html=True)
            if col_tech:
                data = m_filtered[col_tech].value_counts().head(10).reset_index()
                data.columns = ["Technical Person", "Projects"]
                st.plotly_chart(bar_chart(data, "Technical Person", "Projects", "#10b981"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with m4:
            st.markdown('<div class="chart-card"><div class="card-title">Sales Person Load</div><div class="card-subtitle">Project allocation by sales person</div>', unsafe_allow_html=True)
            if col_sales:
                data = m_filtered[col_sales].value_counts().head(10).reset_index()
                data.columns = ["Sales Person", "Projects"]
                st.plotly_chart(bar_chart(data, "Sales Person", "Projects", "#f97316"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.subheader("Master Project Directory")
        st.dataframe(m_filtered.astype(str), use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download Master Data",
            m_filtered.astype(str).to_csv(index=False).encode("utf-8"),
            "master_project_dashboard_data.csv",
            "text/csv",
            use_container_width=True
        )

# =========================================================
# DATA TABLE
# =========================================================
with tab3:
    st.subheader("Raw Data Preview")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Visit Data")
        st.caption(f"Rows: {len(visits_df)} | Columns: {len(visits_df.columns)}")
        st.dataframe(visits_df.astype(str), use_container_width=True, hide_index=True)

    with c2:
        st.markdown("### Master Data")
        st.caption(f"Rows: {len(master_df)} | Columns: {len(master_df.columns)}")
        st.dataframe(master_df.astype(str), use_container_width=True, hide_index=True)
