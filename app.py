import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Page Config & CSS ---
st.set_page_config(layout="wide", page_title="Executive Performance Report", page_icon="📄")

# Advanced CSS for Print-Ready PDF Layout and Custom Cards
st.markdown("""
<style>
    /* Force Light Theme Card Styling */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #f1f5f9;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Print Styles for PDF Export */
    @media print {
        header {display: none !important;}
        footer {display: none !important;}
        .stTabs [data-baseweb="tab-list"] {display: none !important;}
        div[data-testid="stSidebar"] {display: none !important;}
        body {background-color: white !important;}
    }

    /* Custom Insight Cards */
    .insight-card {
        padding: 15px 20px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        gap: 15px;
        font-family: sans-serif;
    }
    .insight-title {font-size: 14px; font-weight: 700; margin: 0;}
    .insight-value {font-size: 13px; font-weight: 500; margin: 0; opacity: 0.8;}
</style>
""", unsafe_allow_html=True)

# --- 2. Google Sheets Connection ---
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

client = init_connection()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304" 

# --- 3. Load Data ---
@st.cache_data(ttl=300) 
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error("Connection Error. Ensure Secrets are correct.")
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
        if any(skip in title for skip in ['setting', 'config', 'associate']): continue
        if not df.empty and ('Site Name' in df.columns or 'Visit ID' in df.columns):
            df['Source Sheet'] = ws.title
            visit_dataframes.append(df)

    visits_df = pd.concat(visit_dataframes, ignore_index=True) if visit_dataframes else pd.DataFrame()
    return visits_df, master_df

visits_df, master_df = load_data()

# --- Helper Functions ---
def get_visit_status(row):
    is_report = str(row.get('Is Report Visit?', '')).strip().lower()
    sub_date = str(row.get('Report Submitted Date', '')).strip()
    if is_report in ['no', 'false', 'n/a']: return 'Technical (NA)'
    if sub_date and sub_date.lower() not in ['nan', 'none', '']: return 'Submitted'
    return 'Pending'

def calc_floors(series):
    total = 0
    for val in series:
        try: total += int(val)
        except: total += 1 if str(val).strip() else 0
    return total

# Data Prep
if not visits_df.empty:
    visits_df['Status'] = visits_df.apply(get_visit_status, axis=1)
    visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
    visits_df['Month'].fillna('Unknown', inplace=True)

# --- UI Setup ---
st.title("📄 Executive Performance Report")
st.markdown("Multi-month associate performance tracking & field analytics")

tab_visits, tab_master, tab_exec = st.tabs(["📊 Visit Analytics", "📈 Master Projects", "💼 Executive Report View"])

