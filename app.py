import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Page Config & CSS ---
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

# Custom CSS to make KPIs look like our HTML infographic cards
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Google Sheets Connection ---
# This caches the connection so it doesn't reconnect on every click
@st.cache_resource
def init_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Make sure credentials.json is in the same folder as this script
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

client = init_connection()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304" # <--- REPLACE THIS WITH YOUR GOOGLE SHEET LINK

# --- 3. Load Data from Google Sheets ---
# This caches the data for 5 minutes so it's fast, but stays live
@st.cache_data(ttl=300) 
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Could not open Google Sheet. Ensure it is shared with the service account email. Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    worksheets = spreadsheet.worksheets()
    visit_dataframes = []
    master_df = pd.DataFrame()

    for ws in worksheets:
        title = ws.title.lower()
        
        # Grab Master Sheet
        if 'master' in title:
            master_df = pd.DataFrame(ws.get_all_records())
            continue
            
        # Skip Config Sheets
        if any(skip in title for skip in ['setting', 'config', 'associate']):
            continue
            
        # Process Visit Logs
        df = pd.DataFrame(ws.get_all_records())
        if not df.empty and ('Site Name' in df.columns or 'Visit ID' in df.columns):
            df['Source Sheet'] = ws.title
            visit_dataframes.append(df)

    visits_df = pd.concat(visit_dataframes, ignore_index=True) if visit_dataframes else pd.DataFrame()
    return visits_df, master_df

# Load the data
visits_df, master_df = load_data()

# --- 4. Helper Functions ---
def get_visit_status(row):
    is_report = str(row.get('Is Report Visit?', '')).strip().lower()
    sub_date = str(row.get('Report Submitted Date', '')).strip()
    
    if is_report in ['no', 'false', 'n/a']: return 'Technical (NA)'
    if sub_date and sub_date.lower() not in ['nan', 'none', '']: return 'Submitted'
    return 'Pending'

# --- 5. UI Setup ---
st.title("📊 Site Visit Deep Analytics")
st.markdown("Live data synchronized directly from your Google Sheets.")

tab_visits, tab_master = st.tabs(["📊 Visit Analytics", "📈 Master Projects"])

# ==========================================
# TAB 1: VISIT ANALYTICS
# ==========================================
with tab_visits:
    if visits_df.empty:
        st.warning("No Visit Log data found.")
    else:
        # Pre-process Data for Filtering
        visits_df['Status'] = visits_df.apply(get_visit_status, axis=1)
        visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
        visits_df['Month'].fillna('Unknown', inplace=True)

        # Filters
        st.subheader("Data Filters")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            sources = ['All'] + list(visits_df['Source Sheet'].unique())
            f_source = st.selectbox("Source Sheet", sources)
        with col2:
            months = ['All'] + list(visits_df['Month'].unique())
            f_month = st.selectbox("Month", months)
        with col3:
            statuses = ['All'] + list(visits_df['Status'].unique())
            f_status = st.selectbox("Status", statuses)
        with col4:
            associates = ['All'] + list(visits_df['Associate ID'].astype(str).unique())
            f_assoc = st.selectbox("Associate", associates)
        with col5:
            sites = ['All'] + list(visits_df['Site Name'].astype(str).unique())
            f_site = st.selectbox("Site Name", sites)

        # Apply Filters
        filtered_v = visits_df.copy()
        if f_source != 'All': filtered_v = filtered_v[filtered_v['Source Sheet'] == f_source]
        if f_month != 'All': filtered_v = filtered_v[filtered_v['Month'] == f_month]
        if f_status != 'All': filtered_v = filtered_v[filtered_v['Status'] == f_status]
        if f_assoc != 'All': filtered_v = filtered_v[filtered_v['Associate ID'].astype(str) == f_assoc]
        if f_site != 'All': filtered_v = filtered_v[filtered_v['Site Name'].astype(str) == f_site]

        # Calculate KPIs
        total_visits = len(filtered_v)
        pending = len(filtered_v[filtered_v['Status'] == 'Pending'])
        submitted = len(filtered_v[filtered_v['Status'] == 'Submitted'])
        tech_na = len(filtered_v[filtered_v['Status'] == 'Technical (NA)'])
        
        # Calculate Submitted Floors safely
        submitted_df = filtered_v[filtered_v['Status'] == 'Submitted']
        total_floors = 0
        for val in submitted_df.get('FloorsVisited', submitted_df.get('Floors Visited', [])):
            try:
                total_floors += int(val)
            except:
                total_floors += 1 if str(val).strip() else 0

        # KPI Metrics Row
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Total Visits", total_visits)
        kpi2.metric("Pending Reports", pending)
        kpi3.metric("Technical (NA)", tech_na)
        kpi4.metric("Submitted", submitted)
        kpi5.metric("Submitted Floors", total_floors)

        st.markdown("---")

        # Charts Row
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown("##### Visits Per Month")
            month_counts = filtered_v['Month'].value_counts().reset_index()
            month_counts.columns = ['Month', 'Visits']
            fig1 = px.bar(month_counts, x='Month', y='Visits', color_discrete_sequence=['#6366f1'])
            st.plotly_chart(fig1, use_container_width=True)

        with chart_col2:
            st.markdown("##### Top Sites / Zones")
            site_counts = filtered_v['Site Name'].value_counts().nlargest(6).reset_index()
            site_counts.columns = ['Site Name', 'Visits']
            fig2 = px.pie(site_counts, names='Site Name', values='Visits', hole=0.4, 
                          color_discrete_sequence=['#6366f1', '#14b8a6', '#f59e0b', '#f43f5e', '#8b5cf6', '#0ea5e9'])
            st.plotly_chart(fig2, use_container_width=True)

        # Table
        st.subheader("Visit Records")
        display_cols = [c for c in ['Source Sheet', 'Visit ID', 'Site Name', 'Tower Name', 'FloorsVisited', 'Associate ID', 'Date of Visit', 'Status', 'Report Submitted Date', 'Comment'] if c in filtered_v.columns]
        st.dataframe(filtered_v[display_cols], use_container_width=True)


