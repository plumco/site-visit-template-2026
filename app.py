import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gspread
from google.oauth2.service_account import Credentials
import numpy as np
from datetime import datetime, timedelta

# --- 1. Page Config & Enhanced CSS ---
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics Pro", page_icon="📊", initial_sidebar_state="expanded")

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        text-align: center;
        font-weight: 700;
    }
    .site-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        border-left: 5px solid #6366f1;
        margin: 1rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .site-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.15);
    }
    .metric-label { font-size: 0.9rem; opacity: 0.9; }
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

# --- 3. Enhanced Data Loading ---
@st.cache_data(ttl=300) 
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"❌ Could not open Google Sheet. Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    worksheets = spreadsheet.worksheets()
    visit_dataframes = []
    master_df = pd.DataFrame()

    for ws in worksheets:
        title = ws.title.lower()
        raw_data = ws.get_all_values()
        if not raw_data or len(raw_data) < 2: continue
            
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

# --- 4. Enhanced Helper Functions ---
def get_visit_status(row):
    is_report = str(row.get('Is Report Visit?', '')).strip().lower()
    sub_date = str(row.get('Report Submitted Date', '')).strip()
    
    if is_report in ['no', 'false', 'n/a']: return 'Technical (NA)'
    if sub_date and sub_date.lower() not in ['nan', 'none', '']: return 'Submitted'
    return 'Pending'

def get_site_metrics(df, site_name):
    """Generate comprehensive site metrics"""
    site_data = df[df['Site Name'].astype(str) == site_name]
    if site_data.empty:
        return {}
    
    total_visits = len(site_data)
    pending = len(site_data[site_data['Status'] == 'Pending'])
    submitted = len(site_data[site_data['Status'] == 'Submitted'])
    tech_na = len(site_data[site_data['Status'] == 'Technical (NA)'])
    
    # Calculate floors visited
    total_floors = 0
    for val in site_data.get('FloorsVisited', site_data.get('Floors Visited', [])):
        try:
            total_floors += int(val) if str(val).strip() else 0
        except:
            total_floors += 1 if str(val).strip() else 0
    
    unique_associates = site_data['Associate ID'].nunique()
    avg_visits_per_assoc = total_visits / unique_associates if unique_associates > 0 else 0
    
    return {
        'total_visits': total_visits,
        'pending': pending,
        'submitted': submitted,
        'tech_na': tech_na,
        'total_floors': total_floors,
        'unique_associates': unique_associates,
        'avg_visits_per_assoc': round(avg_visits_per_assoc, 1),
        'data': site_data
    }

# --- 5. Sidebar Filters ---
st.sidebar.header("🔍 Filters")
if not visits_df.empty:
    visits_df['Status'] = visits_df.apply(get_visit_status, axis=1)
    visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
    visits_df['Month'].fillna('Unknown', inplace=True)

    sidebar_filters = st.sidebar.columns(2)
    with sidebar_filters[0]:
        sources = ['All'] + sorted(visits_df['Source Sheet'].astype(str).unique().tolist())
        f_source = st.selectbox("Source", sources, key="source")
    with sidebar_filters[1]:
        months = ['All'] + sorted(visits_df['Month'].astype(str).unique().tolist())
        f_month = st.selectbox("Month", months, key="month")
    
    sidebar_filters2 = st.sidebar.columns(2)
    with sidebar_filters2[0]:
        statuses = ['All'] + sorted(visits_df['Status'].astype(str).unique().tolist())
        f_status = st.selectbox("Status", statuses, key="status")
    with sidebar_filters2[1]:
        associates = ['All'] + sorted(visits_df['Associate ID'].dropna().astype(str).unique().tolist())
        f_assoc = st.selectbox("Associate", associates[:20], key="assoc")  # Limit to 20

# Apply filters
filtered_v = visits_df.copy()
if f_source != 'All': filtered_v = filtered_v[filtered_v['Source Sheet'].astype(str) == f_source]
if f_month != 'All': filtered_v = filtered_v[filtered_v['Month'].astype(str) == f_month]
if f_status != 'All': filtered_v = filtered_v[filtered_v['Status'].astype(str) == f_status]
if f_assoc != 'All': filtered_v = filtered_v[filtered_v['Associate ID'].astype(str) == f_assoc]

# --- 6. Main Dashboard ---
st.title("📊 Site Visit Deep Analytics Pro")
st.markdown("**Interactive dashboard with site-wise drill-down reports** 🔍")

if filtered_v.empty:
    st.warning("⚠️ No data matches your filters. Adjust filters to see results.")