# ==========================================
# TAB 3: EXECUTIVE PDF REPORT VIEW
# ==========================================
with tab_exec:
    if visits_df.empty:
        st.warning("No data available.")
    else:
        # Header Controls
        col_month, col_btn = st.columns([4, 1])
        all_months_exec = ['All Time'] + list(visits_df['Month'].astype(str).unique())
        with col_month:
            selected_month = st.selectbox("Select Reporting Period", all_months_exec, key="exec_month_filter")
        with col_btn:
            st.markdown("<br><p style='text-align: right; font-size: 12px; color: #64748b;'><i>Press Ctrl+P to save as PDF</i></p>", unsafe_allow_html=True)

        df_exec = visits_df.copy()
        if selected_month != 'All Time':
            df_exec = df_exec[df_exec['Month'] == selected_month]

        # Process Performance Data
        associate_stats = []
        for assoc, group in df_exec.groupby('Associate ID'):
            submitted_group = group[group['Status'] == 'Submitted']
            floor_visits = calc_floors(group.get('FloorsVisited', group.get('Floors Visited', []))) # Total floors
            site_visits = group['Site Name'].nunique() if 'Site Name' in group.columns else 0
            
            report_col = group.get('Is Report Visit?', pd.Series([''] * len(group))).astype(str).str.lower().str.strip()
            mark_yes = len(report_col[report_col.isin(['yes', 'y', 'true'])])
            sugg_no = len(group) - mark_yes 
            
            pending = len(group[group['Status'] == 'Pending'])
            sent = len(group[group['Status'] == 'Submitted'])
            backlog = max(0, mark_yes - sent - pending)
            
            associate_stats.append({
                'Associate ID': assoc, 'Floor Visits': floor_visits, 'Site Visits': site_visits,
                'Mark (Yes)': mark_yes, 'Sugg (No)': sugg_no, 'Pending': pending,
                'Sent': sent, 'Backlog': backlog, 'Grand Total': len(group)
            })
            
        perf_df = pd.DataFrame(associate_stats) if associate_stats else pd.DataFrame()

        # 1. 4-Column Main KPIs
        if not perf_df.empty:
            e_kpi1, e_kpi2, e_kpi3, e_kpi4 = st.columns(4)
            e_kpi1.metric("🏢 TOTAL FLOOR VISITS", perf_df['Floor Visits'].sum())
            e_kpi2.metric("📍 TOTAL SITE VISITS", df_exec['Site Name'].nunique())
            e_kpi3.metric("📄 TOTAL REPORTS SENT", perf_df['Sent'].sum())
            e_kpi4.metric("⏱️ PENDING REPORTS", perf_df['Pending'].sum() + perf_df['Backlog'].sum())

            # 2. Automated Insight Cards
            st.markdown("<br>", unsafe_allow_html=True)
            i1, i2, i3 = st.columns(3)
            
            best_coverage = perf_df.sort_values('Site Visits', ascending=False).iloc[0]
            best_prod = perf_df.sort_values('Floor Visits', ascending=False).iloc[0]
            worst_gap = perf_df.sort_values('Backlog', ascending=False).iloc[0]

            with i1:
                st.markdown(f"""
                <div class="insight-card" style="background-color: #f0f9ff; border: 1px solid #e0f2fe; color: #0369a1;">
                    <div style="font-size: 24px;">🌍</div>
                    <div><p class="insight-title">Highest Coverage</p><p class="insight-value">{best_coverage['Associate ID']} ({best_coverage['Site Visits']} Sites)</p></div>
                </div>
                """, unsafe_allow_html=True)
            with i2:
                st.markdown(f"""
                <div class="insight-card" style="background-color: #f0fdf4; border: 1px solid #dcfce7; color: #15803d;">
                    <div style="font-size: 24px;">🚀</div>
                    <div><p class="insight-title">Highest Productivity</p><p class="insight-value">{best_prod['Associate ID']} ({best_prod['Floor Visits']} Floors)</p></div>
                </div>
                """, unsafe_allow_html=True)
            with i3:
                st.markdown(f"""
                <div class="insight-card" style="background-color: #fff1f2; border: 1px solid #ffe4e6; color: #be123c;">
                    <div style="font-size: 24px;">⏳</div>
                    <div><p class="insight-title">Critical Gaps (Backlog)</p><p class="insight-value">{worst_gap['Associate ID']} ({worst_gap['Backlog']} Reports)</p></div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

            # 3. Charts Section
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### 📄 Reports Sent to Client")
                fig_sent = px.bar(perf_df.sort_values('Sent', ascending=True), x='Sent', y='Associate ID', orientation='h')
                fig_sent.update_traces(marker_color='#3b82f6', marker_line_radius=5)
                fig_sent.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                                       xaxis_title=None, yaxis_title=None, showlegend=False, height=350)
                st.plotly_chart(fig_sent, use_container_width=True)

            with c2:
                st.markdown("##### 🏢 Tower vs Site Visits Breakdown")
                fig_dual = go.Figure()
                sorted_perf = perf_df.sort_values('Floor Visits', ascending=True)
                fig_dual.add_trace(go.Bar(y=sorted_perf['Associate ID'], x=sorted_perf['Floor Visits'], name='Tower', orientation='h', marker_color='#6366f1'))
                fig_dual.add_trace(go.Bar(y=sorted_perf['Associate ID'], x=sorted_perf['Site Visits'], name='Site', orientation='h', marker_color='#10b981'))
                fig_dual.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                       xaxis_title=None, yaxis_title=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=350)
                st.plotly_chart(fig_dual, use_container_width=True)

            # 4. Stylized Report Table
            st.markdown("##### 📊 Detailed Performance Breakdown")
            
            total_row = pd.DataFrame([{
                'Associate ID': 'TEAM TOTALS', 'Floor Visits': perf_df['Floor Visits'].sum(),
                'Site Visits': df_exec['Site Name'].nunique(), 'Mark (Yes)': perf_df['Mark (Yes)'].sum(),
                'Sugg (No)': perf_df['Sugg (No)'].sum(), 'Pending': perf_df['Pending'].sum(),
                'Sent': perf_df['Sent'].sum(), 'Backlog': perf_df['Backlog'].sum(),
                'Grand Total': perf_df['Grand Total'].sum()
            }])
            display_df = pd.concat([perf_df, total_row], ignore_index=True)
            
            html_table = """
            <div style="background-color: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #f1f5f9; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-top: 10px;">
                <table style="width: 100%; border-collapse: collapse; text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; color: #334155;">
                    <thead>
                        <tr style="color: #64748b; font-size: 11px; font-weight: bold; text-transform: uppercase; border-bottom: 2px solid #f1f5f9; letter-spacing: 0.5px;">
                            <th style="padding: 15px 10px; text-align: left;">Associate ID</th>
                            <th style="padding: 15px 10px;">Floor Visits</th>
                            <th style="padding: 15px 10px;">Site Visits</th>
                            <th style="padding: 15px 10px;">Report Mark (Yes)</th>
                            <th style="padding: 15px 10px;">Suggestion (No)</th>
                            <th style="padding: 15px 10px;">Pending</th>
                            <th style="padding: 15px 10px;">Sent</th>
                            <th style="padding: 15px 10px; color: #3b82f6;">Backlog</th>
                            <th style="padding: 15px 10px;">Total Sent</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for idx, row in display_df.iterrows():
                is_footer = row['Associate ID'] == 'TEAM TOTALS'
                row_style = "background-color: #0f172a; color: #ffffff; font-weight: bold;" if is_footer else "border-bottom: 1px solid #f8fafc; font-weight: 600;"
                td_style = "padding: 16px 10px; border-bottom: none;" if is_footer else "padding: 16px 10px;"

                html_table += f"<tr style='{row_style}'>"
                html_table += f"<td style='{td_style} text-align: left; text-transform: uppercase;'>{row['Associate ID']}</td>"
                html_table += f"<td style='{td_style}'>{row['Floor Visits']}</td>"
                html_table += f"<td style='{td_style}'>{row['Site Visits']}</td>"
                html_table += f"<td style='{td_style} color: {'#10b981' if not is_footer else '#34d399'};'>{row['Mark (Yes)']}</td>" 
                html_table += f"<td style='{td_style} color: {'#f43f5e' if not is_footer else '#fb7185'};'>{row['Sugg (No)']}</td>" 
                html_table += f"<td style='{td_style} color: {'#f59e0b' if not is_footer else '#fbbf24'};'>{row['Pending']}</td>"   
                html_table += f"<td style='{td_style}'>{row['Sent']}</td>"
                html_table += f"<td style='{td_style} color: {'#3b82f6' if not is_footer else '#60a5fa'};'>{row['Backlog']}</td>"   
                html_table += f"<td style='{td_style} font-weight: 800; font-size: 15px;'>{row['Sent']}</td>"
                html_table += "</tr>"

            html_table += "</tbody></table></div>"
            st.markdown(html_table, unsafe_allow_html=True)

# ==========================================
# TAB 1 & 2: REMAIN UNCHANGED (Collapsed for brevity, keep existing code here)
# ==========================================
with tab_visits:
    st.info("Visit Analytics active in background.") # Replace with your original Tab 1 code if needed
with tab_master:
    st.info("Master Projects active in background.") # Replace with your original Tab 2 code if needed