# ==========================================
# TAB 2: MASTER PROJECT ANALYTICS
# ==========================================
with tab_master:
    if master_df.empty:
        st.warning("No Master Project data found.")
    else:
        # Standardize Columns safely
        def safe_col(options):
            for o in options:
                if o in master_df.columns: return o
            return None

        col_state = safe_col(['STATE', 'State'])
        col_dist = safe_col(['DISTRICT / CITY', 'DISTRICT', 'District'])
        col_stat = safe_col(['STATUS OF PROJECT', 'Status', 'STATUS'])
        col_tech = safe_col(['Technical Person', 'TECHNICAL PERSON NAME', 'TECHNICAL PERSON'])
        col_sale = safe_col(['Sells Person', 'SALES PERSON NAME', 'SALES PERSON', 'Sales Person'])
        col_distr = safe_col(['Distributer', 'DISTRIBUTOR NANE', 'DISTRIBUTOR', 'Distributor'])
        col_ong = safe_col(['VISIT ONGOING', 'Visit Ongoing'])

        # Filters
        st.subheader("Master Filters")
        m_c1, m_c2, m_c3, m_c4, m_c5, m_c6 = st.columns(6)
        
        filtered_m = master_df.copy()

        if col_state:
            f_state = m_c1.selectbox("State", ['All'] + list(filtered_m[col_state].astype(str).unique()))
            if f_state != 'All': filtered_m = filtered_m[filtered_m[col_state].astype(str) == f_state]
            
        if col_dist:
            f_dist = m_c2.selectbox("District", ['All'] + list(filtered_m[col_dist].astype(str).unique()))
            if f_dist != 'All': filtered_m = filtered_m[filtered_m[col_dist].astype(str) == f_dist]
            
        if col_stat:
            f_stat = m_c3.selectbox("Project Status", ['All'] + list(filtered_m[col_stat].astype(str).unique()))
            if f_stat != 'All': filtered_m = filtered_m[filtered_m[col_stat].astype(str) == f_stat]
            
        if col_tech:
            f_tech = m_c4.selectbox("Tech Person", ['All'] + list(filtered_m[col_tech].astype(str).unique()))
            if f_tech != 'All': filtered_m = filtered_m[filtered_m[col_tech].astype(str) == f_tech]
            
        if col_sale:
            f_sale = m_c5.selectbox("Sales Person", ['All'] + list(filtered_m[col_sale].astype(str).unique()))
            if f_sale != 'All': filtered_m = filtered_m[filtered_m[col_sale].astype(str) == f_sale]

        if col_distr:
            f_distr = m_c6.selectbox("Distributor", ['All'] + list(filtered_m[col_distr].astype(str).unique()))
            if f_distr != 'All': filtered_m = filtered_m[filtered_m[col_distr].astype(str) == f_distr]

        # Master KPIs
        total_proj = len(filtered_m)
        active_proj = len(filtered_m[filtered_m[col_ong].astype(str).str.lower().isin(['yes', 'y', 'ongoing'])]) if col_ong else 0
        unique_states = filtered_m[col_state].nunique() if col_state else 0
        
        # Count unique personnel
        teams_set = set()
        if col_tech: teams_set.update(filtered_m[col_tech].dropna().astype(str).tolist())
        if col_sale: teams_set.update(filtered_m[col_sale].dropna().astype(str).tolist())
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Projects", total_proj)
        k2.metric("Active Visits (Ongoing)", active_proj)
        k3.metric("States Covered", unique_states)
        k4.metric("Tech / Sales Teams", len([x for x in teams_set if x.strip() and x.lower() != 'nan']))

        st.markdown("---")

        # Charts Row
        m_chart1, m_chart2 = st.columns(2)
        with m_chart1:
            st.markdown("##### Projects by State")
            if col_state:
                state_c = filtered_m[col_state].value_counts().reset_index()
                state_c.columns = ['State', 'Count']
                fig3 = px.bar(state_c, x='State', y='Count', color_discrete_sequence=['#14b8a6'])
                st.plotly_chart(fig3, use_container_width=True)
                
        with m_chart2:
            st.markdown("##### Project Status")
            if col_stat:
                stat_c = filtered_m[col_stat].value_counts().reset_index()
                stat_c.columns = ['Status', 'Count']
                fig4 = px.pie(stat_c, names='Status', values='Count', hole=0.4,
                             color_discrete_sequence=['#6366f1', '#14b8a6', '#f59e0b', '#f43f5e'])
                st.plotly_chart(fig4, use_container_width=True)

        # Table
        st.subheader("Master Projects Directory")
        st.dataframe(filtered_m, use_container_width=True)
