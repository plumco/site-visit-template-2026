import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# =========================================================
# 1. PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Executive Site Visit Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# 2. TOP-CLASS FRONTEND CSS
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: radial-gradient(circle at top left, #eff6ff 0, #f8fafc 35%, #eef2f7 100%);
}

.block-container {
    padding: 1.2rem 1.8rem 2rem 1.8rem;
    max-width: 1450px;
}

#MainMenu, footer, header {
    visibility: hidden;
}

/* Premium shell */
.executive-shell {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(203, 213, 225, 0.9);
    border-radius: 30px;
    padding: 26px 28px;
    box-shadow: 0 24px 70px rgba(15, 23, 42, 0.10);
    backdrop-filter: blur(14px);
    margin-bottom: 24px;
}

.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
}

.brand-area {
    display: flex;
    align-items: center;
    gap: 16px;
}

.brand-icon {
    width: 58px;
    height: 58px;
    border-radius: 17px;
    background: linear-gradient(135deg, #2563eb, #4f46e5);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 28px;
    box-shadow: 0 14px 28px rgba(37, 99, 235, 0.35);
}

.brand-title {
    font-size: 30px;
    line-height: 1.1;
    font-weight: 900;
    color: #071126;
    letter-spacing: -1px;
}

.brand-subtitle {
    margin-top: 8px;
    color: #48607f;
    font-size: 14px;
    font-weight: 600;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.pill {
    padding: 12px 18px;
    border-radius: 16px;
    background: #f1f5f9;
    color: #475569;
    font-weight: 800;
    font-size: 13px;
    border: 1px solid #e2e8f0;
}

.pill.active {
    background: white;
    color: #1d4ed8;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
}

.sync-badge {
    margin-top: 20px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 9px 13px;
    border-radius: 999px;
    background: #ecfdf5;
    color: #047857;
    font-weight: 800;
    font-size: 12px;
    border: 1px solid #bbf7d0;
}

/* Filters */
.filter-panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 18px 20px 6px 20px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
    margin-bottom: 22px;
}

.panel-title {
    color: #071126;
    font-size: 18px;
    font-weight: 900;
    margin-bottom: 2px;
}

.panel-subtitle {
    color: #64748b;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 14px;
}

/* KPI Cards */
.kpi-card {
    position: relative;
    overflow: hidden;
    min-height: 150px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 24px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.kpi-card:after {
    content: attr(data-watermark);
    position: absolute;
    right: -8px;
    top: -30px;
    font-size: 105px;
    line-height: 1;
    font-weight: 900;
    color: rgba(15, 23, 42, 0.045);
}

.kpi-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.kpi-icon {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 25px;
    font-weight: 900;
}

.blue { background: linear-gradient(135deg, #2563eb, #6366f1); }
.green { background: linear-gradient(135deg, #10b981, #34d399); }
.orange { background: linear-gradient(135deg, #f59e0b, #f97316); }
.red { background: linear-gradient(135deg, #ef4444, #fb7185); }
.purple { background: linear-gradient(135deg, #7c3aed, #a78bfa); }
.cyan { background: linear-gradient(135deg, #0891b2, #22d3ee); }

.kpi-label {
    color: #64748b;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

.kpi-value {
    margin-top: 10px;
    color: #071126;
    font-size: 36px;
    font-weight: 900;
    letter-spacing: -1px;
}

.kpi-foot {
    margin-top: 14px;
    padding-top: 13px;
    border-top: 1px solid #edf2f7;
    color: #94a3b8;
    font-size: 12px;
    font-style: italic;
    font-weight: 700;
}

.kpi-trend {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 10px;
    border-radius: 12px;
    background: #ecfdf5;
    color: #059669;
    font-size: 12px;
    font-weight: 900;
}

.kpi-trend.warn {
    background: #fff7ed;
    color: #ea580c;
}

.kpi-trend.danger {
    background: #fef2f2;
    color: #dc2626;
}

/* Chart cards */
.chart-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 26px;
    padding: 22px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.07);
    margin-bottom: 22px;
}

.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}

.chart-title-wrap {
    border-left: 5px solid #2563eb;
    padding-left: 12px;
}

.chart-title {
    color: #071126;
    font-size: 18px;
    font-weight: 900;
    margin-bottom: 3px;
}

.chart-subtitle {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
}

.legend-pill {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #475569;
    border-radius: 999px;
    padding: 7px 11px;
    font-size: 11px;
    font-weight: 900;
}

/* Progress list */
.progress-row {
    margin: 18px 0;
}

.progress-label {
    display: flex;
    justify-content: space-between;
    color: #334155;
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 8px;
}

.progress-track {
    height: 11px;
    background: #edf2f7;
    border-radius: 999px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #2563eb, #22c55e);
}

/* Streamlit controls */
.stSelectbox label, .stTextInput label, .stDateInput label, .stMultiSelect label {
    color: #334155 !important;
    font-size: 12px !important;
    font-weight: 900 !important;
}

.stButton > button, .stDownloadButton > button {
    border-radius: 16px !important;
    border: 1px solid #dbe3ef !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #2563eb, #4f46e5) !important;
    color: white !important;
    min-height: 46px;
    box-shadow: 0 12px 28px rgba(37, 99, 235, 0.22);
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background: #edf2f7;
    padding: 8px;
    border-radius: 18px;
    display: inline-flex;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 13px;
    padding: 10px 18px;
    font-weight: 900;
}

.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
    color: #1d4ed8 !important;
}

[data-testid="stDataFrame"] {
    border-radius: 22px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
}

hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 24px 0;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. GOOGLE SHEET CONNECTION
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
# 4. DATA HELPERS
# =========================================================
def clean_headers(headers):
    seen = {}
    output = []
    for i, h in enumerate(headers):
        h = str(h).strip() or f"Blank Column {i + 1}"
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        output.append(h)
    return output


def find_col(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None


def clean_options(series):
    values = series.fillna("").astype(str).str.strip()
    values = values[~values.str.lower().isin(["", "nan", "none", "na"])]
    return ["All"] + sorted(values.unique().tolist())


def filter_exact(df, col, value):
    if col and value != "All":
        return df[df[col].fillna("").astype(str).str.strip() == value]
    return df


def get_status(row):
    is_report = str(row.get("Is Report Visit?", "")).strip().lower()
    submitted = str(row.get("Report Submitted Date", "")).strip().lower()

    if is_report in ["no", "false", "n/a", "na"]:
        return "Technical NA"
    if submitted and submitted not in ["nan", "none", ""]:
        return "Submitted"
    return "Pending"


def get_floor_total(df):
    floor_col = find_col(df, ["FloorsVisited", "Floors Visited", "Floor Visited", "Floors"])
    if not floor_col:
        return 0

    total = 0
    for v in df[floor_col]:
        text = str(v).strip()
        if not text or text.lower() in ["nan", "none", "na"]:
            continue
        try:
            total += int(float(text))
        except Exception:
            total += 1
    return total


def metric_card(title, value, icon, color_class, note="Base month statistics", trend=None, trend_type="good", watermark=""):
    trend_html = ""
    if trend:
        trend_class = "kpi-trend"
        if trend_type == "warn":
            trend_class += " warn"
        if trend_type == "danger":
            trend_class += " danger"
        trend_html = f'<span class="{trend_class}">{trend}</span>'

    return f"""
    <div class="kpi-card" data-watermark="{watermark}">
        <div class="kpi-top">
            <div class="kpi-icon {color_class}">{icon}</div>
            {trend_html}
        </div>
        <div class="kpi-label">{title}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-foot">{note}</div>
    </div>
    """


def progress_list_html(df, name_col, value_col, limit=6):
    if df.empty:
        return "<p style='color:#64748b;font-weight:700;'>No data available</p>"

    top = df.head(limit).copy()
    max_value = max(top[value_col].max(), 1)
    rows = ""
    for _, r in top.iterrows():
        name = str(r[name_col])[:32]
        value = int(r[value_col])
        pct = int((value / max_value) * 100)
        rows += f"""
        <div class="progress-row">
            <div class="progress-label"><span>{name}</span><span>{value}</span></div>
            <div class="progress-track"><div class="progress-fill" style="width:{pct}%"></div></div>
        </div>
        """
    return rows


def fig_layout(fig, height=390):
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter", color="#334155", size=12),
        margin=dict(l=18, r=18, t=15, b=18),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5)
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#eef2f7", zeroline=False)
    return fig


def bar_fig(df, x, y, color="#2563eb", horizontal=False):
    if horizontal:
        fig = px.bar(df, x=y, y=x, orientation="h", text=y)
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
    else:
        fig = px.bar(df, x=x, y=y, text=y)
    fig.update_traces(marker_color=color, textposition="outside", marker_line_width=0, hovertemplate="%{label}<br>%{value}<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis_title="")
    return fig_layout(fig)


def donut_fig(df, names, values):
    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.64,
        color_discrete_sequence=["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"]
    )
    fig.update_traces(textinfo="percent+label", textposition="inside", marker=dict(line=dict(color="#ffffff", width=4)))
    return fig_layout(fig, height=390)

# =========================================================
# 5. LOAD DATA
# =========================================================
@st.cache_data(ttl=300, show_spinner="Building executive dashboard...")
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Could not open Google Sheet. Please check service account sharing. Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    visit_frames = []
    master_df = pd.DataFrame()

    for ws in spreadsheet.worksheets():
        title = ws.title.lower().strip()
        raw = ws.get_all_values()
        if not raw or len(raw) < 2:
            continue

        headers = clean_headers(raw[0])
        df = pd.DataFrame(raw[1:], columns=headers).dropna(how="all")
        if df.empty:
            continue

        if "master" in title:
            master_df = df.copy()
            continue

        if any(skip in title for skip in ["setting", "config", "associate"]):
            continue

        if "Site Name" in df.columns or "Visit ID" in df.columns:
            df["Source Sheet"] = ws.title
            visit_frames.append(df)

    visits_df = pd.concat(visit_frames, ignore_index=True) if visit_frames else pd.DataFrame()
    return visits_df, master_df

visits_df, master_df = load_data()

# =========================================================
# 6. EXECUTIVE HEADER
# =========================================================
now_text = datetime.now().strftime("%d %b %Y, %I:%M %p")

st.markdown(f"""
<div class="executive-shell">
    <div class="topbar">
        <div class="brand-area">
            <div class="brand-icon">▦</div>
            <div>
                <div class="brand-title">Executive Dashboard</div>
                <div class="brand-subtitle">Multi-month associate performance tracking and field analytics</div>
            </div>
        </div>
        <div class="header-actions">
            <div class="pill active">Visual Overview</div>
            <div class="pill">Master Data Table</div>
            <div class="pill">{now_text}</div>
        </div>
    </div>
    <div class="sync-badge">● Live Google Sheets Sync • Auto refresh every 5 minutes</div>
</div>
""", unsafe_allow_html=True)

if st.button("🔄 Refresh Live Data", use_container_width=False):
    st.cache_data.clear()
    st.rerun()

# =========================================================
# 7. MAIN TABS
# =========================================================
tab_visit, tab_master, tab_data = st.tabs(["Visual Overview", "Master Analytics", "Data Tables"])

# =========================================================
# TAB 1: VISIT DASHBOARD
# =========================================================
with tab_visit:
    if visits_df.empty:
        st.warning("No visit data found in Google Sheets.")
    else:
        visits = visits_df.copy()

        site_col = find_col(visits, ["Site Name", "Project Name", "Site"])
        date_col = find_col(visits, ["Date of Visit", "Visit Date", "Date"])
        associate_col = find_col(visits, ["Associate ID", "Associate", "Technical Person", "Person Name"])
        tower_col = find_col(visits, ["Tower Name", "Tower", "Building"])

        visits["Status"] = visits.apply(get_status, axis=1)
        if date_col:
            visits["Visit Date Clean"] = pd.to_datetime(visits[date_col], errors="coerce", dayfirst=True)
            visits["Month"] = visits["Visit Date Clean"].dt.strftime("%B %Y").fillna("Unknown")
        else:
            visits["Visit Date Clean"] = pd.NaT
            visits["Month"] = "Unknown"

        st.markdown('<div class="filter-panel"><div class="panel-title">Smart Filters</div><div class="panel-subtitle">Select month, site, associate or report status to instantly update the dashboard.</div>', unsafe_allow_html=True)
        f1, f2, f3, f4, f5 = st.columns([1.2, 1.2, 1.2, 1.4, 1.4])
        with f1:
            f_month = st.selectbox("Month", clean_options(visits["Month"]), key="v_month")
        with f2:
            f_status = st.selectbox("Report Status", clean_options(visits["Status"]), key="v_status")
        with f3:
            f_source = st.selectbox("Source", clean_options(visits["Source Sheet"]), key="v_source")
        with f4:
            f_site = st.selectbox("Site", clean_options(visits[site_col]), key="v_site") if site_col else "All"
        with f5:
            f_assoc = st.selectbox("Associate", clean_options(visits[associate_col]), key="v_assoc") if associate_col else "All"

        search = st.text_input("Search site, visit ID, tower, comment or associate", key="visit_search")
        st.markdown('</div>', unsafe_allow_html=True)

        filtered = visits.copy()
        filtered = filter_exact(filtered, "Month", f_month)
        filtered = filter_exact(filtered, "Status", f_status)
        filtered = filter_exact(filtered, "Source Sheet", f_source)
        filtered = filter_exact(filtered, site_col, f_site)
        filtered = filter_exact(filtered, associate_col, f_assoc)

        if search:
            search_cols = [c for c in [site_col, "Visit ID", tower_col, associate_col, "Comment"] if c and c in filtered.columns]
            if search_cols:
                mask = filtered[search_cols].astype(str).apply(lambda r: r.str.contains(search, case=False, na=False).any(), axis=1)
                filtered = filtered[mask]

        total_visits = len(filtered)
        submitted = len(filtered[filtered["Status"] == "Submitted"])
        pending = len(filtered[filtered["Status"] == "Pending"])
        tech_na = len(filtered[filtered["Status"] == "Technical NA"])
        floors = get_floor_total(filtered[filtered["Status"] == "Submitted"])
        active_sites = filtered[site_col].nunique() if site_col else 0
        submission_rate = round((submitted / total_visits) * 100, 1) if total_visits else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(metric_card("Total Floor Visits", floors, "▥", "blue", "Submitted report floor count", "↗ Active", "good", "01"), unsafe_allow_html=True)
        with k2:
            st.markdown(metric_card("Total Site Visits", total_visits, "⌖", "green", "All filtered site visits", f"{active_sites} Sites", "good", "02"), unsafe_allow_html=True)
        with k3:
            st.markdown(metric_card("Total Reports Sent", submitted, "▣", "purple", "Reports submitted to client", f"{submission_rate}% Rate", "good", "03"), unsafe_allow_html=True)
        with k4:
            st.markdown(metric_card("Total Pending Reports", pending, "!", "orange", "Reports still pending", f"{pending} Pending", "warn", "04"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns([0.95, 1.45])
        with c1:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Reports Sent to Client</div><div class="chart-subtitle">Associate-wise submitted report performance</div></div><div class="legend-pill">LIVE</div></div>', unsafe_allow_html=True)
            if associate_col:
                report_data = filtered[filtered["Status"] == "Submitted"][associate_col].value_counts().reset_index()
                report_data.columns = ["Associate", "Reports"]
                st.markdown(progress_list_html(report_data, "Associate", "Reports", 7), unsafe_allow_html=True)
            else:
                st.info("Associate column not found.")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Tower vs Site Visits Breakdown</div><div class="chart-subtitle">Visit performance by associate or technical person</div></div><div class="legend-pill">TOWER • SITE</div></div>', unsafe_allow_html=True)
            if associate_col:
                assoc_visits = filtered[associate_col].value_counts().head(10).reset_index()
                assoc_visits.columns = ["Associate", "Visits"]
                st.plotly_chart(bar_fig(assoc_visits, "Associate", "Visits", "#6366f1", horizontal=True), use_container_width=True)
            else:
                st.info("Associate column not found.")
            st.markdown('</div>', unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Monthly Visit Trend</div><div class="chart-subtitle">Month-wise total visit movement</div></div><div class="legend-pill">MONTH</div></div>', unsafe_allow_html=True)
            month_data = filtered.groupby("Month").size().reset_index(name="Visits")
            st.plotly_chart(bar_fig(month_data, "Month", "Visits", "#2563eb"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c4:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Report Status Split</div><div class="chart-subtitle">Submitted, pending and technical NA summary</div></div><div class="legend-pill">STATUS</div></div>', unsafe_allow_html=True)
            status_data = filtered["Status"].value_counts().reset_index()
            status_data.columns = ["Status", "Count"]
            st.plotly_chart(donut_fig(status_data, "Status", "Count"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        c5, c6 = st.columns(2)
        with c5:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Top Sites</div><div class="chart-subtitle">Sites with highest visit frequency</div></div><div class="legend-pill">TOP 10</div></div>', unsafe_allow_html=True)
            if site_col:
                site_data = filtered[site_col].value_counts().head(10).reset_index()
                site_data.columns = ["Site", "Visits"]
                st.plotly_chart(bar_fig(site_data, "Site", "Visits", "#10b981", horizontal=True), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c6:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Technical NA / Pending Control</div><div class="chart-subtitle">Focus area for report closure</div></div><div class="legend-pill">ACTION</div></div>', unsafe_allow_html=True)
            action_data = filtered[filtered["Status"].isin(["Pending", "Technical NA"])]
            if site_col and not action_data.empty:
                action_site = action_data[site_col].value_counts().head(10).reset_index()
                action_site.columns = ["Site", "Open Items"]
                st.plotly_chart(bar_fig(action_site, "Site", "Open Items", "#f59e0b", horizontal=True), use_container_width=True)
            else:
                st.success("No pending action items for selected filter.")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Visit Records</div><div class="chart-subtitle">Clean filtered table for daily review and reporting</div></div></div>', unsafe_allow_html=True)
        cols = ["Source Sheet", "Visit ID", site_col, tower_col, associate_col, date_col, "Status", "Report Submitted Date", "FloorsVisited", "Floors Visited", "Comment"]
        display_cols = []
        for c in cols:
            if c and c in filtered.columns and c not in display_cols:
                display_cols.append(c)
        st.dataframe(filtered[display_cols].astype(str), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download Filtered Visit Data", filtered.astype(str).to_csv(index=False).encode("utf-8"), "filtered_visit_data.csv", "text/csv", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# TAB 2: MASTER DASHBOARD
# =========================================================
with tab_master:
    if master_df.empty:
        st.warning("No master data found in Google Sheets.")
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

        st.markdown('<div class="filter-panel"><div class="panel-title">Master Project Filters</div><div class="panel-subtitle">Use these filters for state, city, technical person and sales person analysis.</div>', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            m_state = st.selectbox("State", clean_options(master[col_state]), key="m_state") if col_state else "All"
        with m2:
            m_city = st.selectbox("District / City", clean_options(master[col_city]), key="m_city") if col_city else "All"
        with m3:
            m_status = st.selectbox("Project Status", clean_options(master[col_status]), key="m_status") if col_status else "All"
        with m4:
            m_tech = st.selectbox("Technical Person", clean_options(master[col_tech]), key="m_tech") if col_tech else "All"
        with m5:
            m_sales = st.selectbox("Sales Person", clean_options(master[col_sales]), key="m_sales") if col_sales else "All"
        m_search = st.text_input("Search project, distributor, city, state or person", key="master_search")
        st.markdown('</div>', unsafe_allow_html=True)

        mf = master.copy()
        mf = filter_exact(mf, col_state, m_state)
        mf = filter_exact(mf, col_city, m_city)
        mf = filter_exact(mf, col_status, m_status)
        mf = filter_exact(mf, col_tech, m_tech)
        mf = filter_exact(mf, col_sales, m_sales)

        if m_search:
            mask = mf.astype(str).apply(lambda r: r.str.contains(m_search, case=False, na=False).any(), axis=1)
            mf = mf[mask]

        total_projects = len(mf)
        active_projects = 0
        if col_ongoing:
            active_projects = len(mf[mf[col_ongoing].astype(str).str.lower().str.strip().isin(["yes", "y", "ongoing", "active"])])
        states = mf[col_state].nunique() if col_state else 0
        cities = mf[col_city].nunique() if col_city else 0

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(metric_card("Total Projects", total_projects, "▤", "blue", "Master project count", watermark="01"), unsafe_allow_html=True)
        with p2:
            st.markdown(metric_card("Active Visits", active_projects, "●", "green", "Ongoing visit projects", watermark="02"), unsafe_allow_html=True)
        with p3:
            st.markdown(metric_card("States Covered", states, "⌖", "purple", "State coverage", watermark="03"), unsafe_allow_html=True)
        with p4:
            st.markdown(metric_card("Cities Covered", cities, "◈", "orange", "District or city coverage", watermark="04"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        a, b = st.columns(2)
        with a:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Projects by State</div><div class="chart-subtitle">State-wise distribution from master data</div></div><div class="legend-pill">STATE</div></div>', unsafe_allow_html=True)
            if col_state:
                data = mf[col_state].value_counts().reset_index()
                data.columns = ["State", "Projects"]
                st.plotly_chart(bar_fig(data, "State", "Projects", "#2563eb"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with b:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Project Status</div><div class="chart-subtitle">Status-wise project split</div></div><div class="legend-pill">STATUS</div></div>', unsafe_allow_html=True)
            if col_status:
                data = mf[col_status].value_counts().reset_index()
                data.columns = ["Status", "Projects"]
                st.plotly_chart(donut_fig(data, "Status", "Projects"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        c, d = st.columns(2)
        with c:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Technical Person Workload</div><div class="chart-subtitle">Project allocation by technical team</div></div><div class="legend-pill">TECH</div></div>', unsafe_allow_html=True)
            if col_tech:
                data = mf[col_tech].value_counts().head(10).reset_index()
                data.columns = ["Technical Person", "Projects"]
                st.plotly_chart(bar_fig(data, "Technical Person", "Projects", "#10b981", horizontal=True), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with d:
            st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Sales Person Workload</div><div class="chart-subtitle">Project allocation by sales team</div></div><div class="legend-pill">SALES</div></div>', unsafe_allow_html=True)
            if col_sales:
                data = mf[col_sales].value_counts().head(10).reset_index()
                data.columns = ["Sales Person", "Projects"]
                st.plotly_chart(bar_fig(data, "Sales Person", "Projects", "#f59e0b", horizontal=True), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Master Project Directory</div><div class="chart-subtitle">Filtered master project list</div></div></div>', unsafe_allow_html=True)
        st.dataframe(mf.astype(str), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download Master Data", mf.astype(str).to_csv(index=False).encode("utf-8"), "filtered_master_data.csv", "text/csv", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# TAB 3: DATA TABLES
# =========================================================
with tab_data:
    st.markdown('<div class="chart-card"><div class="chart-header"><div class="chart-title-wrap"><div class="chart-title">Raw Data Preview</div><div class="chart-subtitle">Original Google Sheet data loaded into dashboard</div></div></div>', unsafe_allow_html=True)

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("### Visit Data")
        st.caption(f"Rows: {len(visits_df)} | Columns: {len(visits_df.columns)}")
        st.dataframe(visits_df.astype(str), use_container_width=True, hide_index=True)
    with t2:
        st.markdown("### Master Data")
        st.caption(f"Rows: {len(master_df)} | Columns: {len(master_df.columns)}")
        st.dataframe(master_df.astype(str), use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)
