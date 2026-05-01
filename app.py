import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Page Config & CSS ---
st.set_page_config(layout="wide", page_title="Monthly Performance Report", page_icon="📊")

# Custom CSS for the PDF/Report look
st.markdown("""
<style>
    /* Clean up default Streamlit padding for a more report-like feel */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Hide top header bar for a cleaner print */
    header {visibility: hidden;}
    
    /* Clean Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 10px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #64748b;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #0f172a !important;
        border-bottom: 3px solid #3b82f6 !important;
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

# --- 3. Load Data ---
@st.cache_data(ttl=300) 
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Connection Error: {e}")
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
        try: total += int(val)
        except: total += 1 if str(val).strip() else 0
    return total

def generate_delta_html(current, prev):
    if prev == 0: return f"<span style='background: #ecfdf5; color: #10b981; padding: 3px 8px; border-radius: 20px; font-weight: 600;'>↗ {current} New</span>"
    diff = current - prev
    if diff > 0: return f"<span style='background: #ecfdf5; color: #10b981; padding: 3px 8px; border-radius: 20px; font-weight: 600;'>↗ {diff} Increase</span>"
    elif diff < 0: return f"<span style='background: #fff1f2; color: #f43f5e; padding: 3px 8px; border-radius: 20px; font-weight: 600;'>↘ {abs(diff)} Decrease</span>"
    else: return f"<span style='background: #f1f5f9; color: #64748b; padding: 3px 8px; border-radius: 20px; font-weight: 600;'>→ No Change</span>"

# --- 5. UI Setup ---
tab_visits, tab_master, tab_exec = st.tabs(["📊 Visit Analytics", "📈 Master Projects", "📑 Executive Report View"])

# ==========================================
# TAB 1 & 2: KEPT STANDARD FOR APP USAGE
# ==========================================
with tab_visits:
    if not visits_df.empty:
        visits_df['Status'] = visits_df.apply(get_visit_status, axis=1)
        visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
        visits_df['Month'].fillna('Unknown', inplace=True)
        st.subheader("Visit Records Filter")
        # Filters omitted for brevity in this snippet to focus on Dashboard, but keeping dataframe
        display_cols = [c for c in ['Source Sheet', 'Visit ID', 'Site Name', 'Tower Name', 'FloorsVisited', 'Associate ID', 'Date of Visit', 'Status', 'Report Submitted Date', 'Comment'] if c in visits_df.columns]
        st.dataframe(visits_df[display_cols].astype(str), use_container_width=True)

with tab_master:
    if not master_df.empty:
        st.subheader("Master Projects Directory")
        st.dataframe(master_df.astype(str), use_container_width=True)

# ==========================================
# TAB 3: THE NEW PDF-STYLE EXECUTIVE REPORT
# ==========================================
with tab_exec:
    if visits_df.empty:
        st.warning("No data available for Executive Dashboard.")
    else:
        st.markdown(f"<h1 style='color: #0f172a; margin-bottom: 0px;'>Monthly Performance Report</h1><p style='color: #64748b; margin-top: 0px; font-size: 15px;'>Multi-month associate performance tracking & field analytics</p>", unsafe_allow_html=True)
        
        all_months_exec = ['All Time'] + list(visits_df['Month'].astype(str).unique())
        selected_month = st.selectbox("Select Reporting Period", all_months_exec, key="exec_month_filter")
        
        df_exec = visits_df.copy()
        df_prev = pd.DataFrame()

        # Month over Month Logic
        if selected_month != 'All Time':
            df_exec = df_exec[df_exec['Month'] == selected_month]
            try:
                curr_dt = pd.to_datetime(selected_month, format='%b %Y')
                prev_dt = curr_dt - pd.DateOffset(months=1)
                prev_str = prev_dt.strftime('%b %Y')
                if prev_str in visits_df['Month'].values:
                    df_prev = visits_df[visits_df['Month'] == prev_str]
            except:
                pass

        # Calculate Current Metrics
        curr_tower = len(df_exec)
        curr_site = df_exec['Site Name'].nunique() if 'Site Name' in df_exec.columns else 0
        curr_sent = len(df_exec[df_exec['Status'] == 'Submitted'])
        curr_pend = len(df_exec[df_exec['Status'] == 'Pending'])
        
        # Calculate Previous Metrics
        prev_tower = len(df_prev)
        prev_site = df_prev['Site Name'].nunique() if 'Site Name' in df_prev.columns and not df_prev.empty else 0
        prev_sent = len(df_prev[df_prev['Status'] == 'Submitted']) if not df_prev.empty else 0
        prev_pend = len(df_prev[df_prev['Status'] == 'Pending']) if not df_prev.empty else 0

        # --- HTML KPI CARDS ---
        html_cards = f"""
        <div style="display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;">
            <!-- Card 1 -->
            <div style="flex: 1; min-width: 200px; background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #f1f5f9;">
                <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <div style="width: 55px; height: 55px; border-radius: 14px; background: #e0e7ff; color: #4f46e5; display: flex; align-items: center; justify-content: center; font-size: 24px;">🏢</div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Total Tower Visits</div>
                        <div style="font-size: 32px; font-weight: 900; color: #0f172a; line-height: 1;">{curr_tower}</div>
                    </div>
                </div>
                <div style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">vs. Last Month &nbsp; {generate_delta_html(curr_tower, prev_tower)}</div>
            </div>
            <!-- Card 2 -->
            <div style="flex: 1; min-width: 200px; background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #f1f5f9;">
                <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <div style="width: 55px; height: 55px; border-radius: 14px; background: #dcfce7; color: #16a34a; display: flex; align-items: center; justify-content: center; font-size: 24px;">📍</div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Total Site Visits</div>
                        <div style="font-size: 32px; font-weight: 900; color: #0f172a; line-height: 1;">{curr_site}</div>
                    </div>
                </div>
                <div style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">vs. Last Month &nbsp; {generate_delta_html(curr_site, prev_site)}</div>
            </div>
            <!-- Card 3 -->
            <div style="flex: 1; min-width: 200px; background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #f1f5f9;">
                <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <div style="width: 55px; height: 55px; border-radius: 14px; background: #e0f2fe; color: #0284c7; display: flex; align-items: center; justify-content: center; font-size: 24px;">📄</div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Total Reports Sent</div>
                        <div style="font-size: 32px; font-weight: 900; color: #0f172a; line-height: 1;">{curr_sent}</div>
                    </div>
                </div>
                <div style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">vs. Last Month &nbsp; {generate_delta_html(curr_sent, prev_sent)}</div>
            </div>
            <!-- Card 4 -->
            <div style="flex: 1; min-width: 200px; background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid #f1f5f9;">
                <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <div style="width: 55px; height: 55px; border-radius: 14px; background: #ffedd5; color: #ea580c; display: flex; align-items: center; justify-content: center; font-size: 24px;">⏱️</div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">Pending Reports</div>
                        <div style="font-size: 32px; font-weight: 900; color: #0f172a; line-height: 1;">{curr_pend}</div>
                    </div>
                </div>
                <div style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 12px;">vs. Last Month &nbsp; {generate_delta_html(curr_pend, prev_pend)}</div>
            </div>
        </div>
        """
        st.markdown(html_cards, unsafe_allow_html=True)

        # --- HIGHLIGHTS BANNER ---
        site_counts = df_exec.groupby('Associate ID')['Site Name'].nunique()
        top_site_assoc = site_counts.idxmax() if not site_counts.empty else "N/A"
        top_site_val = site_counts.max() if not site_counts.empty else 0

        sent_counts = df_exec[df_exec['Status'] == 'Submitted']['Associate ID'].value_counts()
        top_sent_assoc = sent_counts.idxmax() if not sent_counts.empty else "N/A"
        top_sent_val = sent_counts.max() if not sent_counts.empty else 0

        pend_counts = df_exec[df_exec['Status'] != 'Submitted']['Associate ID'].value_counts()
        top_pend_assoc = pend_counts.idxmax() if not pend_counts.empty else "N/A"
        top_pend_val = pend_counts.max() if not pend_counts.empty else 0

        html_highlights = f"""
        <div style="display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;">
            <div style="flex: 1; background: #f0f9ff; border-radius: 12px; padding: 18px; display: flex; align-items: center; gap: 15px; border: 1px solid #e0f2fe;">
                <div style="font-size: 28px;">🌍</div>
                <div>
                    <div style="font-weight: 800; color: #0369a1; font-size: 15px;">Highest Coverage</div>
                    <div style="color: #0ea5e9; font-size: 14px;">{top_site_assoc} ({top_site_val} Sites)</div>
                </div>
            </div>
            <div style="flex: 1; background: #f0fdf4; border-radius: 12px; padding: 18px; display: flex; align-items: center; gap: 15px; border: 1px solid #dcfce7;">
                <div style="font-size: 28px;">🚀</div>
                <div>
                    <div style="font-weight: 800; color: #15803d; font-size: 15px;">Highest Productivity</div>
                    <div style="color: #22c55e; font-size: 14px;">{top_sent_assoc} ({top_sent_val} Sent)</div>
                </div>
            </div>
            <div style="flex: 1; background: #fff1f2; border-radius: 12px; padding: 18px; display: flex; align-items: center; gap: 15px; border: 1px solid #ffe4e6;">
                <div style="font-size: 28px;">⏳</div>
                <div>
                    <div style="font-weight: 800; color: #be123c; font-size: 15px;">Critical Gaps</div>
                    <div style="color: #f43f5e; font-size: 14px;">{top_pend_assoc} ({top_pend_val} Pending)</div>
                </div>
            </div>
        </div>
        """
        st.markdown(html_highlights, unsafe_allow_html=True)

        # --- CHARTS & TOP SITES ROW ---
        col_c1, col_c2, col_c3 = st.columns([1.5, 2, 1])
        
        with col_c1:
            st.markdown("<h4 style='color: #0f172a; font-size: 16px; margin-bottom: 0;'>Reports Sent to Client</h4>", unsafe_allow_html=True)
            sent_data = df_exec[df_exec['Status'] == 'Submitted']['Associate ID'].value_counts().reset_index()
            sent_data.columns = ['Associate ID', 'Reports']
            if not sent_data.empty:
                fig_sent = px.bar(sent_data, x='Reports', y='Associate ID', orientation='h')
                fig_sent.update_traces(marker_color='#3b82f6', marker_line_width=0, opacity=1, width=0.4)
                fig_sent.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=None),
                    yaxis=dict(showgrid=False, title=None, tickfont=dict(color='#0f172a', size=13, weight='bold')),
                    margin=dict(l=0, r=0, t=10, b=0), height=300, yaxis_categoryorder='total ascending'
                )
                st.plotly_chart(fig_sent, use_container_width=True)

        with col_c2:
            st.markdown("<h4 style='color: #0f172a; font-size: 16px; margin-bottom: 0;'><span style='color: #6366f1;'>●</span> Tower &nbsp; <span style='color: #10b981;'>●</span> Site Visits</h4>", unsafe_allow_html=True)
            t_counts = df_exec['Associate ID'].value_counts().reset_index()
            t_counts.columns = ['Associate', 'Tower']
            s_counts = df_exec.groupby('Associate ID')['Site Name'].nunique().reset_index()
            s_counts.columns = ['Associate', 'Site']
            merged_bar = pd.merge(t_counts, s_counts, on='Associate', how='outer').fillna(0)
            
            if not merged_bar.empty:
                fig_breakdown = px.bar(
                    merged_bar, x=['Tower', 'Site'], y='Associate', barmode='group', orientation='h',
                    color_discrete_map={'Tower': '#6366f1', 'Site': '#10b981'}
                )
                fig_breakdown.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
                    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=None),
                    yaxis=dict(showgrid=False, title=None, tickfont=dict(color='#0f172a', size=13, weight='bold')),
                    margin=dict(l=0, r=0, t=10, b=0), height=300, yaxis_categoryorder='total ascending'
                )
                st.plotly_chart(fig_breakdown, use_container_width=True)

        with col_c3:
            st.markdown("<h4 style='color: #0f172a; font-size: 16px; margin-bottom: 5px;'>Top Sites Priority</h4><p style='font-size: 12px; color: #64748b; margin-top: 0px;'>Most visited projects</p>", unsafe_allow_html=True)
            if 'Site Name' in df_exec.columns:
                top_sites = df_exec['Site Name'].value_counts().head(5)
                html_sites = ""
                for i, (site, count) in enumerate(top_sites.items(), 1):
                    arrow = "↗" if i <= 2 else "↘" if i == 5 else "→"
                    color = "#10b981" if i <= 2 else "#f43f5e" if i == 5 else "#94a3b8"
                    html_sites += f"""
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; background: white; padding: 10px; border-radius: 12px; border: 1px solid #f8fafc; box-shadow: 0 2px 5px rgba(0,0,0,0.02);">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="background: #0f172a; color: white; border-radius: 8px; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px;">{i}</div>
                            <div>
                                <div style="color: #0f172a; font-weight: 700; font-size: 13px;">{site}</div>
                                <div style="color: #94a3b8; font-size: 11px;">{count} Total Visits</div>
                            </div>
                        </div>
                        <div style="color: {color}; font-weight: bold; font-size: 14px;">{arrow}</div>
                    </div>
                    """
                st.markdown(html_sites, unsafe_allow_html=True)

        st.markdown("---")

        # --- DETAILED PERFORMANCE TABLE ---
        st.markdown("<h4 style='color: #0f172a; font-size: 16px; text-transform: uppercase;'>Detailed Performance Breakdown</h4><p style='font-size: 12px; color: #64748b; margin-top: 0px; margin-bottom: 20px;'>Individual associate activity log and conversion metrics</p>", unsafe_allow_html=True)
        
        associate_stats = []
        for assoc, group in df_exec.groupby('Associate ID'):
            sub_group = group[group['Status'] == 'Submitted']
            floor_v = calc_floors(sub_group.get('FloorsVisited', sub_group.get('Floors Visited', [])))
            site_v = group['Site Name'].nunique() if 'Site Name' in group.columns else 0
            
            rep_col = group.get('Is Report Visit?', pd.Series([''] * len(group))).astype(str).str.lower().str.strip()
            yes = len(rep_col[rep_col.isin(['yes', 'y', 'true'])])
            no = len(group) - yes 
            
            pend = len(group[group['Status'] == 'Pending'])
            sent = len(group[group['Status'] == 'Submitted'])
            backlog = max(0, yes - sent - pend)
            grand = len(group)
            
            associate_stats.append({'Associate ID': assoc, 'Floor Visits': floor_v, 'Site Visits': site_v, 'Mark (Yes)': yes, 'Sugg (No)': no, 'Pending': pend, 'Sent': sent, 'Backlog': backlog, 'Grand Total': grand})

        if associate_stats:
            perf_df = pd.DataFrame(associate_stats)
            tot_row = pd.DataFrame([{
                'Associate ID': 'TEAM TOTALS', 'Floor Visits': perf_df['Floor Visits'].sum(),
                'Site Visits': df_exec['Site Name'].nunique() if 'Site Name' in df_exec.columns else 0, 
                'Mark (Yes)': perf_df['Mark (Yes)'].sum(), 'Sugg (No)': perf_df['Sugg (No)'].sum(),
                'Pending': perf_df['Pending'].sum(), 'Sent': perf_df['Sent'].sum(),
                'Backlog': perf_df['Backlog'].sum(), 'Grand Total': perf_df['Grand Total'].sum()
            }])
            perf_df = pd.concat([perf_df, tot_row], ignore_index=True)
            
            html_table = """
            <div style="background-color: white; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03); border: 1px solid #f1f5f9; overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: center; font-family: 'Segoe UI', sans-serif; font-size: 14px; color: #334155;">
                    <thead>
                        <tr style="color: #94a3b8; font-size: 11px; text-transform: uppercase; border-bottom: 2px solid #f8fafc; letter-spacing: 1px;">
                            <th style="padding: 15px 10px; text-align: left;">Associate ID</th>
                            <th style="padding: 15px 10px;">Floor Visits</th>
                            <th style="padding: 15px 10px;">Site Visits</th>
                            <th style="padding: 15px 10px;">Report Mark (Yes)</th>
                            <th style="padding: 15px 10px;">Suggestion (No)</th>
                            <th style="padding: 15px 10px;">Pending</th>
                            <th style="padding: 15px 10px;">Total Sent</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for idx, row in perf_df.iterrows():
                is_ftr = row['Associate ID'] == 'TEAM TOTALS'
                rs = "background-color: #0f172a; color: #ffffff; font-weight: bold; border-radius: 12px;" if is_ftr else "border-bottom: 1px solid #f8fafc; font-weight: 700;"
                td = "padding: 20px 10px;" if not is_ftr else "padding: 20px 10px; border-bottom: none;"

                html_table += f"<tr style='{rs}'>"
                html_table += f"<td style='{td} text-align: left; font-size: 15px;'>{row['Associate ID']}</td>"
                html_table += f"<td style='{td} font-weight: {'800' if is_ftr else '600'}; color: {'#ffffff' if is_ftr else '#475569'};'>{row['Floor Visits']}</td>"
                html_table += f"<td style='{td} font-weight: {'800' if is_ftr else '600'}; color: {'#ffffff' if is_ftr else '#475569'};'>{row['Site Visits']}</td>"
                html_table += f"<td style='{td} color: #10b981; font-weight: 800;'>{row['Mark (Yes)']}</td>" 
                html_table += f"<td style='{td} color: #f43f5e; font-weight: 800;'>{row['Sugg (No)']}</td>" 
                html_table += f"<td style='{td} color: #f59e0b; font-weight: 800;'>{row['Pending']}</td>"   
                html_table += f"<td style='{td} font-weight: 900; font-size: 16px; color: {'#3b82f6' if is_ftr else '#0f172a'};'>{row['Sent']}</td>"
                html_table += "</tr>"

            html_table += "</tbody></table></div>"
            st.markdown(html_table, unsafe_allow_html=True)
