import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from html import escape
from datetime import datetime

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
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0px;
        color: #ffffff;
    }

    .sub-title {
        font-size: 16px;
        color: #d1d5db;
        margin-bottom: 25px;
    }

    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #374151;
        padding: 1.2rem;
        border-radius: 1rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.25);
    }

    .report-card {
        background: #ffffff;
        color: #111827;
        border-radius: 14px;
        padding: 24px;
        margin-top: 20px;
        margin-bottom: 20px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 8px 20px rgba(0,0,0,0.20);
    }

    .report-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 3px solid #111827;
        padding-bottom: 14px;
        margin-bottom: 18px;
    }

    .report-title {
        font-size: 30px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 5px;
    }

    .report-subtitle {
        font-size: 14px;
        color: #4b5563;
    }

    .report-badge {
        background: #111827;
        color: #ffffff;
        padding: 8px 14px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 700;
    }

    .report-section-title {
        font-size: 19px;
        font-weight: 800;
        color: #111827;
        margin-top: 20px;
        margin-bottom: 10px;
        border-left: 5px solid #2563eb;
        padding-left: 10px;
    }

    .horizontal-info-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 18px;
        font-size: 13px;
    }

    .horizontal-info-table th {
        background: #f3f4f6;
        color: #111827;
        border: 1px solid #d1d5db;
        padding: 9px;
        text-align: left;
        font-weight: 800;
        white-space: nowrap;
    }

    .horizontal-info-table td {
        border: 1px solid #d1d5db;
        padding: 9px;
        color: #111827;
        vertical-align: top;
    }

    .kpi-strip {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 12px;
        margin-top: 16px;
        margin-bottom: 18px;
    }

    .kpi-box {
        background: #f9fafb;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 14px;
    }

    .kpi-label {
        font-size: 12px;
        color: #6b7280;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .kpi-value {
        font-size: 24px;
        font-weight: 900;
        color: #111827;
    }

    .last-comment-box {
        background: #fffbeb;
        border: 1px solid #f59e0b;
        color: #78350f;
        padding: 14px;
        border-radius: 10px;
        margin-top: 10px;
        margin-bottom: 18px;
        font-size: 14px;
    }

    .download-card {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 18px;
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
        .kpi-strip {
            grid-template-columns: repeat(3, 1fr);
        }
    }

    @media screen and (max-width: 700px) {
        .kpi-strip {
            grid-template-columns: repeat(1, 1fr);
        }
        .report-header {
            display: block;
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
        df[col] = (
            df[col]
            .astype(str)
            .replace({
                "nan": "",
                "None": "",
                "NaT": "",
                "NaN": "",
                "null": "",
                "Null": ""
            })
            .str.strip()
        )

    return df


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


def first_existing_column(df, possible_cols):
    if df.empty:
        return None

    for col in possible_cols:
        if col in df.columns:
            return col

    return None


def parse_floor(val):
    val_str = str(val).strip()

    if not val_str or val_str.lower() in ["nan", "none", "null", "n/a", "na", "-"]:
        return 0

    try:
        return int(float(val_str))
    except Exception:
        return 1


def get_visit_status(row):
    is_report = str(row.get("Is Report Visit?", "")).strip().lower()
    sub_date = str(row.get("Report Submitted Date", "")).strip()

    if is_report in ["no", "n", "false", "n/a", "na"]:
        return "Technical (NA)"

    if sub_date and sub_date.lower() not in ["nan", "none", "", "nat"]:
        return "Submitted"

    return "Pending"


def safe_text(value):
    value = str(value).strip()

    if value.lower() in ["nan", "none", "nat", "null", ""]:
        return "-"

    return escape(value)


def find_master_site_column(master_df):
    return first_existing_column(
        master_df,
        [
            "PROJECT",
            "Project",
            "PROJECT NAME",
            "Project Name",
            "SITE NAME",
            "Site Name",
            "Site"
        ]
    )


def find_visit_site_column(visits_df):
    return first_existing_column(
        visits_df,
        [
            "Site Name",
            "SITE NAME",
            "PROJECT",
            "Project",
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


def get_column_value(row, col):
    if col and col in row.index:
        value = str(row.get(col, "")).strip()
        if value and value.lower() not in ["nan", "none", "null", "nat"]:
            return value
    return "-"


def build_horizontal_table_from_row(row, columns):
    html = "<table class='horizontal-info-table'><tr>"

    for label, col in columns:
        html += f"<th>{safe_text(label)}</th>"

    html += "</tr><tr>"

    for label, col in columns:
        value = get_column_value(row, col) if col else "-"
        html += f"<td>{safe_text(value)}</td>"

    html += "</tr></table>"

    return html


def build_horizontal_table_from_df(df):
    if df.empty:
        return "<p>No data found.</p>"

    safe_df = df.copy().astype(str)
    html = "<table class='horizontal-info-table'><tr>"

    for col in safe_df.columns:
        html += f"<th>{safe_text(col)}</th>"

    html += "</tr>"

    for _, row in safe_df.iterrows():
        html += "<tr>"
        for col in safe_df.columns:
            html += f"<td>{safe_text(row[col])}</td>"
        html += "</tr>"

    html += "</table>"
    return html


def dataframe_to_excel(master_site_df, visit_site_df, summary_df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        master_site_df.to_excel(writer, sheet_name="MasterProject", index=False)
        visit_site_df.to_excel(writer, sheet_name="VisitLog", index=False)

        workbook = writer.book

        for sheet_name in writer.sheets:
            sheet = writer.sheets[sheet_name]

            for cell in sheet[1]:
                cell.font = cell.font.copy(bold=True)

            for column_cells in sheet.columns:
                max_length = 0
                column_letter = column_cells[0].column_letter

                for cell in column_cells:
                    try:
                        cell_value = str(cell.value)
                        if len(cell_value) > max_length:
                            max_length = len(cell_value)
                    except Exception:
                        pass

                adjusted_width = min(max_length + 3, 45)
                sheet.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)
    return output


def create_html_report(
    selected_site,
    master_row,
    master_report_cols_1,
    master_report_cols_2,
    summary_df,
    site_visit_filtered,
    last_visit_comment
):
    generated_on = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{safe_text(selected_site)} Site Visit Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                color: #111827;
            }}

            .header {{
                display: flex;
                justify-content: space-between;
                border-bottom: 3px solid #111827;
                padding-bottom: 12px;
                margin-bottom: 20px;
            }}

            .title {{
                font-size: 28px;
                font-weight: 800;
            }}

            .subtitle {{
                color: #4b5563;
                font-size: 13px;
                margin-top: 5px;
            }}

            .badge {{
                background: #111827;
                color: #ffffff;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                height: fit-content;
            }}

            h2 {{
                font-size: 18px;
                border-left: 5px solid #2563eb;
                padding-left: 10px;
                margin-top: 24px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
                margin-bottom: 18px;
            }}

            th {{
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                padding: 8px;
                text-align: left;
            }}

            td {{
                border: 1px solid #d1d5db;
                padding: 8px;
                vertical-align: top;
            }}

            .comment {{
                background: #fffbeb;
                border: 1px solid #f59e0b;
                padding: 12px;
                border-radius: 8px;
                color: #78350f;
                margin-bottom: 18px;
            }}

            .footer {{
                margin-top: 25px;
                font-size: 11px;
                color: #6b7280;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="title">{safe_text(selected_site)}</div>
                <div class="subtitle">Site Visit Report | Generated on {safe_text(generated_on)}</div>
            </div>
            <div class="badge">Huliot Site Visit Report</div>
        </div>

        <h2>1. Site Master Information</h2>
        {build_horizontal_table_from_row(master_row, master_report_cols_1)}
        {build_horizontal_table_from_row(master_row, master_report_cols_2)}

        <h2>2. Site Visit Summary</h2>
        {build_horizontal_table_from_df(summary_df)}

        <h2>3. Last Visit Comment</h2>
        <div class="comment">{safe_text(last_visit_comment)}</div>

        <h2>4. VisitLog Details</h2>
        {build_horizontal_table_from_df(site_visit_filtered)}

        <div class="footer">
            This report is generated from live Google Sheet data.
        </div>
    </body>
    </html>
    """

    return html.encode("utf-8")


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

        if ws_title_lower == "masterproject" or "master" in ws_title_lower:
            master_df = df.copy()
            master_df["Source Sheet"] = ws_title
            continue

        if any(skip in ws_title_lower for skip in ["setting", "config", "associate", "projectconfigstatus"]):
            continue

        lower_cols = [str(c).lower() for c in df.columns]

        if "visit id" in lower_cols or "site name" in lower_cols:
            df["Source Sheet"] = ws_title
            visit_dataframes.append(df)

    visits_df = pd.concat(visit_dataframes, ignore_index=True) if visit_dataframes else pd.DataFrame()

    visits_df = clean_df(visits_df)
    master_df = clean_df(master_df)

    return visits_df, master_df


# =========================================================
# 6. SESSION DATA
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
# 7. DATA PREPARATION
# =========================================================
if not visits_df.empty:
    visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)

    date_col = first_existing_column(visits_df, ["Date of Visit", "Visit Date", "Date"])

    if date_col:
        visits_df["Date Parsed"] = pd.to_datetime(visits_df[date_col], errors="coerce")
        visits_df["Month"] = visits_df["Date Parsed"].dt.strftime("%b %Y")
        visits_df["Month"] = visits_df["Month"].fillna("Unknown")
    else:
        visits_df["Date Parsed"] = pd.NaT
        visits_df["Month"] = "Unknown"

    floors_col = first_existing_column(visits_df, ["FloorsVisited", "Floors Visited", "Floor Visited", "Floor"])
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
tab_visits, tab_master, tab_exec, tab_site_report = st.tabs([
    "📊 Visit Analytics",
    "📈 Master Projects",
    "👔 Executive Dashboard",
    "🏢 Site Report Card"
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
            associates = ["All"] + clean_options(visits_df[assoc_col]) if assoc_col else ["All"]
            f_assoc = st.selectbox("Associate", associates, key="t1_assoc")

        with col5:
            visit_site_col = find_visit_site_column(visits_df)
            sites = ["All"] + clean_options(visits_df[visit_site_col]) if visit_site_col else ["All"]
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
        submitted_floors_sum = int(
            filtered_v[filtered_v["Clean_Report_Mark"].isin(["YES", "Y", "TRUE"])]["Num_Floors"].sum()
        )

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
                site_counts = filtered_v[visit_site_col].value_counts().nlargest(8).reset_index()
                site_counts.columns = ["Site Name", "Visits"]
                fig2 = px.pie(site_counts, names="Site Name", values="Visits", hole=0.4)
                st.plotly_chart(fig2, use_container_width=True, key="chart_t1_pie")
            else:
                st.info("Site Name column not found.")

        st.subheader("Visit Records")

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
        col_status = first_existing_column(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
        col_ongoing = first_existing_column(master_df, ["VISIT ONGOING", "Visit Ongoing"])
        col_tech = first_existing_column(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
        col_sales = first_existing_column(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
        col_distributor = first_existing_column(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])

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

        if col_status:
            f_status = m_c3.selectbox("Project Status", ["All"] + clean_options(filtered_m[col_status]), key="t2_status")
            if f_status != "All":
                filtered_m = filtered_m[filtered_m[col_status].astype(str) == f_status]

        if col_tech:
            f_tech = m_c4.selectbox("Tech Person", ["All"] + clean_options(filtered_m[col_tech]), key="t2_tech")
            if f_tech != "All":
                filtered_m = filtered_m[filtered_m[col_tech].astype(str) == f_tech]

        if col_sales:
            f_sales = m_c5.selectbox("Sales Person", ["All"] + clean_options(filtered_m[col_sales]), key="t2_sales")
            if f_sales != "All":
                filtered_m = filtered_m[filtered_m[col_sales].astype(str) == f_sales]

        if col_distributor:
            f_distributor = m_c6.selectbox("Distributor", ["All"] + clean_options(filtered_m[col_distributor]), key="t2_distributor")
            if f_distributor != "All":
                filtered_m = filtered_m[filtered_m[col_distributor].astype(str) == f_distributor]

        total_proj = len(filtered_m)

        if col_ongoing:
            active_proj = len(
                filtered_m[
                    filtered_m[col_ongoing].astype(str).str.lower().isin(["yes", "y", "ongoing"])
                ]
            )
        else:
            active_proj = 0

        unique_states = filtered_m[col_state].nunique() if col_state else 0

        teams_set = set()

        if col_tech:
            teams_set.update(filtered_m[col_tech].dropna().astype(str).tolist())

        if col_sales:
            teams_set.update(filtered_m[col_sales].dropna().astype(str).tolist())

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
            if col_status:
                status_c = filtered_m[col_status].value_counts().reset_index()
                status_c.columns = ["Status", "Count"]
                fig4 = px.pie(status_c, names="Status", values="Count", hole=0.4)
                st.plotly_chart(fig4, use_container_width=True, key="chart_t2_status")

        st.subheader("Master Projects Directory")
        st.dataframe(filtered_m.astype(str), use_container_width=True, hide_index=True)


# =========================================================
# TAB 3: EXECUTIVE DASHBOARD
# =========================================================
with tab_exec:
    st.markdown("### Executive Dashboard")
    st.markdown("Multi-month associate performance tracking and field analytics")

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
                    "Report Mark YES": int(report_yes_sum),
                    "Suggestion Visit NO": int(report_no_sum),
                    "Report Pending": int(report_pending),
                    "Report Sent to Client": int(client_sent_floors),
                    "Report Total With Pending": int(client_sent_floors + report_pending)
                })

            summary_df = pd.DataFrame(summary_rows)

            if summary_df.empty:
                st.info("No executive data found.")
            else:
                total_floors = summary_df["Floor Visit"].sum()
                total_sites = summary_df["Site Tower visit"].sum()
                total_sent = summary_df["Report Sent to Client"].sum()
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
                    sorted_df1 = summary_df.sort_values(by="Report Sent to Client", ascending=True)
                    fig_left = px.bar(
                        sorted_df1,
                        x="Report Sent to Client",
                        y="Associate ID",
                        orientation="h",
                        text="Report Sent to Client"
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
                    "Report Mark YES": summary_df["Report Mark YES"].sum(),
                    "Suggestion Visit NO": summary_df["Suggestion Visit NO"].sum(),
                    "Report Pending": total_pending,
                    "Report Sent to Client": total_sent,
                    "Report Total With Pending": summary_df["Report Total With Pending"].sum()
                }])

                display_df = pd.concat([summary_df, total_row], ignore_index=True)

                st.dataframe(display_df, use_container_width=True, hide_index=True)


# =========================================================
# TAB 4: SITE REPORT CARD
# =========================================================
with tab_site_report:
    st.markdown("### 🏢 Site Report Card")
    st.markdown("Select one site. The report will show all MasterProject information above and all VisitLog data below.")

    if master_df.empty and visits_df.empty:
        st.warning("No MasterProject or VisitLog data found.")
    else:
        master_site_col = find_master_site_column(master_df) if not master_df.empty else None
        visit_site_col = find_visit_site_column(visits_df) if not visits_df.empty else None

        all_sites = []

        if master_site_col:
            all_sites += clean_options(master_df[master_site_col])

        if visit_site_col:
            all_sites += clean_options(visits_df[visit_site_col])

        all_sites = sorted(list(set([x for x in all_sites if str(x).strip()])))

        if not all_sites:
            st.warning("No site names found.")
        else:
            control_col1, control_col2 = st.columns([3, 1])

            with control_col1:
                selected_site = st.selectbox(
                    "Select Site Name",
                    all_sites,
                    key="site_report_selected_site"
                )

            with control_col2:
                st.write("")
                st.write("")
                show_all_columns = st.checkbox("Show all columns", value=True)

            site_master = filter_by_site(master_df, master_site_col, selected_site) if master_site_col else pd.DataFrame()
            site_visits = filter_by_site(visits_df, visit_site_col, selected_site) if visit_site_col else pd.DataFrame()

            if not site_master.empty:
                master_row = site_master.iloc[0]
            else:
                master_row = pd.Series(dtype="object")

            # Master columns
            col_project = master_site_col
            col_state = first_existing_column(master_df, ["STATE", "State"])
            col_dist = first_existing_column(master_df, ["DISTRICT / CITY", "DISTRICT", "District", "CITY", "City"])
            col_area = first_existing_column(master_df, ["Area", "AREA"])
            col_status = first_existing_column(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
            col_visit_ongoing = first_existing_column(master_df, ["VISIT ONGOING", "Visit Ongoing"])
            col_tech = first_existing_column(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
            col_sales = first_existing_column(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
            col_distributor = first_existing_column(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])

            # Visit columns
            assoc_col = first_existing_column(site_visits, ["Associate ID", "Associate", "Technical Person"])
            date_col = first_existing_column(site_visits, ["Date of Visit", "Visit Date", "Date"])
            comment_col = first_existing_column(site_visits, ["Comment", "Remarks", "Observation"])
            tower_col = first_existing_column(site_visits, ["Tower Name", "Tower", "Building"])
            floor_col = first_existing_column(site_visits, ["FloorsVisited", "Floors Visited", "Floor Visited", "Floor"])

            # Latest visit
            last_visit_date = "-"
            last_visit_by = "-"
            last_visit_comment = "-"

            if not site_visits.empty:
                if "Date Parsed" in site_visits.columns:
                    sorted_visits = site_visits.sort_values("Date Parsed", ascending=False)
                elif date_col:
                    sorted_visits = site_visits.sort_values(date_col, ascending=False)
                else:
                    sorted_visits = site_visits.copy()

                last_row = sorted_visits.iloc[0]

                if date_col:
                    last_visit_date = last_row.get(date_col, "-")

                if assoc_col:
                    last_visit_by = last_row.get(assoc_col, "-")

                if comment_col:
                    last_visit_comment = last_row.get(comment_col, "-")

            # KPIs
            total_visit_records = len(site_visits)
            total_floor_visits = int(site_visits["Num_Floors"].sum()) if not site_visits.empty and "Num_Floors" in site_visits.columns else 0
            submitted_reports = len(site_visits[site_visits["Status"] == "Submitted"]) if not site_visits.empty and "Status" in site_visits.columns else 0
            pending_reports = len(site_visits[site_visits["Status"] == "Pending"]) if not site_visits.empty and "Status" in site_visits.columns else 0
            technical_na = len(site_visits[site_visits["Status"] == "Technical (NA)"]) if not site_visits.empty and "Status" in site_visits.columns else 0
            total_towers = site_visits[tower_col].nunique() if tower_col and not site_visits.empty else 0

            summary_df = pd.DataFrame([{
                "Site Name": selected_site,
                "Total Visit Records": total_visit_records,
                "Total Floor Visits": total_floor_visits,
                "Submitted Reports": submitted_reports,
                "Pending Reports": pending_reports,
                "Technical NA": technical_na,
                "Total Towers": total_towers,
                "Last Visit Date": last_visit_date,
                "Last Visit By": last_visit_by
            }])

            master_report_cols_1 = [
                ("Project / Site Name", col_project),
                ("State", col_state),
                ("District / City", col_dist),
                ("Area", col_area),
                ("Project Status", col_status),
                ("Visit Ongoing", col_visit_ongoing)
            ]

            master_report_cols_2 = [
                ("Technical Person", col_tech),
                ("Sales Person", col_sales),
                ("Distributor", col_distributor),
                ("Source Sheet", "Source Sheet"),
                ("Last Visit Date", None),
                ("Last Visit By", None)
            ]

            # Custom row for last visit values
            master_row_for_report = master_row.copy()
            master_row_for_report["Last Visit Date"] = last_visit_date
            master_row_for_report["Last Visit By"] = last_visit_by

            master_report_cols_2 = [
                ("Technical Person", col_tech),
                ("Sales Person", col_sales),
                ("Distributor", col_distributor),
                ("Source Sheet", "Source Sheet"),
                ("Last Visit Date", "Last Visit Date"),
                ("Last Visit By", "Last Visit By")
            ]

            # Main report card
            st.markdown(f"""
            <div class="report-card">
                <div class="report-header">
                    <div>
                        <div class="report-title">{safe_text(selected_site)}</div>
                        <div class="report-subtitle">
                            Site Visit Report | MasterProject information above and VisitLog data below
                        </div>
                    </div>
                    <div class="report-badge">Live Google Sheet Report</div>
                </div>

                <div class="report-section-title">1. Site Master Information</div>
                {build_horizontal_table_from_row(master_row_for_report, master_report_cols_1)}
                {build_horizontal_table_from_row(master_row_for_report, master_report_cols_2)}

                <div class="report-section-title">2. Visit Summary</div>

                <div class="kpi-strip">
                    <div class="kpi-box">
                        <div class="kpi-label">Visit Records</div>
                        <div class="kpi-value">{total_visit_records}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Floor Visits</div>
                        <div class="kpi-value">{total_floor_visits}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Submitted</div>
                        <div class="kpi-value">{submitted_reports}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Pending</div>
                        <div class="kpi-value">{pending_reports}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Technical NA</div>
                        <div class="kpi-value">{technical_na}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Towers</div>
                        <div class="kpi-value">{total_towers}</div>
                    </div>
                </div>

                <div class="report-section-title">3. Last Visit Comment</div>
                <div class="last-comment-box">
                    <b>Date:</b> {safe_text(last_visit_date)} &nbsp; | &nbsp;
                    <b>Visited By:</b> {safe_text(last_visit_by)}
                    <br><br>
                    <b>Comment:</b> {safe_text(last_visit_comment)}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Filters for VisitLog
            st.markdown("### 📋 VisitLog Data")

            if site_visits.empty:
                st.warning("No VisitLog records found for selected site.")
            else:
                vf1, vf2, vf3, vf4 = st.columns(4)

                with vf1:
                    site_months = ["All"] + clean_options(site_visits["Month"]) if "Month" in site_visits.columns else ["All"]
                    sf_month = st.selectbox("Month", site_months, key="site_report_month")

                with vf2:
                    site_statuses = ["All"] + clean_options(site_visits["Status"]) if "Status" in site_visits.columns else ["All"]
                    sf_status = st.selectbox("Status", site_statuses, key="site_report_status")

                with vf3:
                    site_associates = ["All"] + clean_options(site_visits[assoc_col]) if assoc_col else ["All"]
                    sf_assoc = st.selectbox("Associate", site_associates, key="site_report_assoc")

                with vf4:
                    if tower_col:
                        site_towers = ["All"] + clean_options(site_visits[tower_col])
                    else:
                        site_towers = ["All"]
                    sf_tower = st.selectbox("Tower", site_towers, key="site_report_tower")

                site_visit_filtered = site_visits.copy()

                if sf_month != "All" and "Month" in site_visit_filtered.columns:
                    site_visit_filtered = site_visit_filtered[site_visit_filtered["Month"] == sf_month]

                if sf_status != "All" and "Status" in site_visit_filtered.columns:
                    site_visit_filtered = site_visit_filtered[site_visit_filtered["Status"] == sf_status]

                if assoc_col and sf_assoc != "All":
                    site_visit_filtered = site_visit_filtered[site_visit_filtered[assoc_col].astype(str) == sf_assoc]

                if tower_col and sf_tower != "All":
                    site_visit_filtered = site_visit_filtered[site_visit_filtered[tower_col].astype(str) == sf_tower]

                # Better report columns
                preferred_visit_cols = []

                for c in [
                    "Source Sheet",
                    "Visit ID",
                    visit_site_col,
                    tower_col,
                    floor_col,
                    assoc_col,
                    date_col,
                    "Is Report Visit?",
                    "Status",
                    "Report Submitted Date",
                    comment_col,
                    "CreatedAt"
                ]:
                    if c and c in site_visit_filtered.columns and c not in preferred_visit_cols:
                        preferred_visit_cols.append(c)

                if show_all_columns:
                    visit_display_df = site_visit_filtered.copy()
                else:
                    visit_display_df = site_visit_filtered[preferred_visit_cols].copy()

                # Charts
                chart_a, chart_b = st.columns(2)

                with chart_a:
                    st.markdown("##### Site Visits by Month")
                    if "Month" in site_visit_filtered.columns:
                        month_chart = site_visit_filtered["Month"].value_counts().reset_index()
                        month_chart.columns = ["Month", "Visits"]
                        fig_site_month = px.bar(month_chart, x="Month", y="Visits")
                        st.plotly_chart(fig_site_month, use_container_width=True, key="site_report_month_chart")

                with chart_b:
                    st.markdown("##### Status Breakdown")
                    if "Status" in site_visit_filtered.columns:
                        status_chart = site_visit_filtered["Status"].value_counts().reset_index()
                        status_chart.columns = ["Status", "Count"]
                        fig_site_status = px.pie(status_chart, names="Status", values="Count", hole=0.4)
                        st.plotly_chart(fig_site_status, use_container_width=True, key="site_report_status_chart")

                # VisitLog table
                st.dataframe(
                    visit_display_df.astype(str),
                    use_container_width=True,
                    hide_index=True
                )

                # Full MasterProject horizontal data
                st.markdown("### 📌 Full MasterProject Data")

                if site_master.empty:
                    st.warning("Selected site not found in MasterProject.")
                    master_download_df = pd.DataFrame()
                else:
                    master_download_df = site_master.copy()
                    st.dataframe(master_download_df.astype(str), use_container_width=True, hide_index=True)

                # Downloads
                st.markdown("""
                <div class="download-card">
                    <h3 style="color:white; margin-top:0;">⬇️ Download Report</h3>
                    <p style="color:#d1d5db; margin-bottom:0;">
                        Use Excel for official sharing and HTML for printable report format.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                d1, d2, d3 = st.columns(3)

                excel_file = dataframe_to_excel(
                    master_download_df,
                    visit_display_df,
                    summary_df
                )

                html_file = create_html_report(
                    selected_site=selected_site,
                    master_row=master_row_for_report,
                    master_report_cols_1=master_report_cols_1,
                    master_report_cols_2=master_report_cols_2,
                    summary_df=summary_df,
                    site_visit_filtered=visit_display_df,
                    last_visit_comment=last_visit_comment
                )

                csv_file = visit_display_df.to_csv(index=False).encode("utf-8")

                safe_filename_site = selected_site.replace("/", "_").replace("\\", "_").replace(" ", "_")

                with d1:
                    st.download_button(
                        label="⬇️ Download Excel Report",
                        data=excel_file,
                        file_name=f"{safe_filename_site}_Site_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                with d2:
                    st.download_button(
                        label="⬇️ Download Printable HTML Report",
                        data=html_file,
                        file_name=f"{safe_filename_site}_Site_Report.html",
                        mime="text/html"
                    )

                with d3:
                    st.download_button(
                        label="⬇️ Download VisitLog CSV",
                        data=csv_file,
                        file_name=f"{safe_filename_site}_VisitLog.csv",
                        mime="text/csv"
                    )
