import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Page Config & CSS ---
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

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
@st.cache_resource
def init_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

client = init_connection()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304" 

# --- 3. Load Data from Google Sheets ---
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
        
        raw_data = ws.get_all_values()
        if not raw_data or len(raw_data) < 2:
            continue
            
        raw_headers = [str(h).strip() for h in raw_data[0]] 
        
        seen = {}
        headers = []
        for h in raw_headers:
            if h in seen:
                seen[h] += 1
                headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                headers.append(h)
                
        df = pd.DataFrame(raw_data[1:], columns=headers)
        
        if 'master' in title:
            master_df = df
            continue
            
        if any(skip in title for skip in ['setting', 'config', 'associate']):
            continue
            
        if not df.empty and ('Site Name' in df.columns or 'Visit ID' in df.columns):
            df['Source Sheet'] = ws.title
            visit_dataframes.append(df)

    visits_df = pd.concat(visit_dataframes, ignore_index=True) if visit_dataframes else pd.DataFrame()
    return visits_df, master_df

visits_df, master_df = load_data()

# --- 4. Helper Functions ---
def get_visit_status(row):
    is_report = str(row.get('Is Report Visit?', '')).strip().lower()
    sub_date = str(row.get('Report Submitted Date', '')).strip()
    
    if is_report in ['no', 'false', 'n/a']: return 'Technical (NA)'
    if sub_date and sub_date.lower() not in ['nan', 'none', '']: return 'Submitted'
    return 'Pending'

def parse_floor(val):
    """
    Core Logic: If it's a number, return the number. 
    If it's any text/name, consider it as 1. 
    If it's completely empty, consider it as 0.
    """
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'none', 'null', 'n/a', '-']:
        return 0
    try:
        # Try to convert to float first (in case of '2.0'), then integer
        return int(float(val_str))
    except ValueError:
        # If it hits an error, it means it is text (e.g., "John Doe", "Ground Floor")
        # Rule: If there is any text, consider it as 1
        return 1

# --- 5. UI Setup ---
st.title("📊 Site Visit Deep Analytics")
st.markdown("Live data synchronized directly from your Google Sheets.")

tab_visits, tab_master, tab_exec = st.tabs(["📊 Visit Analytics", "📈 Master Projects", "👔 Executive Summary"])

# ==========================================
# TAB 1: VISIT ANALYTICS
# ==========================================
with tab_visits:
    if visits_df.empty:
        st.warning("No Visit Log data found.")
    else:
        visits_df['Status'] = visits_df.apply(get_visit_status, axis=1)
        visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
        visits_df['Month'].fillna('Unknown', inplace=True)

        st.subheader("Data Filters")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            sources = ['All'] + list(visits_df['Source Sheet'].astype(str).unique())
            f_source = st.selectbox("Source Sheet", sources)
        with col2:
            months = ['All'] + list(visits_df['Month'].astype(str).unique())
            f_month = st.selectbox("Month", months)
        with col3:
            statuses = ['All'] + list(visits_df['Status'].astype(str).unique())
            f_status = st.selectbox("Status", statuses)
        with col4:
            associates = ['All'] + list(visits_df['Associate ID'].astype(str).unique())
            f_assoc = st.selectbox("Associate", associates)
        with col5:
            sites = ['All'] + list(visits_df['Site Name'].astype(str).unique())
            f_site = st.selectbox("Site Name", sites)

        filtered_v = visits_df.copy()
        if f_source != 'All': filtered_v = filtered_v[filtered_v['Source Sheet'].astype(str) == f_source]
        if f_month != 'All': filtered_v = filtered_v[filtered_v['Month'].astype(str) == f_month]
        if f_status != 'All': filtered_v = filtered_v[filtered_v['Status'].astype(str) == f_status]
        if f_assoc != 'All': filtered_v = filtered_v[filtered_v['Associate ID'].astype(str) == f_assoc]
        if f_site != 'All': filtered_v = filtered_v[filtered_v['Site Name'].astype(str) == f_site]

        total_visits = len(filtered_v)
        pending = len(filtered_v[filtered_v['Status'] == 'Pending'])
        submitted = len(filtered_v[filtered_v['Status'] == 'Submitted'])
        tech_na = len(filtered_v[filtered_v['Status'] == 'Technical (NA)'])
        
        submitted_df = filtered_v[filtered_v['Status'] == 'Submitted']
        
        # Apply strict text=1 logic for Top KPI Floors
        floors_col_t1 = 'FloorsVisited' if 'FloorsVisited' in submitted_df.columns else 'Floors Visited'
        total_floors = sum(parse_floor(val) for val in submitted_df.get(floors_col_t1, []))

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Total Visits", total_visits)
        kpi2.metric("Pending Reports", pending)
        kpi3.metric("Technical (NA)", tech_na)
        kpi4.metric("Submitted", submitted)
        kpi5.metric("Submitted Floors", total_floors)

        st.markdown("---")

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

        st.subheader("Visit Records")
        display_cols = [c for c in ['Source Sheet', 'Visit ID', 'Site Name', 'Tower Name', 'FloorsVisited', 'Associate ID', 'Date of Visit', 'Status', 'Report Submitted Date', 'Comment'] if c in filtered_v.columns]
        st.dataframe(filtered_v[display_cols].astype(str), use_container_width=True)

