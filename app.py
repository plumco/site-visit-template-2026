import re
from datetime import date
from io import BytesIO
from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Site Visit Live Dashboard", page_icon="🏗️", layout="wide")

SHEETS = ["ProjectConfigStatus", "VisitLog", "MasterProject", "Settings"]
TODAY = pd.Timestamp(date.today()).normalize()

st.markdown(
    """
    <style>
    .main {background:#ffffff;}
    .top-header {background:#0B5CAB;color:white;padding:18px 24px;border-radius:16px;margin-bottom:14px;}
    .top-header h1 {margin:0;font-size:30px;}
    .top-header p {margin:4px 0 0 0;font-size:14px;opacity:.95;}
    .kpi-card {background:#F8FAFC;border:1px solid #E5E7EB;border-radius:16px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.05);}
    .kpi-title {font-size:13px;color:#64748B;margin-bottom:6px;}
    .kpi-value {font-size:28px;font-weight:800;color:#0F172A;}
    .section-title {font-size:20px;font-weight:800;margin:18px 0 8px;color:#0F172A;}
    .red {background:#FEE2E2;color:#991B1B;padding:4px 8px;border-radius:999px;font-weight:700;}
    .orange {background:#FFEDD5;color:#9A3412;padding:4px 8px;border-radius:999px;font-weight:700;}
    .yellow {background:#FEF9C3;color:#854D0E;padding:4px 8px;border-radius:999px;font-weight:700;}
    .green {background:#DCFCE7;color:#166534;padding:4px 8px;border-radius:999px;font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True,
)


def clean_col(c):
    c = "" if c is None else str(c).strip()
    c = re.sub(r"\s+", " ", c)
    return c


def to_date(series):
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def to_bool(series):
    return series.astype(str).str.strip().str.lower().isin(["yes", "y", "true", "1", "report", "report visit"])


def get_secret(section, key, default=""):
    try:
        return st.secrets.get(section, {}).get(key, default)
    except Exception:
        return default


@st.cache_data(ttl=300, show_spinner=False)
def read_google_sheet(sheet_name: str, spreadsheet_id: str, api_key: str) -> pd.DataFrame:
    if not spreadsheet_id:
        raise ValueError("Missing Google spreadsheet_id. Add it in Streamlit secrets or sidebar.")

    if api_key:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{quote(sheet_name)}?key={api_key}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        values = r.json().get("values", [])
        if not values:
            return pd.DataFrame()
        header = [clean_col(x) for x in values[0]]
        rows = values[1:]
        width = len(header)
        rows = [row + [""] * (width - len(row)) if len(row) < width else row[:width] for row in rows]
        df = pd.DataFrame(rows, columns=header)
    else:
        # Works when the file is shared publicly or published to web.
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"
        df = pd.read_csv(url)
        df.columns = [clean_col(c) for c in df.columns]

    df = df.loc[:, [c for c in df.columns if c and not str(c).startswith("Unnamed")]]
    return df


@st.cache_data(ttl=300, show_spinner=False)
def read_excel_upload(file_bytes: bytes) -> dict:
    return pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=str)


def load_data():
    sidebar_id = st.sidebar.text_input("Google Spreadsheet ID", value=get_secret("google", "spreadsheet_id", ""), type="password")
    sidebar_key = st.sidebar.text_input("Google API Key", value=get_secret("google", "api_key", ""), type="password")
    uploaded = st.sidebar.file_uploader("Optional local Excel test file", type=["xlsx"])

    if uploaded is not None:
        all_sheets = read_excel_upload(uploaded.getvalue())
        return {name: all_sheets.get(name, pd.DataFrame()).copy() for name in SHEETS}

    data = {}
    for sheet in SHEETS:
        data[sheet] = read_google_sheet(sheet, sidebar_id, sidebar_key)
    return data


def prepare_data(data):
    pc = data.get("ProjectConfigStatus", pd.DataFrame()).copy()
    vl = data.get("VisitLog", pd.DataFrame()).copy()
    mp = data.get("MasterProject", pd.DataFrame()).copy()

    for df in [pc, vl, mp]:
        df.columns = [clean_col(c) for c in df.columns]

    # Project config status
    for col in ["Next Due Date", "Last Visit Date"]:
        if col in pc:
            pc[col] = to_date(pc[col])
    if "Days Until Due" in pc:
        pc["Days Until Due"] = pd.to_numeric(pc["Days Until Due"], errors="coerce")
    elif "Next Due Date" in pc:
        pc["Days Until Due"] = (pc["Next Due Date"] - TODAY).dt.days
    else:
        pc["Days Until Due"] = np.nan

    # Visit log
    for col in ["Date of Visit", "CreatedAt", "Report Submitted Date"]:
        if col in vl:
            vl[col] = to_date(vl[col])
    if "Is Report Visit?" in vl:
        vl["Is Report Visit? Bool"] = to_bool(vl["Is Report Visit?"])
    else:
        vl["Is Report Visit? Bool"] = False

    # Master project enrichment
    if not mp.empty:
        rename_map = {
            "PROJECT": "Site Name",
            "STATE": "State",
            "DISTRICT / CITY": "City",
            "STATUS OF PROJECT": "Master Status",
        }
        mp = mp.rename(columns={k: v for k, v in rename_map.items() if k in mp.columns})
        keep = [c for c in ["Site Name", "State", "City", "Master Status"] if c in mp.columns]
        mp = mp[keep].drop_duplicates(subset=["Site Name"]) if "Site Name" in keep else pd.DataFrame()

    if not pc.empty and not mp.empty and "Site Name" in pc.columns:
        pc = pc.merge(mp, on="Site Name", how="left")
    if not vl.empty and not mp.empty and "Site Name" in vl.columns:
        vl = vl.merge(mp, on="Site Name", how="left")

    return pc, vl, mp


def today_work(pc, vl):
    parts = []
    if not vl.empty:
        tv = vl.copy()
        mask = pd.Series(False, index=tv.index)
        if "Date of Visit" in tv:
            mask |= tv["Date of Visit"].eq(TODAY)
        if "CreatedAt" in tv:
            mask |= tv["CreatedAt"].eq(TODAY)
        if "Report Submitted Date" in tv and "Date of Visit" in tv:
            mask |= tv["Date of Visit"].eq(TODAY) & tv["Report Submitted Date"].isna()
        tv = tv[mask].copy()
        if not tv.empty:
            cols = ["Site Name", "Tower Name", "Associate ID", "Date of Visit", "FloorsVisited", "Is Report Visit?", "Comment", "State", "City"]
            tv = tv[[c for c in cols if c in tv.columns]]
            parts.append(tv)

    base = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    if not pc.empty:
        due = pc.copy()
        mask = pd.Series(False, index=due.index)
        if "Next Due Date" in due:
            mask |= due["Next Due Date"].eq(TODAY)
        if "Days Until Due" in due:
            mask |= due["Days Until Due"].le(2)
        due = due[mask].copy()
        if not due.empty:
            cols = ["Site Name", "Tower Name", "Assignee", "Next Due Date", "Days Until Due", "Project Status", "State", "City"]
            due = due[[c for c in cols if c in due.columns]]
            due = due.rename(columns={"Assignee": "Associate ID"})
            base = pd.concat([base, due], ignore_index=True)

    if base.empty:
        return base

    # Enrich today rows with project status/due date.
    enrich_cols = [c for c in ["Site Name", "Tower Name", "Next Due Date", "Days Until Due", "Project Status"] if c in pc.columns]
    if "Site Name" in base.columns and enrich_cols:
        key_cols = ["Site Name"] + (["Tower Name"] if "Tower Name" in pc.columns and "Tower Name" in base.columns else [])
        enrich = pc[enrich_cols].drop_duplicates(subset=key_cols)
        base = base.merge(enrich, on=key_cols, how="left", suffixes=("", "_pc"))
        for c in ["Next Due Date", "Days Until Due", "Project Status"]:
            alt = f"{c}_pc"
            if alt in base.columns:
                if c in base.columns:
                    base[c] = base[c].combine_first(base[alt])
                else:
                    base[c] = base[alt]
                base.drop(columns=[alt], inplace=True)

    desired = ["Site Name", "Tower Name", "Associate ID", "Date of Visit", "FloorsVisited", "Is Report Visit?", "Comment", "Next Due Date", "Days Until Due", "Project Status", "State", "City"]
    for c in desired:
        if c not in base.columns:
            base[c] = np.nan
    return base[desired].drop_duplicates().reset_index(drop=True)


def status_bucket(days):
    if pd.isna(days):
        return "On-track"
    if days < 0:
        return "Overdue"
    if days == 0:
        return "Due today"
    if days <= 2:
        return "Due in next 2 days"
    return "On-track"


def metric_card(title, value):
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{title}</div><div class='kpi-value'>{value}</div></div>", unsafe_allow_html=True)


def filter_df(df):
    if df.empty:
        return df
    with st.sidebar:
        st.header("Filters")
        date_filter = st.date_input("Date", value=date.today())
        assoc_options = sorted([x for x in df.get("Associate ID", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
        site_options = sorted([x for x in df.get("Site Name", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
        status_options = sorted([x for x in df.get("Project Status", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
        state_options = sorted([x for x in df.get("State", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
        city_options = sorted([x for x in df.get("City", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
        report_options = ["All", "Report visit", "Not report visit"]

        assoc = st.multiselect("Associate", assoc_options)
        site = st.multiselect("Site Name", site_options)
        status = st.multiselect("Project Status", status_options)
        report_status = st.selectbox("Report status", report_options)
        state = st.multiselect("State", state_options)
        city = st.multiselect("City", city_options)

    out = df.copy()
    selected_date = pd.Timestamp(date_filter).normalize()
    if "Date of Visit" in out.columns:
        out = out[out["Date of Visit"].isna() | out["Date of Visit"].eq(selected_date) | out["Next Due Date"].eq(selected_date) | out["Days Until Due"].le(2)]
    if assoc:
        out = out[out["Associate ID"].astype(str).isin(assoc)]
    if site:
        out = out[out["Site Name"].astype(str).isin(site)]
    if status:
        out = out[out["Project Status"].astype(str).isin(status)]
    if state:
        out = out[out["State"].astype(str).isin(state)]
    if city:
        out = out[out["City"].astype(str).isin(city)]
    if report_status != "All" and "Is Report Visit?" in out.columns:
        bool_col = to_bool(out["Is Report Visit?"])
        out = out[bool_col] if report_status == "Report visit" else out[~bool_col]
    return out


try:
    st.markdown("<div class='top-header'><h1>Site Visit Live Dashboard</h1><p>Daily site review, report tracking, due follow-up and project status monitoring</p></div>", unsafe_allow_html=True)
    data = load_data()
    pc, vl, mp = prepare_data(data)
    tw = today_work(pc, vl)
    tw = filter_df(tw)

    # KPI calculations
    visits_today = vl[vl.get("Date of Visit", pd.Series(dtype="datetime64[ns]")).eq(TODAY)] if not vl.empty and "Date of Visit" in vl else pd.DataFrame()
    projects_visited_today = visits_today.get("Site Name", pd.Series(dtype=str)).nunique() if not visits_today.empty else 0
    total_visits_today = len(visits_today)
    report_visits_today = int(visits_today.get("Is Report Visit? Bool", pd.Series(dtype=bool)).sum()) if not visits_today.empty else 0
    pending_reports = 0
    if not visits_today.empty and "Report Submitted Date" in visits_today:
        pending_reports = int(visits_today["Report Submitted Date"].isna().sum())
    overdue_projects = int((pc.get("Days Until Due", pd.Series(dtype=float)) < 0).sum()) if not pc.empty else 0
    due_today = int((pc.get("Days Until Due", pd.Series(dtype=float)) == 0).sum()) if not pc.empty else 0
    due_next_2 = int(pc.get("Days Until Due", pd.Series(dtype=float)).between(1, 2, inclusive="both").sum()) if not pc.empty else 0
    project_status = pc.get("Project Status", pd.Series(dtype=str)).astype(str).str.lower() if not pc.empty else pd.Series(dtype=str)
    active_projects = int(project_status.str.contains("active|ongoing|in progress|progress", na=False).sum())
    completed_projects = int(project_status.str.contains("complete|completed|closed|done", na=False).sum())

    kpis = [
        ("Total projects", pc.get("Site Name", pd.Series(dtype=str)).nunique() if not pc.empty else 0),
        ("Projects visited today", projects_visited_today),
        ("Total visits today", total_visits_today),
        ("Report visits today", report_visits_today),
        ("Pending reports", pending_reports),
        ("Overdue projects", overdue_projects),
        ("Due today", due_today),
        ("Due in next 2 days", due_next_2),
        ("Active projects", active_projects),
        ("Completed projects", completed_projects),
    ]

    for row in [kpis[:5], kpis[5:]]:
        cols = st.columns(5)
        for col, (title, value) in zip(cols, row):
            with col:
                metric_card(title, value)

    st.markdown("<div class='section-title'>Alerts</div>", unsafe_allow_html=True)
    a1, a2, a3, a4, a5 = st.columns(5)
    a1.markdown(f"<span class='red'>Overdue: {overdue_projects}</span>", unsafe_allow_html=True)
    a2.markdown(f"<span class='orange'>Due today: {due_today}</span>", unsafe_allow_html=True)
    a3.markdown(f"<span class='yellow'>Due ≤ 2 days: {due_next_2}</span>", unsafe_allow_html=True)
    a4.markdown(f"<span class='green'>Completed: {completed_projects}</span>", unsafe_allow_html=True)
    a5.markdown(f"<span class='red'>Pending reports: {pending_reports}</span>", unsafe_allow_html=True)

    left, right = st.columns([1.55, 1])
    with left:
        st.markdown("<div class='section-title'>Today's work table</div>", unsafe_allow_html=True)
        display = tw.copy()
        for c in ["Date of Visit", "Next Due Date"]:
            if c in display:
                display[c] = pd.to_datetime(display[c], errors="coerce").dt.strftime("%d-%m-%Y").replace("NaT", "")
        st.dataframe(display, use_container_width=True, hide_index=True)

    with right:
        st.markdown("<div class='section-title'>Work status charts</div>", unsafe_allow_html=True)
        if not visits_today.empty and "Associate ID" in visits_today:
            st.plotly_chart(px.bar(visits_today.groupby("Associate ID", dropna=False).size().reset_index(name="Visits"), x="Associate ID", y="Visits", title="Visits today by associate"), use_container_width=True)
        if not visits_today.empty and "Site Name" in visits_today:
            st.plotly_chart(px.bar(visits_today.groupby("Site Name", dropna=False).size().reset_index(name="Visits"), x="Site Name", y="Visits", title="Visits today by site"), use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if not pc.empty and "Project Status" in pc:
            st.plotly_chart(px.pie(pc.groupby("Project Status", dropna=False).size().reset_index(name="Projects"), names="Project Status", values="Projects", title="Projects by status"), use_container_width=True)
    with c2:
        if not pc.empty and "Days Until Due" in pc:
            temp = pc.copy()
            temp["Due Bucket"] = temp["Days Until Due"].apply(status_bucket)
            st.plotly_chart(px.pie(temp.groupby("Due Bucket").size().reset_index(name="Projects"), names="Due Bucket", values="Projects", title="Overdue vs due soon vs on-track"), use_container_width=True)
    with c3:
        if not visits_today.empty and "Report Submitted Date" in visits_today:
            temp = visits_today.copy()
            temp["Report Status"] = np.where(temp["Report Submitted Date"].notna(), "Submitted", "Not submitted")
            st.plotly_chart(px.pie(temp.groupby("Report Status").size().reset_index(name="Visits"), names="Report Status", values="Visits", title="Report submitted vs not submitted"), use_container_width=True)
    with c4:
        if not visits_today.empty and "Tower Name" in visits_today:
            st.plotly_chart(px.bar(visits_today.groupby("Tower Name", dropna=False).size().reset_index(name="Visits"), x="Tower Name", y="Visits", title="Today's visits by tower"), use_container_width=True)

    st.caption("Data refreshes automatically every 5 minutes. Use the top-right Streamlit rerun button for instant refresh after editing Google Sheets.")

except Exception as e:
    st.error("Dashboard could not load. Check Spreadsheet ID, API key, sheet sharing permission, and exact sheet names.")
    st.exception(e)
