import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# 1. PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Site Visit Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 2. CUSTOM CSS
# =========================================================
st.markdown("""
<style>
    .main {
        background-color: #f8fafc;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    .dashboard-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0rem;
    }

    .dashboard-subtitle {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1.2rem;
    }

    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }

    div[data-testid="metric-container"] label {
        color: #64748b;
        font-size: 0.85rem;
    }

    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #0f172a;
        font-weight: 800;
    }

    .section-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-bottom: 1rem;
    }

    .small-note {
        color: #64748b;
        font-size: 0.85rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 10px 18px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. GOOGLE SHEETS CONNECTION
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
# 4. HELPER FUNCTIONS
# =========================================================
def clean_headers(headers):
    """Clean and de-duplicate Google Sheet headers."""
    cleaned = []
    seen = {}

    for i, h in enumerate(headers):
        h = str(h).strip()
        if not h:
            h = f"Unnamed_{i + 1}"

        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0

        cleaned.append(h)

    return cleaned


def safe_col(df, possible_names):
    """Return first matching column from possible names."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def unique_options(series):
    """Create clean dropdown options."""
    values = (
        series.fillna("")
        .astype(str)
        .str.strip()
        .replace(["nan", "None", "none", "NaN"], "")
    )
    values = sorted([v for v in values.unique() if v])
    return ["All"] + values


def apply_filter(df, column, selected_value):
    if column and selected_value != "All":
        return df[df[column].fillna("").astype(str).str.strip() == selected_value]
    return df


def get_visit_status(row):
    is_report = str(row.get("Is Report Visit?", "")).strip().lower()
    submitted_date = str(row.get("Report Submitted Date", "")).strip()

    if is_report in ["no", "false", "n/a", "na"]:
        return "Technical (NA)"

    if submitted_date and submitted_date.lower() not in ["nan", "none", ""]:
        return "Submitted"

    return "Pending"


def calculate_floor_count(df):
    floor_col = safe_col(df, ["FloorsVisited", "Floors Visited", "Floor Visited", "Floors"])
    if not floor_col:
        return 0

    total = 0
    for val in df[floor_col]:
        text = str(val).strip()
        if not text or text.lower() in ["nan", "none"]:
            continue
        try:
            total += int(float(text))
        except Exception:
            total += 1
    return total


def make_bar(df, x, y, title, color="#6366f1"):
    fig = px.bar(df, x=x, y=y, text=y)
    fig.update_traces(marker_color=color, textposition="outside")
    fig.update_layout(
        title=title,
        title_font_size=18,
        height=390,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis_title="",
        yaxis_title="",
        font=dict(color="#334155")
    )
    return fig


def make_pie(df, names, values, title):
    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.55,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(
        title=title,
        title_font_size=18,
        height=390,
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig

# =========================================================
# 5. LOAD DATA
# =========================================================
@st.cache_data(ttl=300, show_spinner="Loading live data from Google Sheets...")
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Could not open Google Sheet. Please share the sheet with your service account email. Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    visit_dataframes = []
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

        if any(skip in title for skip in ["setting", "config", "associate"]):
            continue

        if "Site Name" in df.columns or "Visit ID" in df.columns:
            df["Source Sheet"] = ws.title
            visit_dataframes.append(df)

    visits_df = pd.concat(visit_dataframes, ignore_index=True) if visit_dataframes else pd.DataFrame()
    return visits_df, master_df

visits_df, master_df = load_data()

# =========================================================
# 6. HEADER
# =========================================================
st.markdown('<p class="dashboard-title">📊 Site Visit Deep Analytics</p>', unsafe_allow_html=True)
st.markdown('<p class="dashboard-subtitle">Interactive live dashboard connected with Google Sheets</p>', unsafe_allow_html=True)

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# =========================================================
# 7. TABS
# =========================================================
tab_visits, tab_master, tab_raw = st.tabs([
    "📊 Visit Analytics",
    "📈 Master Projects",
    "🧾 Raw Data"
])

# =========================================================
# TAB 1: VISIT ANALYTICS
# =========================================================
with tab_visits:
    if visits_df.empty:
        st.warning("No visit log data found. Please check your sheet names and columns.")
    else:
        visits_df = visits_df.copy()

        date_col = safe_col(visits_df, ["Date of Visit", "Visit Date", "Date"])
        site_col = safe_col(visits_df, ["Site Name", "Project Name", "Site"])
        assoc_col = safe_col(visits_df, ["Associate ID", "Associate", "Technical Person"])
        tower_col = safe_col(visits_df, ["Tower Name", "Tower", "Building"])

        visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)

        if date_col:
            visits_df["Visit Date Clean"] = pd.to_datetime(visits_df[date_col], errors="coerce", dayfirst=True)
            visits_df["Month"] = visits_df["Visit Date Clean"].dt.strftime("%b %Y")
            visits_df["Month"] = visits_df["Month"].fillna("Unknown")
        else:
            visits_df["Visit Date Clean"] = pd.NaT
            visits_df["Month"] = "Unknown"

        # Sidebar filters
        with st.sidebar:
            st.header("Visit Filters")

            search_text = st.text_input("Search Site / Visit ID / Comment")
            f_source = st.selectbox("Source Sheet", unique_options(visits_df["Source Sheet"]))
            f_month = st.selectbox("Month", unique_options(visits_df["Month"]))
            f_status = st.selectbox("Report Status", unique_options(visits_df["Status"]))

            f_assoc = "All"
            if assoc_col:
                f_assoc = st.selectbox("Associate", unique_options(visits_df[assoc_col]))

            f_site = "All"
            if site_col:
                f_site = st.selectbox("Site Name", unique_options(visits_df[site_col]))

            if date_col:
                valid_dates = visits_df["Visit Date Clean"].dropna()
                if not valid_dates.empty:
                    min_date = valid_dates.min().date()
                    max_date = valid_dates.max().date()
                    date_range = st.date_input("Date Range", value=(min_date, max_date))
                else:
                    date_range = None
            else:
                date_range = None

        filtered_v = visits_df.copy()
        filtered_v = apply_filter(filtered_v, "Source Sheet", f_source)
        filtered_v = apply_filter(filtered_v, "Month", f_month)
        filtered_v = apply_filter(filtered_v, "Status", f_status)
        filtered_v = apply_filter(filtered_v, assoc_col, f_assoc)
        filtered_v = apply_filter(filtered_v, site_col, f_site)

        if date_col and date_range and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_v = filtered_v[
                (filtered_v["Visit Date Clean"].dt.date >= start_date) &
                (filtered_v["Visit Date Clean"].dt.date <= end_date)
            ]

        if search_text:
            search_cols = [c for c in [site_col, "Visit ID", "Comment", tower_col] if c and c in filtered_v.columns]
            if search_cols:
                mask = filtered_v[search_cols].astype(str).apply(
                    lambda row: row.str.contains(search_text, case=False, na=False).any(),
                    axis=1
                )
                filtered_v = filtered_v[mask]

        # KPI cards
        total_visits = len(filtered_v)
        pending = len(filtered_v[filtered_v["Status"] == "Pending"])
        submitted = len(filtered_v[filtered_v["Status"] == "Submitted"])
        tech_na = len(filtered_v[filtered_v["Status"] == "Technical (NA)"])
        total_floors = calculate_floor_count(filtered_v[filtered_v["Status"] == "Submitted"])
        submission_rate = round((submitted / total_visits) * 100, 1) if total_visits else 0

        kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
        kpi1.metric("Total Visits", total_visits)
        kpi2.metric("Pending Reports", pending)
        kpi3.metric("Submitted", submitted)
        kpi4.metric("Technical NA", tech_na)
        kpi5.metric("Submitted Floors", total_floors)
        kpi6.metric("Submission Rate", f"{submission_rate}%")

        st.markdown("---")

        # Charts row 1
        c1, c2 = st.columns(2)

        with c1:
            month_counts = (
                filtered_v.groupby("Month", dropna=False)
                .size()
                .reset_index(name="Visits")
            )
            st.plotly_chart(
                make_bar(month_counts, "Month", "Visits", "Visits Per Month", "#6366f1"),
                use_container_width=True
            )

        with c2:
            status_counts = filtered_v["Status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            st.plotly_chart(
                make_pie(status_counts, "Status", "Count", "Report Status Split"),
                use_container_width=True
            )

        # Charts row 2
        c3, c4 = st.columns(2)

        with c3:
            if site_col:
                site_counts = filtered_v[site_col].value_counts().nlargest(10).reset_index()
                site_counts.columns = ["Site Name", "Visits"]
                st.plotly_chart(
                    make_bar(site_counts, "Site Name", "Visits", "Top 10 Sites by Visits", "#14b8a6"),
                    use_container_width=True
                )
            else:
                st.info("Site Name column not found.")

        with c4:
            if assoc_col:
                assoc_counts = filtered_v[assoc_col].value_counts().nlargest(10).reset_index()
                assoc_counts.columns = ["Associate", "Visits"]
                st.plotly_chart(
                    make_bar(assoc_counts, "Associate", "Visits", "Visits by Associate", "#f59e0b"),
                    use_container_width=True
                )
            else:
                st.info("Associate column not found.")

        # Records table
        st.subheader("Visit Records")

        preferred_cols = [
            "Source Sheet",
            "Visit ID",
            site_col,
            tower_col,
            "FloorsVisited",
            "Floors Visited",
            assoc_col,
            date_col,
            "Status",
            "Report Submitted Date",
            "Comment"
        ]
        display_cols = []
        for c in preferred_cols:
            if c and c in filtered_v.columns and c not in display_cols:
                display_cols.append(c)

        st.dataframe(
            filtered_v[display_cols].astype(str) if display_cols else filtered_v.astype(str),
            use_container_width=True,
            hide_index=True
        )

        csv = filtered_v.astype(str).to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Filtered Visit Data",
            data=csv,
            file_name="filtered_visit_data.csv",
            mime="text/csv"
        )