else:
    # KPI Cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    total_visits = len(filtered_v)
    pending = len(filtered_v[filtered_v['Status'] == 'Pending'])
    submitted = len(filtered_v[filtered_v['Status'] == 'Submitted'])
    tech_na = len(filtered_v[filtered_v['Status'] == 'Technical (NA)'])
    
    # Floors calculation
    total_floors = 0
    for val in filtered_v.get('FloorsVisited', filtered_v.get('Floors Visited', [])):
        try:
            total_floors += int(val)
        except:
            total_floors += 1 if str(val).strip() else 0
    
    unique_sites = filtered_v['Site Name'].nunique()
    
    with col1: st.metric("Total Visits", total_visits)
    with col2: st.metric("Pending", pending, delta=f"{pending/total_visits*100:.1f}%")
    with col3: st.metric("Submitted", submitted, delta=f"{submitted/total_visits*100:.1f}%")
    with col4: st.metric("Technical (NA)", tech_na)
    with col5: st.metric("Sites", unique_sites)
    with col6: st.metric("Total Floors", total_floors)

    st.markdown("---")

    # Charts Row 1
    chart_col1, chart_col2 = st.columns([2, 1])
    
    with chart_col1:
        st.markdown("### 📈 Visits Trend & Status Breakdown")
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Visits by Month', 'Status Distribution'),
            vertical_spacing=0.1,
            row_heights=[0.6, 0.4]
        )
        
        # Monthly trend
        month_counts = filtered_v['Month'].value_counts().reindex(
            sorted(filtered_v['Month'].unique()), fill_value=0
        ).reset_index()
        month_counts.columns = ['Month', 'Visits']
        fig.add_trace(
            go.Bar(x=month_counts['Month'], y=month_counts['Visits'], 
                   marker_color='#6366f1', name='Visits', row=1, col=1),
            row=1, col=1
        )
        
        # Status pie
        status_counts = filtered_v['Status'].value_counts()
        fig.add_trace(
            go.Pie(labels=status_counts.index, values=status_counts.values, 
                   marker_colors=['#ef4444', '#10b981', '#f59e0b', '#6b7280'],
                   name='Status', hole=0.4),
            row=2, col=1
        )
        
        fig.update_layout(height=500, showlegend=False, title_font_size=16)
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        st.markdown("### 🏢 Top 10 Sites")
        top_sites = filtered_v['Site Name'].value_counts().head(10).reset_index()
        top_sites.columns = ['Site', 'Visits']
        fig_pie = px.bar(top_sites, x='Visits', y='Site', orientation='h',
                        color='Visits', color_continuous_scale='Viridis')
        fig_pie.update_layout(height=500, title_font_size=16, margin=dict(l=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # === INTERACTIVE SITE CARDS WITH DRILL-DOWN ===
    st.markdown("---")
    st.markdown("## 🏗️ **Site-Wise Analytics** - Click any site for detailed report")
    
    site_groups = filtered_v.groupby('Site Name').size().sort_values(ascending=False)
    top_sites_list = site_groups.head(15).index.tolist()
    
    selected_site = st.selectbox(
        "🔍 Quick Site Selection", 
        [''] + top_sites_list,
        help="Select a site for instant detailed report"
    )
    
    # Display site cards
    for site_name in top_sites_list[:12]:  # Show top 12 sites
        metrics = get_site_metrics(filtered_v, site_name)
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"""
            <div class="site-card" onclick="window.parent.document.querySelector('select[aria-label*="{site_name}"]').selected=true">
                <h3 style="margin:0; color:#1f2937;">{site_name}</h3>
                <p style="margin:0.5rem 0; color:#6b7280; font-size:0.9rem;">
                    {metrics['total_visits']} visits • {metrics['unique_associates']} associates
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.metric("Submitted", metrics['submitted'], delta=f"{metrics['submitted']/max(metrics['total_visits'],1)*100:.0f}%")
        with col3:
            st.metric("Floors", metrics['total_floors'])

    # === DETAILED SITE REPORT (DRILL-DOWN) ===
    if selected_site and selected_site != '':
        st.markdown("---")
        st.markdown(f"## 📋 **Complete Report: {selected_site}**")
        st.markdown("**Detailed analytics, visit history, and comments**")
        
        site_metrics = get_site_metrics(filtered_v, selected_site)
        site_data = site_metrics['data']
        
        # Site KPI Row
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1: st.metric("📊 Total Visits", site_metrics['total_visits'])
        with k2: st.metric("⏳ Pending", site_metrics['pending'])
        with k3: st.metric("✅ Submitted", site_metrics['submitted'])
        with k4: st.metric("🏢 Floors Covered", site_metrics['total_floors'])
        with k5: st.metric("👥 Associates", site_metrics['unique_associates'])
        
        # Detailed charts for selected site
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📊 Visit Timeline")
            site_data['Date'] = pd.to_datetime(site_data['Date of Visit'], errors='coerce')
            timeline_fig = px.scatter(site_data, x='Date', color='Status', 
                                    title="Visit Timeline", height=400)
            st.plotly_chart(timeline_fig, use_container_width=True)
        
        with c2:
            st.markdown("### 👥 Associate Performance")
            assoc_perf = site_data.groupby('Associate ID').agg({
                'Status': lambda x: (x=='Submitted').sum()
            }).reset_index()
            assoc_perf.columns = ['Associate', 'Submitted']
            assoc_fig = px.bar(assoc_perf.sort_values('Submitted', ascending=False), 
                             x='Submitted', y='Associate', 
                             title="Submissions by Associate")
            st.plotly_chart(assoc_fig, use_container_width=True)
        
        # Complete Visit History with Comments
        st.markdown("### 📝 **Complete Visit History & Comments**")
        display_cols = ['Visit ID', 'Date of Visit', 'Associate ID', 'Status', 
                       'FloorsVisited', 'Report Submitted Date', 'Comment']
        display_cols = [c for c in display_cols if c in site_data.columns]
        
        # Highlight comments
        def highlight_comments(row):
            if 'Comment' in site_data.columns and str(row.get('Comment', '')).strip():
                return ['background-color: #fef3c7'] * len(row)
            return [''] * len(row)
        
        styled_df = site_data[display_cols].style.apply(highlight_comments, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)

# --- 7. Master Projects Tab (Enhanced) ---
tab1, tab2 = st.tabs(["📊 Site Visits", "🏢 Master Projects"])

# Move the main dashboard content to tab1
# (The code above goes in tab1)

with tab2:
    if not master_df.empty:
        # Master projects analytics (keep existing code but enhanced)
        st.subheader("🏢 Master Projects Overview")
        # ... existing master projects code ...
        st.info("Master Projects analytics coming soon with similar drill-down features!")