# ==========================================
# TAB 2: MASTER PROJECT ANALYTICS
# ==========================================
with tab_master:
    if master_df.empty:
        st.warning("No Master Project data found.")
    else:
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

        total_proj = len(filtered_m)
        active_proj = len(filtered_m[filtered_m[col_ong].astype(str).str.lower().isin(['yes', 'y', 'ongoing'])]) if col_ong else 0
        unique_states = filtered_m[col_state].nunique() if col_state else 0
        
        teams_set = set()
        if col_tech: teams_set.update(filtered_m[col_tech].dropna().astype(str).tolist())
        if col_sale: teams_set.update(filtered_m[col_sale].dropna().astype(str).tolist())
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Projects", total_proj)
        k2.metric("Active Visits (Ongoing)", active_proj)
        k3.metric("States Covered", unique_states)
        k4.metric("Tech / Sales Teams", len([x for x in teams_set if x.strip() and x.lower() not in ['nan', 'none', '']]))

        st.markdown("---")

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

        st.subheader("Master Projects Directory")
        st.dataframe(filtered_m.astype(str), use_container_width=True)

# ==========================================
# TAB 3: EXECUTIVE SUMMARY (TABLE GENERATOR)
# ==========================================
with tab_exec:
    # 1. Ensure Date is formatted for the month filter globally
    if 'Month' not in visits_df.columns and not visits_df.empty:
        visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
        visits_df['Month'] = visits_df['Month'].fillna('Unknown')

    # 2. Create Header and Dropdown in the same row
    exec_col1, exec_col2 = st.columns([4, 1])
    with exec_col1:
        st.subheader("Monthly Summary (Associate Data)")
    with exec_col2:
        if not visits_df.empty:
            exec_months = ['All'] + list(visits_df['Month'].dropna().unique())
            selected_month = st.selectbox("Month Filter", exec_months, label_visibility="collapsed")
        else:
            selected_month = 'All'

    if visits_df.empty:
        st.warning("No Visit Log data found to build the summary.")
    else:
        # 3. Filter Data based on Dropdown
        exec_filtered_df = visits_df.copy()
        if selected_month != 'All':
            exec_filtered_df = exec_filtered_df[exec_filtered_df['Month'] == selected_month]

        if exec_filtered_df.empty:
            st.info(f"No records found for {selected_month}.")
        else:
            # Pre-process status logic so we can check for 'Pending'
            if 'Status' not in exec_filtered_df.columns:
                exec_filtered_df['Status'] = exec_filtered_df.apply(get_visit_status, axis=1)

            # Apply the parse_floor logic (counts names/text as 1, converts numbers normally)
            floors_col = 'FloorsVisited' if 'FloorsVisited' in exec_filtered_df.columns else 'Floors Visited'
            exec_filtered_df['Num_Floors'] = exec_filtered_df.get(floors_col, pd.Series([], dtype=float)).apply(parse_floor)
            
            # Clean the "Is Report Visit?" column for accurate checking
            exec_filtered_df['Clean_Report_Mark'] = exec_filtered_df.get('Is Report Visit?', '').astype(str).str.strip().str.upper()
            
            # Generate the Grouped Summary Table
            summary_rows = []
            
            # Group by Associate ID using the FILTERED dataframe
            for assoc, group in exec_filtered_df.groupby('Associate ID'):
                if pd.isna(assoc) or str(assoc).strip() == '':
                    continue
                    
                # 1. Floor Visit (Sum of FloorsVisited handling texts as 1)
                floor_visit_sum = group['Num_Floors'].sum()
                
                # 2. Site Tower Visit (Count of Site Names)
                site_tower_count = group['Site Name'].count() if 'Site Name' in group.columns else 0
                
                # 3. Report Mark (YES) -> count
                report_yes_count = len(group[group['Clean_Report_Mark'].isin(['YES', 'Y', 'TRUE'])])
                
                # 4. Suggestion Visit (NO) -> count
                report_no_count = len(group[group['Clean_Report_Mark'].isin(['NO', 'N', 'FALSE'])])
                
                # 5. Report Pending (From Status calculation)
                report_pending = len(group[group['Status'] == 'Pending'])
                
                # 6. Report sent to the client 
                # (Filter to YES reports only, then sum the strictly parsed Floors)
                yes_reports = group[group['Clean_Report_Mark'].isin(['YES', 'Y', 'TRUE'])]
                client_sent_floors = yes_reports['Num_Floors'].sum()
                
                # Append Row exactly matching the requested format
                summary_rows.append({
                    'Associate ID': assoc,
                    'Floor Visit': int(floor_visit_sum),
                    'Site Tower visit': int(site_tower_count),
                    'Repoert Mark (YES)': report_yes_count,
                    'Suggestion Visit (NO)': report_no_count,
                    'Report Pending': report_pending,
                    'Repoert send to the client': int(client_sent_floors),
                    'March Month(Pending) Repoert send to the client': 0, # Placeholder for previous month
                    'report total with Pend': int(client_sent_floors)     # Summing current + previous
                })
                
            summary_df = pd.DataFrame(summary_rows)
            
            # Display the stylized dataframe
            st.dataframe(
                summary_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Repoert send to the client": st.column_config.NumberColumn(
                        "Repoert send to the client",
                        help="Sum of floors where Is Report Visit is YES (Text names = 1 floor)"
                    )
                }
            )
