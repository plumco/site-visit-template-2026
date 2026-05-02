import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Page Config & CSS ---
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

# Custom CSS to make the dashboard look premium and match your design
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .highlight-card {
        padding: 20px; 
        border-radius: 12px; 
        text-align: left; 
        font-family: sans-serif;
        font-weight: bold;
        margin-top: 10px;
    }
    .card-blue { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .card-green { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .card-red { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
    .card-title { font-size: 0.9rem; margin-bottom: 5px; opacity: 0.8; }
    .card-value { font-size: 1.2rem; }
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
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'none', 'null', 'n/a', '-']:
        return 0
    try:
        return int(float(val_str))
    except ValueError:
        return 1

# --- 5. UI Setup ---
st.title("📊 Site Visit Deep Analytics")
st.markdown("Live data synchronized directly from your Google Sheets.")

tab_visits, tab_master, tab_exec = st.tabs(["📊 Visit Analytics", "📈 Master Projects", "👔 Executive Dashboard"])

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

        # Convert Floors to Numbers properly for the entire filtered set
        floors_col_t1 = 'FloorsVisited' if 'FloorsVisited' in filtered_v.columns else 'Floors Visited'
        filtered_v['Num_Floors'] = filtered_v.get(floors_col_t1, pd.Series([], dtype=float)).apply(parse_floor)

        # Calculate KPIs by summing FloorsVisited (instead of just counting rows)
        total_visits_floors = int(filtered_v['Num_Floors'].sum())
        pending_count = len(filtered_v[filtered_v['Status'] == 'Pending'])
        submitted_count = len(filtered_v[filtered_v['Status'] == 'Submitted'])
        
        tech_na_floors = int(filtered_v[filtered_v['Status'] == 'Technical (NA)']['Num_Floors'].sum())
        submitted_floors_sum = int(filtered_v[filtered_v['Status'] == 'Submitted']['Num_Floors'].sum())

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
# TAB 3: EXECUTIVE DASHBOARD (FULL UI)
# ==========================================
with tab_exec:
    # 1. Format Date for Month Filter
    if 'Month' not in visits_df.columns and not visits_df.empty:
        visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
        visits_df['Month'] = visits_df['Month'].fillna('Unknown')

    # 2. Header and Month Dropdown Area
    exec_col1, exec_col2 = st.columns([4, 1])
    with exec_col1:
        st.markdown("### Executive Dashboard")
        st.markdown("Multi-month associate performance tracking & field analytics", unsafe_allow_html=True)
    with exec_col2:
        if not visits_df.empty:
            exec_months = ['All'] + list(visits_df['Month'].dropna().unique())
            selected_month = st.selectbox("Month", exec_months, label_visibility="collapsed", key="exec_month_filter")
        else:
            selected_month = 'All'

    if visits_df.empty:
        st.warning("No Visit Log data found to build the dashboard.")
    else:
        # Filter Data
        exec_filtered_df = visits_df.copy()
        if selected_month != 'All':
            exec_filtered_df = exec_filtered_df[exec_filtered_df['Month'] == selected_month]

        if exec_filtered_df.empty:
            st.info(f"No records found for {selected_month}.")
        else:
            # Prepare Data & Status
            if 'Status' not in exec_filtered_df.columns:
                exec_filtered_df['Status'] = exec_filtered_df.apply(get_visit_status, axis=1)

            floors_col = 'FloorsVisited' if 'FloorsVisited' in exec_filtered_df.columns else 'Floors Visited'
            exec_filtered_df['Num_Floors'] = exec_filtered_df.get(floors_col, pd.Series([], dtype=float)).apply(parse_floor)
            exec_filtered_df['Clean_Report_Mark'] = exec_filtered_df.get('Is Report Visit?', '').astype(str).str.strip().str.upper()
            
            # Build the Core Summary Table
            summary_rows = []
            for assoc, group in exec_filtered_df.groupby('Associate ID'):
                if pd.isna(assoc) or str(assoc).strip() == '':
                    continue
                    
                # Floor visits and Site Visits
                floor_visit_sum = group['Num_Floors'].sum()
                site_tower_count = group['Site Name'].count() if 'Site Name' in group.columns else 0
                
                mask_yes = group['Clean_Report_Mark'].isin(['YES', 'Y', 'TRUE'])
                mask_no = group['Clean_Report_Mark'].isin(['NO', 'N', 'FALSE'])
                
                report_yes_sum = group[mask_yes]['Num_Floors'].sum()
                report_no_sum = group[mask_no]['Num_Floors'].sum()
                
                report_pending = len(group[group['Status'] == 'Pending'])
                
                # Client sent floors (based on YES marking)
                client_sent_floors = group[mask_yes]['Num_Floors'].sum()
                
                summary_rows.append({
                    'Associate ID': assoc,
                    'Floor Visit': int(floor_visit_sum),
                    'Site Tower visit': int(site_tower_count),
                    'Report Mark (YES)': int(report_yes_sum),
                    'Suggestion Visit (NO)': int(report_no_sum),
                    'Report Pending': report_pending,
                    'Report sent to the client': int(client_sent_floors),
                    'March Month(Pending)': 0,
                    'Report total with Pend': int(client_sent_floors)
                })
                
            summary_df = pd.DataFrame(summary_rows)

            # --- TOP KPI METRICS ---
            if not summary_df.empty:
                total_floors = summary_df['Floor Visit'].sum()
                total_sites = summary_df['Site Tower visit'].sum()
                total_sent = summary_df['Report sent to the client'].sum()
                total_pending = summary_df['Report Pending'].sum()
            else:
                total_floors = total_sites = total_sent = total_pending = 0

            st.write("") # Spacer
            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
            kpi_col1.metric("TOTAL FLOOR VISITS", total_floors)
            kpi_col2.metric("TOTAL SITE VISITS", total_sites)
            kpi_col3.metric("TOTAL REPORTS SENT", total_sent)
            kpi_col4.metric("TOTAL PENDING REPORTS", total_pending)

            st.write("") # Spacer
            st.markdown("---")

            # --- CHARTS SECTION ---
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.markdown("#### 📊 Reports Sent to Client")
                if not summary_df.empty:
                    sorted_df1 = summary_df.sort_values(by='Report sent to the client', ascending=True)
                    fig_left = px.bar(
                        sorted_df1, 
                        x='Report sent to the client', 
                        y='Associate ID', 
                        orientation='h',
                        text='Report sent to the client',
                        color_discrete_sequence=['#3b82f6']
                    )
                    fig_left.update_traces(textposition='outside')
                    fig_left.update_layout(xaxis_title="", yaxis_title="", showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_left, use_container_width=True)
                    
            with chart_col2:
                st.markdown("#### 🏢 Tower vs Site Visits Breakdown")
                if not summary_df.empty:
                    df_melted = summary_df.melt(
                        id_vars='Associate ID', 
                        value_vars=['Floor Visit', 'Site Tower visit'], 
                        var_name='Visit Type', 
                        value_name='Count'
                    )
                    fig_right = px.bar(
                        df_melted, 
                        x='Count', 
                        y='Associate ID', 
                        color='Visit Type', 
                        barmode='group', 
                        orientation='h',
                        color_discrete_map={'Floor Visit': '#6366f1', 'Site Tower visit': '#10b981'}
                    )
                    fig_right.update_layout(xaxis_title="", yaxis_title="", legend_title="", margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_right, use_container_width=True)

            # --- DETAILED PERFORMANCE BREAKDOWN TABLE ---
            st.markdown("#### 📋 Detailed Performance Breakdown")
            
            if not summary_df.empty:
                total_row = pd.DataFrame([{
                    'Associate ID': 'TEAM TOTALS',
                    'Floor Visit': total_floors,
                    'Site Tower visit': total_sites,
                    'Report Mark (YES)': summary_df['Report Mark (YES)'].sum(),
                    'Suggestion Visit (NO)': summary_df['Suggestion Visit (NO)'].sum(),
                    'Report Pending': total_pending,
                    'Report sent to the client': total_sent,
                    'March Month(Pending)': 0,
                    'Report total with Pend': summary_df['Report total with Pend'].sum()
                }])
                display_df = pd.concat([summary_df, total_row], ignore_index=True)
                
                st.dataframe(
                    display_df, 
                    use_container_width=True, 
                    hide_index=True
                )
                
                # --- BOTTOM HIGHLIGHT CARDS ---
                highest_coverage_str = "None"
                highest_prod_str = "None"
                critical_gaps_str = "None"
                
                if len(summary_df) > 0:
                    idx_max_site = summary_df['Site Tower visit'].idxmax()
                    highest_coverage_str = f"{summary_df.loc[idx_max_site, 'Associate ID']} ({summary_df.loc[idx_max_site, 'Site Tower visit']} Sites)"
                    
                    idx_max_floor = summary_df['Floor Visit'].idxmax()
                    highest_prod_str = f"{summary_df.loc[idx_max_floor, 'Associate ID']} ({summary_df.loc[idx_max_floor, 'Floor Visit']} Floors)"
                    
                    zero_sent_df = summary_df[summary_df['Report sent to the client'] == 0]
                    if not zero_sent_df.empty:
                        critical_gaps_str = ", ".join(zero_sent_df['Associate ID'].tolist()) + " (0 Sent)"
                    else:
                        critical_gaps_str = "All Associates Active"

                st.write("")
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
