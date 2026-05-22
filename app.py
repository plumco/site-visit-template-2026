import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from html import escape

# =========================================================
# 1. PAGE CONFIG
# =========================================================
st.set_page_config(
    layout="wide",
    page_title="Site Visit Deep Analytics",
    page_icon="📊"
)

# =========================================================
# 2. CSS
# =========================================================
st.markdown("""
<style>
    .main-title {
        font-size: 44px;
        font-weight: 800;
        margin-bottom: 0px;
    }

    .sub-title {
        font-size: 16px;
        color: #d1d5db;
        margin-bottom: 25px;
    }

    div[data-testid="metric-container"] {
        background-color: transparent;
        border: 0px;
        padding: 0.5rem 0rem;
    }

    .site-card {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        border: 1px solid #374151;
        border-radius: 18px;
        padding: 24px;
        margin-top: 15px;
        margin-bottom: 20px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.35);
    }

    .site-name {
        font-size: 34px;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 5px;
    }

    .site-meta {
        font-size: 15px;
        color: #d1d5db;
        margin-bottom: 12px;
    }

    .info-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin-top: 18px;
    }

    .info-box {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 14px;
    }

    .info-label {
        font-size: 12px;
        color: #94a3b8;
        margin-bottom: 5px;
    }

    .info-value {
        font-size: 16px;
        font-weight: 700;
        color: #ffffff;
        word-break: break-word;
    }

    .section-card {
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 16px;
        padding: 18px;
        margin-top: 16px;
        margin-bottom: 18px;
    }

    .section-title {
        font-size: 22px;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 12px;
    }

    .small-note {
        font-size: 13px;
        color: #9ca3af;
    }

    .highlight-card {
        padding: 20px;
        border-radius: 12px;
        text-align: left;
        font-family: sans-serif;
        font-weight: bold;
        margin-top: 10px;
    }

    .card-blue  { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .card-green { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .card-red   { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
    .card-title { font-size: 0.9rem; margin-bottom: 5px; opacity: 0.8; }
    .card-value { font-size: 1.2rem; }

    @media screen and (max-width: 1200px) {
        .info-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    @media screen and (max-width: 700px) {
        .info-grid {
            grid-template-columns: repeat(1, 1fr);
        }
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. GOOGLE SHEETS CONNECTION
# =========================================================
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

SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"


# =========================================================
# 4. HELPER FUNCTIONS
# =========================================================
def make_unique_headers(raw_headers):
    headers = []
    seen = {}

    for h in raw_headers:
        h = str(h).strip()

        if h == "" or h.lower() == "nan":
            h = "Blank"

        if h in seen:
            seen[h] += 1
            headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            headers.append(h)

    return headers


def clean_df(df):
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        df[col] = df[col].astype(str).replace({
            "nan": "",
            "None": "",
            "NaT": "",
            "NaN": ""
        }).str.strip()

    return df


def first_existing_column(df, possible_cols):
    for col in possible_cols:
        if col in df.columns:
            return col
    return None


def clean_options(series):
    values = (
        series.astype(str)
        .str.strip()
        .replace(["nan", "None", "NaT", "", "null", "Null"], pd.NA)
        .dropna()
        .unique()
        .tolist()
    )
    return sorted(values)


def parse_floor(val):
    val_str = str(val).strip()

    if not val_str or val_str.lower() in ["nan", "none", "null", "n/a", "-"]:
        return 0

    try:
        return int(float(val_str))
    except Exception:
        return 1


def get_visit_status(row):
    is_report = str(row.get("Is Report Visit?", "")).strip().lower()
    sub_date = str(row.get("Report Submitted Date", "")).strip()

    if is_report in ["no", "false", "n/a", "na"]:
        return "Technical (NA)"

    if sub_date and sub_date.lower() not in ["nan", "none", ""]:
        return "Submitted"

    return "Pending"


def safe_text(value):
    value = str(value).strip()
    if value.lower() in ["nan", "none", "nat", ""]:
        return "-"
    return escape(value)


def info_box(label, value):
    return f"""
    <div class="info-box">
        <div class="info-label">{safe_text(label)}</div>
        <div class="info-value">{safe_text(value)}</div>
    </div>
    """


def find_master_site_column(master_df):
    return first_existing_column(
        master_df,
        [
            "PROJECT",
            "PROJECT NAME",
            "Project",
            "Project Name",
            "Site Name",
            "SITE NAME"
        ]
    )


def find_visit_site_column(visits_df):
    return first_existing_column(
        visits_df,
        [
            "Site Name",
            "SITE NAME",
            "PROJECT",
            "PROJECT NAME",
            "Project Name"
        ]
    )


def filter_by_site(df, site_col, selected_site):
    if df.empty or not site_col:
        return pd.DataFrame()

    return df[
        df[site_col]
        .astype(str)
        .str.strip()
        .str.lower()
        == str(selected_site).strip().lower()
    ].copy()


# =========================================================
# 5. LOAD GOOGLE SHEET DATA
# =========================================================
@st.cache_data(ttl=600)
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Could not open Google Sheet. Please share the sheet with your service account email. Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    worksheets = spreadsheet.worksheets()

    visit_dataframes = []
    master_df = pd.DataFrame()

    for ws in worksheets:
        ws_title = ws.title.strip()
        ws_title_lower = ws_title.lower()

        raw_data = ws.get_all_values()

        if not raw_data or len(raw_data) < 2:
            continue

        headers = make_unique_headers(raw_data[0])
        df = pd.DataFrame(raw_data[1:], columns=headers)
        df = clean_df(df)

        if df.empty:
            continue

        # Master Project sheet
        if ws_title_lower == "masterproject" or "master project" in ws_title_lower:
            master_df = df.copy()
            master_df["Source Sheet"] = ws_title
            continue

        # Visit log only
        if ws_title_lower == "visitlog" or "visit id" in [c.lower() for c in df.columns]:
            df["Source Sheet"] = ws_title
            visit_dataframes.append(df)
            continue

        # Do not include config / setting sheets in visit data
        if any(skip in ws_title_lower for skip in ["setting", "config", "associate", "projectconfigstatus"]):
            continue

    visits_df = pd.concat(visit_dataframes, ignore_index=True) if visit_dataframes else pd.DataFrame()

    visits_df = clean_df(visits_df)
    master_df = clean_df(master_df)

    return visits_df, master_df


# =========================================================
# 6. DATA SESSION
# =========================================================
if "data_loaded" not in st.session_state:
    visits_df, master_df = load_data()
    st.session_state["visits_df"] = visits_df
    st.session_state["master_df"] = master_df
    st.session_state["data_loaded"] = True

visits_df = st.session_state["visits_df"]
master_df = st.session_state["master_df"]

if st.sidebar.button("🔄 Refresh Google Sheet Data"):
    st.cache_data.clear()
    visits_df, master_df = load_data()
    st.session_state["visits_df"] = visits_df
    st.session_state["master_df"] = master_df
    st.session_state["data_loaded"] = True
    st.rerun()


# =========================================================
# 7. COMMON DATA PREPARATION
# =========================================================
if not visits_df.empty:
    visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)

    if "Date of Visit" in visits_df.columns:
        visits_df["Date Parsed"] = pd.to_datetime(visits_df["Date of Visit"], errors="coerce")
        visits_df["Month"] = visits_df["Date Parsed"].dt.strftime("%b %Y")
        visits_df["Month"] = visits_df["Month"].fillna("Unknown")
    else:
        visits_df["Month"] = "Unknown"

    floors_col = first_existing_column(visits_df, ["FloorsVisited", "Floors Visited", "Floor Visited"])
    if floors_col:
        visits_df["Num_Floors"] = visits_df[floors_col].apply(parse_floor)
    else:
        visits_df["Num_Floors"] = 0

    if "Is Report Visit?" in visits_df.columns:
        visits_df["Clean_Report_Mark"] = visits_df["Is Report Visit?"].astype(str).str.strip().str.upper()
    else:
        visits_df["Clean_Report_Mark"] = ""


# =========================================================
# 8. HEADER
# =========================================================
st.markdown('<div class="main-title">📊 Site Visit Deep Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Live data synchronized directly from your Google Sheets.</div>', unsafe_allow_html=True)


# =========================================================
# 9. TABS
# =========================================================
tab_visits, tab_master, tab_exec, tab_site_card = st.tabs([
    "📊 Visit Analytics",
    "📈 Master Projects",
    "👔 Executive Dashboard",
    "🏢 Site Card"
])


# =========================================================
# TAB 1: VISIT ANALYTICS
# =========================================================
with tab_visits:
    if visits_df.empty:
        st.warning("No Visit Log data found.")
    else:
        st.subheader("Data Filters")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            sources = ["All"] + clean_options(visits_df["Source Sheet"])
            f_source = st.selectbox("Source Sheet", sources, key="t1_source")

        with col2:
            months = ["All"] + clean_options(visits_df["Month"])
            f_month = st.selectbox("Month", months, key="t1_month")

        with col3:
            statuses = ["All"] + clean_options(visits_df["Status"])
            f_status = st.selectbox("Status", statuses, key="t1_status")

        with col4:
            assoc_col = first_existing_column(visits_df, ["Associate ID", "Associate", "Technical Person"])
            if assoc_col:
                associates = ["All"] + clean_options(visits_df[assoc_col])
            else:
                associates = ["All"]
            f_assoc = st.selectbox("Associate", associates, key="t1_assoc")

        with col5:
            visit_site_col = find_visit_site_column(visits_df)
            if visit_site_col:
                sites = ["All"] + clean_options(visits_df[visit_site_col])
            else:
                sites = ["All"]
            f_site = st.selectbox("Site Name", sites, key="t1_site")

        filtered_v = visits_df.copy()

        if f_source != "All":
            filtered_v = filtered_v[filtered_v["Source Sheet"].astype(str) == f_source]

        if f_month != "All":
            filtered_v = filtered_v[filtered_v["Month"].astype(str) == f_month]

        if f_status != "All":
            filtered_v = filtered_v[filtered_v["Status"].astype(str) == f_status]

        if assoc_col and f_assoc != "All":
            filtered_v = filtered_v[filtered_v[assoc_col].astype(str) == f_assoc]

        if visit_site_col and f_site != "All":
            filtered_v = filtered_v[filtered_v[visit_site_col].astype(str) == f_site]

        total_visits_floors = int(filtered_v["Num_Floors"].sum())
        pending_count = len(filtered_v[filtered_v["Status"] == "Pending"])
        submitted_count = len(filtered_v[filtered_v["Status"] == "Submitted"])
        tech_na_floors = int(filtered_v[filtered_v["Status"] == "Technical (NA)"]["Num_Floors"].sum())
        submitted_floors_sum = int(filtered_v[filtered_v["Clean_Report_Mark"].isin(["YES", "Y", "TRUE"])]["Num_Floors"].sum())

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

        kpi1.metric("Total Visits", total_visits_floors)
        kpi2.metric("Pending Reports", pending_count)
        kpi3.metric("Technical (NA)", tech_na_floors)
        kpi4.metric("Submitted", submitted_count)
        kpi5.metric("Submitted Floors", submitted_floors_sum)

        st.markdown("---")

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("##### Visits Per Month")
            month_counts = filtered_v["Month"].value_counts().reset_index()
            month_counts.columns = ["Month", "Visits"]
            fig1 = px.bar(month_counts, x="Month", y="Visits")
            st.plotly_chart(fig1, use_container_width=True, key="chart_t1_month")

        with chart_col2:
            st.markdown("##### Top Sites / Zones")
            if visit_site_col:
                site_counts = filtered_v[visit_site_col].value_counts().nlargest(6).reset_index()
                site_counts.columns = ["Site Name", "Visits"]
                fig2 = px.pie(site_counts, names="Site Name", values="Visits", hole=0.4)
                st.plotly_chart(fig2, use_container_width=True, key="chart_t1_pie")
            else:
                st.info("Site Name column not found.")

        st.subheader("Visit Records")

        display_cols = [
            "Source Sheet",
            "Visit ID",
            visit_site_col,
            "Tower Name",
            "FloorsVisited",
            "Floors Visited",
            assoc_col,
            "Date of Visit",
            "Status",
            "Report Submitted Date",
            "Comment"
        ]

        display_cols = []
        for c in [
            "Source Sheet",
            "Visit ID",
            visit_site_col,
            "Tower Name",
            "FloorsVisited",
            "Floors Visited",
            assoc_col,
            "Date of Visit",
            "Status",
            "Report Submitted Date",
            "Comment"
        ]:
            if c and c in filtered_v.columns and c not in display_cols:
                display_cols.append(c)

        st.dataframe(filtered_v[display_cols].astype(str), use_container_width=True, hide_index=True)


# =========================================================
# TAB 2: MASTER PROJECTS
# =========================================================
with tab_master:
    if master_df.empty:
        st.warning("No MasterProject data found.")
    else:
        col_project = find_master_site_column(master_df)
        col_state = first_existing_column(master_df, ["STATE", "State"])
        col_dist = first_existing_column(master_df, ["DISTRICT / CITY", "DISTRICT", "District", "CITY", "City"])
        col_area = first_existing_column(master_df, ["Area", "AREA"])
        col_stat = first_existing_column(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
        col_ong = first_existing_column(master_df, ["VISIT ONGOING", "Visit Ongoing"])
        col_tech = first_existing_column(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
        col_sale = first_existing_column(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
        col_distr = first_existing_column(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])

        st.subheader("Master Filters")

        m_c1, m_c2, m_c3, m_c4, m_c5, m_c6 = st.columns(6)

        filtered_m = master_df.copy()

        if col_state:
            f_state = m_c1.selectbox("State", ["All"] + clean_options(filtered_m[col_state]), key="t2_state")
            if f_state != "All":
                filtered_m = filtered_m[filtered_m[col_state].astype(str) == f_state]

        if col_dist:
            f_dist = m_c2.selectbox("District", ["All"] + clean_options(filtered_m[col_dist]), key="t2_dist")
            if f_dist != "All":
                filtered_m = filtered_m[filtered_m[col_dist].astype(str) == f_dist]

        if col_stat:
            f_stat = m_c3.selectbox("Project Status", ["All"] + clean_options(filtered_m[col_stat]), key="t2_stat")
            if f_stat != "All":
                filtered_m = filtered_m[filtered_m[col_stat].astype(str) == f_stat]

        if col_tech:
            f_tech = m_c4.selectbox("Tech Person", ["All"] + clean_options(filtered_m[col_tech]), key="t2_tech")
            if f_tech != "All":
                filtered_m = filtered_m[filtered_m[col_tech].astype(str) == f_tech]

        if col_sale:
            f_sale = m_c5.selectbox("Sales Person", ["All"] + clean_options(filtered_m[col_sale]), key="t2_sale")
            if f_sale != "All":
                filtered_m = filtered_m[filtered_m[col_sale].astype(str) == f_sale]

        if col_distr:
            f_distr = m_c6.selectbox("Distributor", ["All"] + clean_options(filtered_m[col_distr]), key="t2_distr")
            if f_distr != "All":
                filtered_m = filtered_m[filtered_m[col_distr].astype(str) == f_distr]

        total_proj = len(filtered_m)

        if col_ong:
            active_proj = len(
                filtered_m[
                    filtered_m[col_ong].astype(str).str.lower().isin(["yes", "y", "ongoing"])
                ]
            )
        else:
            active_proj = 0

        unique_states = filtered_m[col_state].nunique() if col_state else 0

        teams_set = set()

        if col_tech:
            teams_set.update(filtered_m[col_tech].dropna().astype(str).tolist())

        if col_sale:
            teams_set.update(filtered_m[col_sale].dropna().astype(str).tolist())

        teams_count = len([
            x for x in teams_set
            if str(x).strip() and str(x).strip().lower() not in ["nan", "none", ""]
        ])

        k1, k2, k3, k4 = st.columns(4)

        k1.metric("Total Projects", total_proj)
        k2.metric("Active Visits", active_proj)
        k3.metric("States Covered", unique_states)
        k4.metric("Tech / Sales Teams", teams_count)

        st.markdown("---")

        m_chart1, m_chart2 = st.columns(2)

        with m_chart1:
            st.markdown("##### Projects by State")
            if col_state:
                state_c = filtered_m[col_state].value_counts().reset_index()
                state_c.columns = ["State", "Count"]
                fig3 = px.bar(state_c, x="State", y="Count")
                st.plotly_chart(fig3, use_container_width=True, key="chart_t2_state")

        with m_chart2:
            st.markdown("##### Project Status")
            if col_stat:
                stat_c = filtered_m[col_stat].value_counts().reset_index()
                stat_c.columns = ["Status", "Count"]
                fig4 = px.pie(stat_c, names="Status", values="Count", hole=0.4)
                st.plotly_chart(fig4, use_container_width=True, key="chart_t2_pie")

        st.subheader("Master Projects Directory")
        st.dataframe(filtered_m.astype(str), use_container_width=True, hide_index=True)


# =========================================================
# TAB 3: EXECUTIVE DASHBOARD
# =========================================================
with tab_exec:
    st.markdown("### Executive Dashboard")
    st.markdown("Multi-month associate performance tracking & field analytics")

    if visits_df.empty:
        st.warning("No Visit Log data found.")
    else:
        e1, e2 = st.columns([4, 1])

        with e2:
            exec_months = ["All"] + clean_options(visits_df["Month"])
            selected_month = st.selectbox("Month", exec_months, label_visibility="collapsed", key="t3_month")

        exec_filtered_df = visits_df.copy()

        if selected_month != "All":
            exec_filtered_df = exec_filtered_df[exec_filtered_df["Month"] == selected_month]

        assoc_col = first_existing_column(exec_filtered_df, ["Associate ID", "Associate", "Technical Person"])

        if not assoc_col:
            st.error("Associate ID column not found.")
        else:
            summary_rows = []

            for assoc, group in exec_filtered_df.groupby(assoc_col):
                if pd.isna(assoc) or str(assoc).strip() == "":
                    continue

                floor_visit_sum = group["Num_Floors"].sum()
                site_tower_count = len(group)

                mask_yes = group["Clean_Report_Mark"].isin(["YES", "Y", "TRUE"])
                mask_no = group["Clean_Report_Mark"].isin(["NO", "N", "FALSE"])

                report_yes_sum = group[mask_yes]["Num_Floors"].sum()
                report_no_sum = group[mask_no]["Num_Floors"].sum()
                report_pending = len(group[group["Status"] == "Pending"])
                client_sent_floors = group[mask_yes]["Num_Floors"].sum()

                summary_rows.append({
                    "Associate ID": assoc,
                    "Floor Visit": int(floor_visit_sum),
                    "Site Tower visit": int(site_tower_count),
                    "Report Mark (YES)": int(report_yes_sum),
                    "Suggestion Visit (NO)": int(report_no_sum),
                    "Report Pending": int(report_pending),
                    "Report sent to the client": int(client_sent_floors),
                    "Report total with Pend": int(client_sent_floors + report_pending)
                })

            summary_df = pd.DataFrame(summary_rows)

            if summary_df.empty:
                st.info("No executive data found.")
            else:
                total_floors = summary_df["Floor Visit"].sum()
                total_sites = summary_df["Site Tower visit"].sum()
                total_sent = summary_df["Report sent to the client"].sum()
                total_pending = summary_df["Report Pending"].sum()

                kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

                kpi_col1.metric("TOTAL FLOOR VISITS", total_floors)
                kpi_col2.metric("TOTAL SITE VISITS", total_sites)
                kpi_col3.metric("TOTAL REPORTS SENT", total_sent)
                kpi_col4.metric("TOTAL PENDING REPORTS", total_pending)

                st.markdown("---")

                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    st.markdown("#### 📊 Reports Sent to Client")
                    sorted_df1 = summary_df.sort_values(by="Report sent to the client", ascending=True)
                    fig_left = px.bar(
                        sorted_df1,
                        x="Report sent to the client",
                        y="Associate ID",
                        orientation="h",
                        text="Report sent to the client"
                    )
                    fig_left.update_traces(textposition="outside")
                    fig_left.update_layout(
                        xaxis_title="",
                        yaxis_title="",
                        showlegend=False,
                        margin=dict(l=0, r=0, t=30, b=0)
                    )
                    st.plotly_chart(fig_left, use_container_width=True, key="chart_t3_reports")

                with chart_col2:
                    st.markdown("#### 🏢 Tower vs Site Visits Breakdown")
                    df_melted = summary_df.melt(
                        id_vars="Associate ID",
                        value_vars=["Floor Visit", "Site Tower visit"],
                        var_name="Visit Type",
                        value_name="Count"
                    )
                    fig_right = px.bar(
                        df_melted,
                        x="Count",
                        y="Associate ID",
                        color="Visit Type",
                        barmode="group",
                        orientation="h"
                    )
                    fig_right.update_layout(
                        xaxis_title="",
                        yaxis_title="",
                        legend_title="",
                        margin=dict(l=0, r=0, t=30, b=0)
                    )
                    st.plotly_chart(fig_right, use_container_width=True, key="chart_t3_breakdown")

                st.markdown("#### 📋 Detailed Performance Breakdown")

                total_row = pd.DataFrame([{
                    "Associate ID": "TEAM TOTALS",
                    "Floor Visit": total_floors,
                    "Site Tower visit": total_sites,
                    "Report Mark (YES)": summary_df["Report Mark (YES)"].sum(),
                    "Suggestion Visit (NO)": summary_df["Suggestion Visit (NO)"].sum(),
                    "Report Pending": total_pending,
                    "Report sent to the client": total_sent,
                    "Report total with Pend": summary_df["Report total with Pend"].sum()
                }])

                display_df = pd.concat([summary_df, total_row], ignore_index=True)

                st.dataframe(display_df, use_container_width=True, hide_index=True)

                idx_max_site = summary_df["Site Tower visit"].idxmax()
                highest_coverage_str = f"{summary_df.loc[idx_max_site, 'Associate ID']} ({summary_df.loc[idx_max_site, 'Site Tower visit']} Sites)"

                idx_max_floor = summary_df["Floor Visit"].idxmax()
                highest_prod_str = f"{summary_df.loc[idx_max_floor, 'Associate ID']} ({summary_df.loc[idx_max_floor, 'Floor Visit']} Floors)"

                zero_sent_df = summary_df[summary_df["Report sent to the client"] == 0]

                if not zero_sent_df.empty:
                    critical_gaps_str = ", ".join(zero_sent_df["Associate ID"].astype(str).tolist()) + " (0 Sent)"
                else:
                    critical_gaps_str = "All Associates Active"

                h_col1, h_col2, h_col3 = st.columns(3)

                with h_col1:
                    st.markdown(f"""
                    <div class="highlight-card card-blue">
                        <div class="card-title">🌎 Highest Coverage</div>
                        <div class="card-value">{highest_coverage_str}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with h_col2:
                    st.markdown(f"""
                    <div class="highlight-card card-green">
                        <div class="card-title">🚀 Highest Productivity</div>
                        <div class="card-value">{highest_prod_str}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with h_col3:
                    st.markdown(f"""
                    <div class="highlight-card card-red">
                        <div class="card-title">⏳ Critical Gaps</div>
                        <div class="card-value">{critical_gaps_str}</div>
                    </div>
                    """, unsafe_allow_html=True)


# =========================================================
# TAB 4: SITE CARD
# =========================================================
with tab_site_card:
    st.markdown("### 🏢 Site Card")
    st.markdown("Select one site and get complete MasterProject information above and VisitLog details below.")

    master_site_col = find_master_site_column(master_df) if not master_df.empty else None
    visit_site_col = find_visit_site_column(visits_df) if not visits_df.empty else None

    all_sites = []

    if master_site_col:
        all_sites += clean_options(master_df[master_site_col])

    if visit_site_col:
        all_sites += clean_options(visits_df[visit_site_col])

    all_sites = sorted(list(set([x for x in all_sites if str(x).strip()])))

    if not all_sites:
        st.warning("No site names found in MasterProject or VisitLog.")
    else:
        selected_site = st.selectbox(
            "Select Site Name",
            all_sites,
            key="site_card_selected_site"
        )

        site_master = filter_by_site(master_df, master_site_col, selected_site) if master_site_col else pd.DataFrame()
        site_visits = filter_by_site(visits_df, visit_site_col, selected_site) if visit_site_col else pd.DataFrame()

        # Master columns
        col_project = master_site_col
        col_state = first_existing_column(master_df, ["STATE", "State"])
        col_dist = first_existing_column(master_df, ["DISTRICT / CITY", "DISTRICT", "District", "CITY", "City"])
        col_area = first_existing_column(master_df, ["Area", "AREA"])
        col_status = first_existing_column(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
        col_visit_ongoing = first_existing_column(master_df, ["VISIT ONGOING", "Visit Ongoing"])
        col_tech = first_existing_column(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
        col_sales = first_existing_column(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
        col_distb = first_existing_column(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])

        if not site_master.empty:
            master_row = site_master.iloc[0]
        else:
            master_row = pd.Series(dtype="object")

        site_name = selected_site
        state_val = master_row.get(col_state, "-") if col_state else "-"
        dist_val = master_row.get(col_dist, "-") if col_dist else "-"
        area_val = master_row.get(col_area, "-") if col_area else "-"
        status_val = master_row.get(col_status, "-") if col_status else "-"
        ongoing_val = master_row.get(col_visit_ongoing, "-") if col_visit_ongoing else "-"
        tech_val = master_row.get(col_tech, "-") if col_tech else "-"
        sales_val = master_row.get(col_sales, "-") if col_sales else "-"
        distributor_val = master_row.get(col_distb, "-") if col_distb else "-"

        # Visit KPIs
        total_visit_records = len(site_visits)
        total_floor_visits = int(site_visits["Num_Floors"].sum()) if not site_visits.empty and "Num_Floors" in site_visits.columns else 0
        submitted_reports = len(site_visits[site_visits["Status"] == "Submitted"]) if not site_visits.empty else 0
        pending_reports = len(site_visits[site_visits["Status"] == "Pending"]) if not site_visits.empty else 0
        technical_na = len(site_visits[site_visits["Status"] == "Technical (NA)"]) if not site_visits.empty else 0

        last_visit_date = "-"
        last_visit_by = "-"
        last_visit_comment = "-"

        if not site_visits.empty:
            if "Date Parsed" in site_visits.columns:
                sorted_visits = site_visits.sort_values("Date Parsed", ascending=False)
            elif "Date of Visit" in site_visits.columns:
                sorted_visits = site_visits.sort_values("Date of Visit", ascending=False)
            else:
                sorted_visits = site_visits.copy()

            last_row = sorted_visits.iloc[0]

            if "Date of Visit" in sorted_visits.columns:
                last_visit_date = last_row.get("Date of Visit", "-")

            assoc_col = first_existing_column(sorted_visits, ["Associate ID", "Associate", "Technical Person"])
            if assoc_col:
                last_visit_by = last_row.get(assoc_col, "-")

            if "Comment" in sorted_visits.columns:
                last_visit_comment = last_row.get("Comment", "-")

        # Header Site Card
        st.markdown(f"""
        <div class="site-card">
            <div class="site-name">{safe_text(site_name)}</div>
            <div class="site-meta">
                {safe_text(state_val)} | {safe_text(dist_val)} | {safe_text(area_val)}
            </div>

            <div class="info-grid">
                {info_box("Project Status", status_val)}
                {info_box("Visit Ongoing", ongoing_val)}
                {info_box("Technical Person", tech_val)}
                {info_box("Sales Person", sales_val)}
                {info_box("Distributor", distributor_val)}
                {info_box("Total Visit Records", total_visit_records)}
                {info_box("Total Floor Visits", total_floor_visits)}
                {info_box("Pending Reports", pending_reports)}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # KPI row
        k1, k2, k3, k4, k5 = st.columns(5)

        k1.metric("Visit Records", total_visit_records)
        k2.metric("Floor Visits", total_floor_visits)
        k3.metric("Submitted", submitted_reports)
        k4.metric("Pending", pending_reports)
        k5.metric("Technical NA", technical_na)

        # MasterProject Details Above
        st.markdown("""
        <div class="section-card">
            <div class="section-title">📌 MasterProject Details</div>
            <div class="small-note">Complete master information for selected site.</div>
        </div>
        """, unsafe_allow_html=True)

        if site_master.empty:
            st.warning("This site was found in VisitLog, but not found in MasterProject.")
        else:
            # Show all tower columns and other master data
            st.dataframe(site_master.astype(str), use_container_width=True, hide_index=True)

            # Extra readable view
            with st.expander("Open full MasterProject details in vertical view", expanded=False):
                master_vertical = site_master.T.reset_index()
                master_vertical.columns = ["Field", "Value"]
                st.dataframe(master_vertical.astype(str), use_container_width=True, hide_index=True)

        # Last visit summary
        st.markdown("""
        <div class="section-card">
            <div class="section-title">🕒 Latest Visit Summary</div>
        </div>
        """, unsafe_allow_html=True)

        l1, l2, l3 = st.columns([1, 1, 3])

        l1.metric("Last Visit Date", str(last_visit_date))
        l2.metric("Visited By", str(last_visit_by))

        with l3:
            st.markdown("**Last Visit Comment**")
            st.info(str(last_visit_comment))

        # VisitLog Data Below
        st.markdown("""
        <div class="section-card">
            <div class="section-title">📋 VisitLog Details</div>
            <div class="small-note">All visit records for selected site.</div>
        </div>
        """, unsafe_allow_html=True)

        if site_visits.empty:
            st.warning("No VisitLog records found for this site.")
        else:
            # Filters inside site card
            vc1, vc2, vc3 = st.columns(3)

            with vc1:
                site_months = ["All"] + clean_options(site_visits["Month"]) if "Month" in site_visits.columns else ["All"]
                sf_month = st.selectbox("Filter Month", site_months, key="site_card_month")

            with vc2:
                site_statuses = ["All"] + clean_options(site_visits["Status"]) if "Status" in site_visits.columns else ["All"]
                sf_status = st.selectbox("Filter Status", site_statuses, key="site_card_status")

            with vc3:
                assoc_col = first_existing_column(site_visits, ["Associate ID", "Associate", "Technical Person"])
                if assoc_col:
                    site_associates = ["All"] + clean_options(site_visits[assoc_col])
                else:
                    site_associates = ["All"]
                sf_assoc = st.selectbox("Filter Associate", site_associates, key="site_card_assoc")

            site_visit_filtered = site_visits.copy()

            if sf_month != "All" and "Month" in site_visit_filtered.columns:
                site_visit_filtered = site_visit_filtered[site_visit_filtered["Month"] == sf_month]

            if sf_status != "All" and "Status" in site_visit_filtered.columns:
                site_visit_filtered = site_visit_filtered[site_visit_filtered["Status"] == sf_status]

            if assoc_col and sf_assoc != "All":
                site_visit_filtered = site_visit_filtered[site_visit_filtered[assoc_col].astype(str) == sf_assoc]

            # Site Visit Charts
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("##### Site Visits by Month")
                if "Month" in site_visit_filtered.columns:
                    month_chart = site_visit_filtered["Month"].value_counts().reset_index()
                    month_chart.columns = ["Month", "Visits"]
                    fig_site_month = px.bar(month_chart, x="Month", y="Visits")
                    st.plotly_chart(fig_site_month, use_container_width=True, key="site_card_month_chart")

            with c2:
                st.markdown("##### Visit Status Breakdown")
                if "Status" in site_visit_filtered.columns:
                    status_chart = site_visit_filtered["Status"].value_counts().reset_index()
                    status_chart.columns = ["Status", "Count"]
                    fig_site_status = px.pie(status_chart, names="Status", values="Count", hole=0.4)
                    st.plotly_chart(fig_site_status, use_container_width=True, key="site_card_status_chart")

            # Visit table
            visit_display_cols = []

            for c in [
                "Source Sheet",
                "Visit ID",
                visit_site_col,
                "Tower Name",
                "FloorsVisited",
                "Floors Visited",
                "Associate ID",
                "Date of Visit",
                "Is Report Visit?",
                "Status",
                "Report Submitted Date",
                "Comment",
                "CreatedAt"
            ]:
                if c and c in site_visit_filtered.columns and c not in visit_display_cols:
                    visit_display_cols.append(c)

            st.dataframe(
                site_visit_filtered[visit_display_cols].astype(str),
                use_container_width=True,
                hide_index=True
            )

            csv_data = site_visit_filtered[visit_display_cols].to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Download Selected Site VisitLog CSV",
                data=csv_data,
                file_name=f"{selected_site}_VisitLog.csv",
                mime="text/csv"
            )
