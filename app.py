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
            
        # Extract headers
        raw_headers = [str(h).strip() for h in raw_data[0]] 
        
        # Fix Duplicate Columns instantly
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
        
        # Grab Master Sheet
        if 'master' in title:
            master_df = df
            continue
            
        # Skip Config Sheets
        if any(skip in title for skip in ['setting', 'config', 'associate']):
            continue
            
        # Process Visit Logs
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

def calc_floors(series):
    total = 0
    for val in series:
        try:
            total += int(val)
        except:
            total += 1 if str(val).strip() else 0
    return total

# --- 5. UI Setup ---
st.title("📊 Site Visit Deep Analytics")
st.markdown("Live data synchronized directly from your Google Sheets.")

tab_visits, tab_master, tab_exec = st.tabs(["📊 Visit Analytics", "📈 Master Projects", "💼 Executive Dashboard"])

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
        total_floors = calc_floors(submitted_df.get('FloorsVisited', submitted_df.get('Floors Visited', [])))

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
# TAB 3: EXECUTIVE DASHBOARD
# ==========================================
with tab_exec:
    if visits_df.empty:
        st.warning("No data available for Executive Dashboard.")
    else:
        st.subheader("Multi-Month Associate Performance Tracking")
        all_months_exec = ['All Time'] + list(visits_df['Month'].astype(str).unique())
        selected_month = st.selectbox("Select Month", all_months_exec, key="exec_month_filter")
        
        df_exec = visits_df.copy()
        if selected_month != 'All Time':
            df_exec = df_exec[df_exec['Month'] == selected_month]

        # 1. Executive KPIs
        tot_tower_visits = len(df_exec) 
        tot_site_visits = df_exec['Site Name'].nunique() if 'Site Name' in df_exec.columns else 0
        tot_sent = len(df_exec[df_exec['Status'] == 'Submitted'])
        tot_pending = len(df_exec[df_exec['Status'] == 'Pending'])
        exec_submitted_df = df_exec[df_exec['Status'] == 'Submitted']
        tot_floors_sent = calc_floors(exec_submitted_df.get('FloorsVisited', exec_submitted_df.get('Floors Visited', [])))

        e_kpi1, e_kpi2, e_kpi3, e_kpi4, e_kpi5 = st.columns(5)
        e_kpi1.metric("🏢 Total Tower Visits", tot_tower_visits)
        e_kpi2.metric("📍 Total Site Visits", tot_site_visits)
        e_kpi3.metric("📄 Total Reports Sent", tot_sent)
        e_kpi4.metric("⏱️ Pending Reports", tot_pending)
        e_kpi5.metric("🏢 Submitted Floors", tot_floors_sent)
        
        st.markdown("---")

        # 2. Executive Charts
        e_chart1, e_chart2, e_list = st.columns([2, 2, 1])
        
        with e_chart1:
            st.markdown("##### Reports Sent to Client by Associate")
            sent_data = df_exec[df_exec['Status'] == 'Submitted']['Associate ID'].value_counts().reset_index()
            sent_data.columns = ['Associate ID', 'Reports']
            if not sent_data.empty:
                fig_sent = px.bar(sent_data, x='Reports', y='Associate ID', orientation='h', color_discrete_sequence=['#3b82f6'])
                fig_sent.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_sent, use_container_width=True)
            else:
                st.info("No submitted reports for this period.")

        with e_chart2:
            st.markdown("##### Tower Visits Breakdown by Associate")
            tower_data = df_exec['Associate ID'].value_counts().reset_index()
            tower_data.columns = ['Associate ID', 'Tower Visits']
            if not tower_data.empty:
                fig_tower = px.bar(tower_data, x='Tower Visits', y='Associate ID', orientation='h', color_discrete_sequence=['#10b981'])
                fig_tower.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_tower, use_container_width=True)
            else:
                st.info("No tower visits for this period.")
                
        with e_list:
            st.markdown("##### Top 5 Sites Visited")
            if 'Site Name' in df_exec.columns:
                top_sites = df_exec['Site Name'].value_counts().head(5)
                for i, (site, count) in enumerate(top_sites.items(), 1):
                    st.markdown(f"**{i}. {site}**: {count} visits")
            else:
                st.info("No site data.")

        st.markdown("---")

        # 3. CUSTOM STYLIZED HTML TABLE 
        st.markdown("##### Detailed Associate Performance Tracking")
        
        associate_stats = []
        for assoc, group in df_exec.groupby('Associate ID'):
            floor_visits = calc_floors(group.get('FloorsVisited', group.get('Floors Visited', [])))
            site_visits = group['Site Name'].nunique() if 'Site Name' in group.columns else 0
            
            report_col = group.get('Is Report Visit?', pd.Series([''] * len(group))).astype(str).str.lower().str.strip()
            mark_yes = len(report_col[report_col.isin(['yes', 'y', 'true'])])
            sugg_no = len(report_col[report_col.isin(['no', 'n', 'false'])])
            
            pending = len(group[group['Status'] == 'Pending'])
            sent = len(group[group['Status'] == 'Submitted'])
            grand_total = len(group)
            
            associate_stats.append({
                'Associate ID': assoc,
                'Floor Visits': floor_visits,
                'Site Visits': site_visits,
                'Mark (Yes)': mark_yes,
                'Sugg (No)': sugg_no,
                'Pending': pending,
                'Sent': sent,
                'Backlog': pending, 
                'Grand Total': grand_total
            })

        if associate_stats:
            perf_df = pd.DataFrame(associate_stats)
            
            # Add Team Aggregate Row
            total_row = pd.DataFrame([{
                'Associate ID': 'TEAM AGGREGATE',
                'Floor Visits': perf_df['Floor Visits'].sum(),
                'Site Visits': perf_df['Site Visits'].sum(),
                'Mark (Yes)': perf_df['Mark (Yes)'].sum(),
                'Sugg (No)': perf_df['Sugg (No)'].sum(),
                'Pending': perf_df['Pending'].sum(),
                'Sent': perf_df['Sent'].sum(),
                'Backlog': perf_df['Backlog'].sum(),
                'Grand Total': perf_df['Grand Total'].sum()
            }])
            
            perf_df = pd.concat([perf_df, total_row], ignore_index=True)
            
            # --- GENERATE CUSTOM HTML TABLE ---
            html_table = """
            <div style="background-color: #ffffff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-top: 10px; overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; color: #334155;">
                    <thead>
                        <tr style="color: #94a3b8; font-size: 11px; text-transform: uppercase; border-bottom: 2px solid #f1f5f9; letter-spacing: 1px;">
                            <th style="padding: 15px 10px; text-align: left;">Associate ID</th>
                            <th style="padding: 15px 10px;">Floor Visits</th>
                            <th style="padding: 15px 10px;">Site Visits</th>
                            <th style="padding: 15px 10px;">Mark (Yes)</th>
                            <th style="padding: 15px 10px;">Sugg (No)</th>
                            <th style="padding: 15px 10px;">Pending</th>
                            <th style="padding: 15px 10px;">Sent</th>
                            <th style="padding: 15px 10px; color: #3b82f6;">Backlog</th>
                            <th style="padding: 15px 10px;">Grand Total</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for idx, row in perf_df.iterrows():
                is_footer = row['Associate ID'] == 'TEAM AGGREGATE'
                
                if is_footer:
                    # Dark navy footer row
                    row_style = "background-color: #0f172a; color: #ffffff; font-weight: bold;"
                    td_style = "padding: 18px 10px; border-bottom: none;"
                else:
                    # Standard row
                    row_style = "border-bottom: 1px solid #f8fafc; font-weight: 700;"
                    td_style = "padding: 18px 10px;"

                html_table += f"<tr style='{row_style}'>"
                html_table += f"<td style='{td_style} text-align: left; text-transform: uppercase;'>{row['Associate ID']}</td>"
                html_table += f"<td style='{td_style} font-weight: {'bold' if is_footer else '500'}; color: {'#ffffff' if is_footer else '#64748b'};'>{row['Floor Visits']}</td>"
                html_table += f"<td style='{td_style} font-weight: {'bold' if is_footer else '500'}; color: {'#ffffff' if is_footer else '#64748b'};'>{row['Site Visits']}</td>"
                
                # Colored Columns
                html_table += f"<td style='{td_style} color: #10b981;'>{row['Mark (Yes)']}</td>" # Green
                html_table += f"<td style='{td_style} color: #f43f5e;'>{row['Sugg (No)']}</td>" # Red
                html_table += f"<td style='{td_style} color: #f59e0b;'>{row['Pending']}</td>"   # Orange
                
                html_table += f"<td style='{td_style} font-weight: {'bold' if is_footer else '500'}; color: {'#ffffff' if is_footer else '#64748b'};'>{row['Sent']}</td>"
                html_table += f"<td style='{td_style} color: #3b82f6;'>{row['Backlog']}</td>"   # Blue
                
                html_table += f"<td style='{td_style} font-weight: 800; font-size: 16px; color: {'#3b82f6' if is_footer else '#0f172a'};'>{row['Grand Total']}</td>"
                html_table += "</tr>"

            html_table += """
                    </tbody>
                </table>
            </div>
            """
            
            # Render the HTML instead of the default dataframe
            st.markdown(html_table, unsafe_allow_html=True)
            
        else:
            st.info("No associate performance data available for this period.")
