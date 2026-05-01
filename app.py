import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import requests
from io import StringIO

st.set_page_config(
    page_title="Site Visit Dashboard",
    page_icon="📊",
    layout="wide"
)

# ---------------- CONFIG ----------------
SPREADSHEET_ID = st.secrets["GOOGLE_SHEET_ID"]
API_KEY = st.secrets["GOOGLE_API_KEY"]

SHEETS = {
    "VisitLog": "VisitLog",
    "ProjectConfigStatus": "ProjectConfigStatus",
    "MasterProject": "MasterProject",
}

# ---------------- STYLE ----------------
st.markdown("""
<style>
.main {background-color:#ffffff;}
.block-container {padding-top:1.5rem;}
.header {
    background:#0b5ed7;
    padding:18px;
    border-radius:12px;
    color:white;
    margin-bottom:20px;
}
.kpi-card {
    background:#f8f9fa;
    padding:18px;
    border-radius:12px;
    border-left:5px solid #0b5ed7;
}
.red {color:#dc3545;font-weight:700;}
.orange {color:#fd7e14;font-weight:700;}
.yellow {color:#ffc107;font-weight:700;}
.green {color:#198754;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ---------------- LOAD GOOGLE SHEET ----------------
@st.cache_data(ttl=300)
def load_sheet(sheet_name):
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{SPREADSHEET_ID}/values/{sheet_name}?key={API_KEY}"
    )
    response = requests.get(url)

    if response.status_code != 200:
        st.error(f"Cannot load sheet: {sheet_name}")
        st.write(response.text)
        return pd.DataFrame()

    values = response.json().get("values", [])
    if not values:
        return pd.DataFrame()

    headers = values[0]
    rows = values[1:]

    df = pd.DataFrame(rows, columns=headers)

    return df


def clean_date(series):
    return pd.to_datetime(series, errors="coerce").dt.date


def find_col(df, possible_names):
    cols = {c.strip().lower(): c for c in df.columns}
    for name in possible_names:
        if name.lower() in cols:
            return cols[name.lower()]
    return None


visit = load_sheet("VisitLog")
project = load_sheet("ProjectConfigStatus")
master = load_sheet("MasterProject")

# ---------------- COLUMN DETECTION ----------------
visit_date_col = find_col(visit, ["Date of Visit", "Visit Date", "Date"])
site_col = find_col(visit, ["Site Name", "Project Name", "Site"])
tower_col = find_col(visit, ["Tower Name", "Tower"])
associate_col = find_col(visit, ["Associate Name", "Associate ID", "Associate"])
floors_col = find_col(visit, ["Floors Visited", "Submitted Floors", "Floor"])
report_visit_col = find_col(visit, ["Is Report Visit?", "Report Visit", "Is Report Visit"])
report_submitted_col = find_col(visit, ["Report Submitted Date", "Submitted Date"])
comment_col = find_col(visit, ["Comment", "Comments", "Remark", "Remarks"])

next_due_col = find_col(project, ["Next Due Date", "Due Date"])
days_until_due_col = find_col(project, ["Days Until Due"])
project_status_col = find_col(project, ["Project Status", "Status"])
project_site_col = find_col(project, ["Site Name", "Project Name", "Site"])
created_col = find_col(project, ["CreatedAt", "Created At"])

state_col = find_col(master, ["State"])
city_col = find_col(master, ["City"])
master_site_col = find_col(master, ["Site Name", "Project Name", "Site"])

today = date.today()

# ---------------- PREPARE DATA ----------------
if not visit.empty and visit_date_col:
    visit[visit_date_col] = clean_date(visit[visit_date_col])

if not project.empty and next_due_col:
    project[next_due_col] = clean_date(project[next_due_col])

if not project.empty and created_col:
    project[created_col] = clean_date(project[created_col])

if not project.empty and next_due_col:
    project["Days Until Due Auto"] = (
        pd.to_datetime(project[next_due_col], errors="coerce").dt.date - today
    ).apply(lambda x: x.days if pd.notnull(x) else None)

if days_until_due_col and days_until_due_col in project.columns:
    project["Days Until Due Final"] = pd.to_numeric(project[days_until_due_col], errors="coerce")
else:
    project["Days Until Due Final"] = project.get("Days Until Due Auto")

# ---------------- MERGE DATA ----------------
today_visits = visit.copy()

if visit_date_col:
    today_visits = today_visits[today_visits[visit_date_col] == today]

if site_col and project_site_col and not today_visits.empty:
    today_visits = today_visits.merge(
        project,
        left_on=site_col,
        right_on=project_site_col,
        how="left",
        suffixes=("", "_project")
    )

if site_col and master_site_col and not today_visits.empty:
    today_visits = today_visits.merge(
        master,
        left_on=site_col,
        right_on=master_site_col,
        how="left",
        suffixes=("", "_master")
    )

# ---------------- HEADER ----------------
st.markdown("""
<div class="header">
<h1>📊 Site Visit Deep Analytics</h1>
<p>Live data synchronized directly from Google Sheets</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Visit Analytics", "📋 Master Projects"])

# ---------------- TAB 1 ----------------
with tab1:
    st.subheader("Data Filters")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        date_filter = st.date_input("Date", today)

    filtered = visit.copy()
    if visit_date_col:
        filtered = filtered[filtered[visit_date_col] == date_filter]

    with c2:
        associate_options = ["All"]
        if associate_col:
            associate_options += sorted(filtered[associate_col].dropna().unique().tolist())
        selected_associate = st.selectbox("Associate", associate_options)

    with c3:
        site_options = ["All"]
        if site_col:
            site_options += sorted(filtered[site_col].dropna().unique().tolist())
        selected_site = st.selectbox("Site Name", site_options)

    with c4:
        status_options = ["All"]
        if project_status_col and project_status_col in filtered.columns:
            status_options += sorted(filtered[project_status_col].dropna().unique().tolist())
        selected_status = st.selectbox("Project Status", status_options)

    with c5:
        report_options = ["All", "Submitted", "Pending"]
        selected_report = st.selectbox("Report Status", report_options)

    if selected_associate != "All" and associate_col:
        filtered = filtered[filtered[associate_col] == selected_associate]

    if selected_site != "All" and site_col:
        filtered = filtered[filtered[site_col] == selected_site]

    # ---------------- KPI ----------------
    total_projects = len(project)
    projects_visited_today = today_visits[site_col].nunique() if site_col and not today_visits.empty else 0
    total_visits_today = len(today_visits)

    pending_reports = 0
    submitted_reports = 0

    if report_submitted_col and report_submitted_col in today_visits.columns:
        pending_reports = today_visits[report_submitted_col].replace("", pd.NA).isna().sum()
        submitted_reports = today_visits[report_submitted_col].replace("", pd.NA).notna().sum()

    overdue_projects = 0
    due_today = 0
    due_next_2 = 0

    if "Days Until Due Final" in project.columns:
        overdue_projects = (project["Days Until Due Final"] < 0).sum()
        due_today = (project["Days Until Due Final"] == 0).sum()
        due_next_2 = project["Days Until Due Final"].between(1, 2).sum()

    active_projects = 0
    completed_projects = 0

    if project_status_col:
        active_projects = project[project_status_col].astype(str).str.contains("active", case=False, na=False).sum()
        completed_projects = project[project_status_col].astype(str).str.contains("complete", case=False, na=False).sum()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Projects", total_projects)
    k2.metric("Projects Visited Today", projects_visited_today)
    k3.metric("Total Visits Today", total_visits_today)
    k4.metric("Pending Reports", pending_reports)
    k5.metric("Submitted Reports", submitted_reports)

    k6, k7, k8, k9, k10 = st.columns(5)
    k6.metric("Overdue Projects", overdue_projects)
    k7.metric("Due Today", due_today)
    k8.metric("Due in Next 2 Days", due_next_2)
    k9.metric("Active Projects", active_projects)
    k10.metric("Completed Projects", completed_projects)

    st.divider()

    # ---------------- ALERTS ----------------
    st.subheader("Alerts")

    a1, a2, a3, a4 = st.columns(4)
    a1.markdown(f"<p class='red'>Overdue Projects: {overdue_projects}</p>", unsafe_allow_html=True)
    a2.markdown(f"<p class='orange'>Due Today: {due_today}</p>", unsafe_allow_html=True)
    a3.markdown(f"<p class='yellow'>Due in 2 Days: {due_next_2}</p>", unsafe_allow_html=True)
    a4.markdown(f"<p class='red'>Pending Reports: {pending_reports}</p>", unsafe_allow_html=True)

    st.divider()

    # ---------------- TODAY TABLE ----------------
    st.subheader("Today’s Work Table")

    table_cols = []
    for col in [
        site_col,
        tower_col,
        associate_col,
        visit_date_col,
        floors_col,
        report_visit_col,
        comment_col,
        next_due_col,
        "Days Until Due Final",
        project_status_col,
    ]:
        if col and col in today_visits.columns and col not in table_cols:
            table_cols.append(col)

    if not today_visits.empty and table_cols:
        st.dataframe(today_visits[table_cols], use_container_width=True, height=350)
    else:
        st.info("No records found for today.")

    st.divider()

    # ---------------- CHARTS ----------------
    st.subheader("Work Status Charts")

    c1, c2 = st.columns(2)

    with c1:
        if associate_col and not filtered.empty:
            chart = filtered[associate_col].value_counts().reset_index()
            chart.columns = ["Associate", "Visits"]
            fig = px.bar(chart, x="Associate", y="Visits", title="Visits Today by Associate")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if site_col and not filtered.empty:
            chart = filtered[site_col].value_counts().head(10).reset_index()
            chart.columns = ["Site", "Visits"]
            fig = px.bar(chart, x="Site", y="Visits", title="Visits Today by Site")
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        if project_status_col and not project.empty:
            chart = project[project_status_col].value_counts().reset_index()
            chart.columns = ["Status", "Count"]
            fig = px.pie(chart, names="Status", values="Count", title="Projects by Status")
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        if "Days Until Due Final" in project.columns:
            status_data = {
                "Status": ["Overdue", "Due Soon", "On Track"],
                "Count": [
                    (project["Days Until Due Final"] < 0).sum(),
                    project["Days Until Due Final"].between(0, 2).sum(),
                    (project["Days Until Due Final"] > 2).sum(),
                ],
            }
            fig = px.bar(pd.DataFrame(status_data), x="Status", y="Count", title="Overdue vs Due Soon vs On Track")
            st.plotly_chart(fig, use_container_width=True)

    c5, c6 = st.columns(2)

    with c5:
        report_data = pd.DataFrame({
            "Report Status": ["Submitted", "Pending"],
            "Count": [submitted_reports, pending_reports]
        })
        fig = px.pie(report_data, names="Report Status", values="Count", title="Report Submitted vs Not Submitted")
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        if tower_col and not filtered.empty:
            chart = filtered[tower_col].value_counts().head(10).reset_index()
            chart.columns = ["Tower", "Visits"]
            fig = px.bar(chart, x="Tower", y="Visits", title="Today’s Visits by Tower")
            st.plotly_chart(fig, use_container_width=True)

# ---------------- TAB 2 ----------------
with tab2:
    st.subheader("Master Project Data")

    if not master.empty:
        st.dataframe(master, use_container_width=True, height=500)
    else:
        st.info("MasterProject sheet not found or empty.")

    st.subheader("Project Configuration Status")

    if not project.empty:
        st.dataframe(project, use_container_width=True, height=500)
    else:
        st.info("ProjectConfigStatus sheet not found or empty.")