# =========================================================
# TAB 2: MASTER PROJECT ANALYTICS
# =========================================================
with tab_master:
    if master_df.empty:
        st.warning("No master project data found.")
    else:
        master_df = master_df.copy()

        col_state = safe_col(master_df, ["STATE", "State"])
        col_dist = safe_col(master_df, ["DISTRICT / CITY", "DISTRICT", "District", "City"])
        col_stat = safe_col(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
        col_tech = safe_col(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
        col_sale = safe_col(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
        col_distr = safe_col(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])
        col_ong = safe_col(master_df, ["VISIT ONGOING", "Visit Ongoing", "ONGOING"])
        col_project = safe_col(master_df, ["PROJECT NAME", "Project Name", "SITE NAME", "Site Name"])

        with st.sidebar:
            st.header("Master Filters")
            master_search = st.text_input("Search Master Project")

            f_state = st.selectbox("Master State", unique_options(master_df[col_state])) if col_state else "All"
            f_dist = st.selectbox("Master District", unique_options(master_df[col_dist])) if col_dist else "All"
            f_stat = st.selectbox("Master Project Status", unique_options(master_df[col_stat])) if col_stat else "All"
            f_tech = st.selectbox("Master Tech Person", unique_options(master_df[col_tech])) if col_tech else "All"
            f_sale = st.selectbox("Master Sales Person", unique_options(master_df[col_sale])) if col_sale else "All"
            f_distr = st.selectbox("Master Distributor", unique_options(master_df[col_distr])) if col_distr else "All"

        filtered_m = master_df.copy()
        filtered_m = apply_filter(filtered_m, col_state, f_state)
        filtered_m = apply_filter(filtered_m, col_dist, f_dist)
        filtered_m = apply_filter(filtered_m, col_stat, f_stat)
        filtered_m = apply_filter(filtered_m, col_tech, f_tech)
        filtered_m = apply_filter(filtered_m, col_sale, f_sale)
        filtered_m = apply_filter(filtered_m, col_distr, f_distr)

        if master_search:
            mask = filtered_m.astype(str).apply(
                lambda row: row.str.contains(master_search, case=False, na=False).any(),
                axis=1
            )
            filtered_m = filtered_m[mask]

        total_projects = len(filtered_m)
        active_projects = 0
        if col_ong:
            active_projects = len(
                filtered_m[
                    filtered_m[col_ong]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.strip()
                    .isin(["yes", "y", "ongoing", "active"])
                ]
            )

        unique_states = filtered_m[col_state].nunique() if col_state else 0

        team_names = set()
        if col_tech:
            team_names.update(filtered_m[col_tech].dropna().astype(str).str.strip().tolist())
        if col_sale:
            team_names.update(filtered_m[col_sale].dropna().astype(str).str.strip().tolist())
        team_names = [x for x in team_names if x and x.lower() not in ["nan", "none"]]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Projects", total_projects)
        m2.metric("Active Visits", active_projects)
        m3.metric("States Covered", unique_states)
        m4.metric("Tech / Sales Team", len(team_names))

        st.markdown("---")

        mc1, mc2 = st.columns(2)

        with mc1:
            if col_state:
                state_counts = filtered_m[col_state].value_counts().reset_index()
                state_counts.columns = ["State", "Projects"]
                st.plotly_chart(
                    make_bar(state_counts, "State", "Projects", "Projects by State", "#14b8a6"),
                    use_container_width=True
                )
            else:
                st.info("State column not found.")

        with mc2:
            if col_stat:
                status_counts = filtered_m[col_stat].value_counts().reset_index()
                status_counts.columns = ["Status", "Projects"]
                st.plotly_chart(
                    make_pie(status_counts, "Status", "Projects", "Project Status"),
                    use_container_width=True
                )
            else:
                st.info("Project status column not found.")

        mc3, mc4 = st.columns(2)

        with mc3:
            if col_tech:
                tech_counts = filtered_m[col_tech].value_counts().nlargest(10).reset_index()
                tech_counts.columns = ["Technical Person", "Projects"]
                st.plotly_chart(
                    make_bar(tech_counts, "Technical Person", "Projects", "Projects by Technical Person", "#6366f1"),
                    use_container_width=True
                )

        with mc4:
            if col_sale:
                sale_counts = filtered_m[col_sale].value_counts().nlargest(10).reset_index()
                sale_counts.columns = ["Sales Person", "Projects"]
                st.plotly_chart(
                    make_bar(sale_counts, "Sales Person", "Projects", "Projects by Sales Person", "#f59e0b"),
                    use_container_width=True
                )

        st.subheader("Master Projects Directory")
        st.dataframe(filtered_m.astype(str), use_container_width=True, hide_index=True)

        csv_master = filtered_m.astype(str).to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Filtered Master Data",
            data=csv_master,
            file_name="filtered_master_project_data.csv",
            mime="text/csv"
        )

# =========================================================
# TAB 3: RAW DATA
# =========================================================
with tab_raw:
    st.subheader("Raw Google Sheet Data Preview")

    raw_1, raw_2 = st.columns(2)
    with raw_1:
        st.markdown("#### Visit Data")
        st.write(f"Rows: {len(visits_df)} | Columns: {len(visits_df.columns)}")
        st.dataframe(visits_df.astype(str), use_container_width=True, hide_index=True)

    with raw_2:
        st.markdown("#### Master Data")
        st.write(f"Rows: {len(master_df)} | Columns: {len(master_df.columns)}")
        st.dataframe(master_df.astype(str), use_container_width=True, hide_index=True)
