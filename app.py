import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

# ─────────────────────────────────────────
# 1. PAGE CONFIG & CSS
# ─────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Huliot West Zone – Site Visit Analytics",
    page_icon="📊"
)

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 8px 18px;
    }
    
    /* Print Styles for PDF Export (Tab 3) */
    @media print {
        header {display: none !important;}
        footer {display: none !important;}
        .stTabs [data-baseweb="tab-list"] {display: none !important;}
        div[data-testid="stSidebar"] {display: none !important;}
        body {background-color: white !important;}
    }

    /* Custom Insight Cards for Executive View */
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

# ─────────────────────────────────────────
# 2. GOOGLE SHEETS CONNECTION
# ─────────────────────────────────────────
@st.cache_resource
def init_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)

client = init_connection()

SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"

# ─────────────────────────────────────────
# 3. LOAD DATA  (refreshes every 5 minutes)
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(
            f"❌ Cannot open Google Sheet. "
            f"Make sure it is shared with your service-account email.\n\nError: {e}"
        )
        return pd.DataFrame(), pd.DataFrame()

    worksheets = spreadsheet.worksheets()
    visit_frames = []
    master_df    = pd.DataFrame()

    for ws in worksheets:
        title    = ws.title.lower()
        raw_data = ws.get_all_values()

        if not raw_data or len(raw_data) < 2:
            continue

        raw_headers = [str(h).strip() for h in raw_data[0]]
        seen, headers = {}, []
        for h in raw_headers:
            if h in seen:
                seen[h] += 1
                headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                headers.append(h)

        df = pd.DataFrame(raw_data[1:], columns=headers)

        if "master" in title:
            master_df = df
            continue

        if any(skip in title for skip in ["setting", "config", "associate"]):
            continue

        if not df.empty and ("Site Name" in df.columns or "Visit ID" in df.columns):
            df["Source Sheet"] = ws.title
            visit_frames.append(df)

    visits_df = (
        pd.concat(visit_frames, ignore_index=True) if visit_frames else pd.DataFrame()
    )
    return visits_df, master_df

# ─────────────────────────────────────────
# 4. HELPER FUNCTIONS
# ─────────────────────────────────────────
def get_visit_status(row):
    is_report = str(row.get("Is Report Visit?", "")).strip().lower()
    # Adjusted to catch 'Report Sabmishan Date' from your specific file formatting
    sub_date  = str(row.get("Report Submitted Date", row.get("Report Sabmishan Date", ""))).strip().lower()
    
    if is_report in ["no", "false", "n/a", "nan", ""]:
        return "Technical (NA)"
    if sub_date and sub_date not in ["nan", "none", "", "no"]:
        return "Submitted"
    return "Pending"

def calc_floors(series):
    total = 0
    for val in series:
        try:
            total += int(val)
        except Exception:
            total += 1 if str(val).strip() else 0
    return total

def safe_col(df, options):
    for o in options:
        if o in df.columns:
            return o
    return None

def multiselect_filter(df, column, label, key):
    if column not in df.columns:
        return df
    choices = ["All"] + sorted(df[column].astype(str).unique().tolist())
    selected = st.selectbox(label, choices, key=key)
    if selected != "All":
        df = df[df[column].astype(str) == selected]
    return df

# ─────────────────────────────────────────
# 5. LOAD  +  EARLY-EXIT IF EMPTY
# ─────────────────────────────────────────
with st.spinner("Syncing data from Google Sheets …"):
    visits_df, master_df = load_data()

# ─────────────────────────────────────────
# 6. PAGE HEADER
# ─────────────────────────────────────────
st.title("📊 Huliot West Zone – Site Visit Analytics")
st.caption("Live data · refreshes every 5 minutes · Pune | Mumbai | Ahmedabad")
st.markdown("---")

# ─────────────────────────────────────────
# 7. TABS
# ─────────────────────────────────────────
tab_visits, tab_master, tab_exec = st.tabs([
    "📋 Visit Analytics",
    "📁 Master Projects",
    "📄 Executive Report View",
])

# ═══════════════════════════════════════════════════════
# TAB 1 · VISIT ANALYTICS
# ═══════════════════════════════════════════════════════
with tab_visits:
    if visits_df.empty:
        st.warning("No visit log data found in the sheet.")
    else:
        visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)
        visits_df["Month"]  = (
            pd.to_datetime(visits_df["Date of Visit"], errors="coerce")
            .dt.strftime("%b %Y")
            .fillna("Unknown")
        )

        st.subheader("Filters")
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1: filtered_v = multiselect_filter(visits_df.copy(), "Source Sheet", "Sheet",      "f_sheet")
        with fc2: filtered_v = multiselect_filter(filtered_v,       "Month",        "Month",      "f_month")
        with fc3: filtered_v = multiselect_filter(filtered_v,       "Status",       "Status",     "f_status")
        with fc4: filtered_v = multiselect_filter(filtered_v,       "Associate ID", "Associate",  "f_assoc")
        with fc5: filtered_v = multiselect_filter(filtered_v,       "Site Name",    "Site Name",  "f_site")

        total_visits = len(filtered_v)
        pending      = len(filtered_v[filtered_v["Status"] == "Pending"])
        submitted    = len(filtered_v[filtered_v["Status"] == "Submitted"])
        tech_na      = len(filtered_v[filtered_v["Status"] == "Technical (NA)"])
        sub_df = filtered_v[filtered_v["Status"] == "Submitted"]
        floors_col = "FloorsVisited" if "FloorsVisited" in sub_df.columns else "Floors Visited"
        total_floors = calc_floors(sub_df.get(floors_col, pd.Series(dtype=str)))

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Visits",    total_visits)
        k2.metric("Pending Reports", pending)
        k3.metric("Technical (NA)",  tech_na)
        k4.metric("Submitted",       submitted)
        k5.metric("Floors Covered",  total_floors)
        st.markdown("---")

        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("##### Visits Per Month")
            month_counts = filtered_v["Month"].value_counts().rename_axis("Month").reset_index(name="Visits")
            fig_month = px.bar(month_counts, x="Month", y="Visits", color_discrete_sequence=["#185FA5"])
            fig_month.update_layout(margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig_month, use_container_width=True)
        with ch2:
            st.markdown("##### Visit Status Breakdown")
            status_counts = filtered_v["Status"].value_counts().rename_axis("Status").reset_index(name="Count")
            fig_status = px.pie(status_counts, names="Status", values="Count", hole=0.45, color_discrete_sequence=["#0F6E56", "#BA7517", "#888780"])
            fig_status.update_layout(margin=dict(t=10, b=10), height=280)
            st.plotly_chart(fig_status, use_container_width=True)

        st.markdown("##### Top Sites by Visit Count")
        site_counts = filtered_v["Site Name"].value_counts().nlargest(8).rename_axis("Site Name").reset_index(name="Visits")
        fig_sites = px.bar(site_counts, x="Visits", y="Site Name", orientation="h", color_discrete_sequence=["#1D9E75"])
        fig_sites.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=10, b=10), height=300)
        st.plotly_chart(fig_sites, use_container_width=True)

        st.subheader("Visit Records")
        display_cols = [c for c in ["Source Sheet", "Visit ID", "Site Name", "Tower Name", "FloorsVisited", "Floors Visited", "Associate ID", "Date of Visit", "Status", "Report Sabmishan Date", "Report Submitted Date", "Comment"] if c in filtered_v.columns]
        st.dataframe(filtered_v[display_cols].astype(str), use_container_width=True)

# ═══════════════════════════════════════════════════════
# TAB 2 · MASTER PROJECTS
# ═══════════════════════════════════════════════════════
with tab_master:
    if master_df.empty:
        st.warning("No Master sheet found in the spreadsheet.")
    else:
        col_state = safe_col(master_df, ["STATE", "State"])
        col_dist  = safe_col(master_df, ["DISTRICT / CITY", "DISTRICT", "District"])
        col_stat  = safe_col(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
        col_tech  = safe_col(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
        col_sale  = safe_col(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
        col_distr = safe_col(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])
        col_ong   = safe_col(master_df, ["VISIT ONGOING", "Visit Ongoing"])

        st.subheader("Filters")
        mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
        filtered_m = master_df.copy()
        cols_map = {
            mc1: (col_state, "State",       "m_state"),
            mc2: (col_dist,  "District",    "m_dist"),
            mc3: (col_stat,  "Proj Status", "m_stat"),
            mc4: (col_tech,  "Tech Person", "m_tech"),
            mc5: (col_sale,  "Sales",       "m_sale"),
            mc6: (col_distr, "Distributor", "m_distr"),
        }
        for col_widget, (col_name, label, key) in cols_map.items():
            if col_name:
                with col_widget:
                    filtered_m = multiselect_filter(filtered_m, col_name, label, key)

        total_proj   = len(filtered_m)
        active_proj  = 0
        if col_ong:
            active_proj = len(filtered_m[filtered_m[col_ong].astype(str).str.lower().isin(["yes", "y", "ongoing"])])
        unique_states = filtered_m[col_state].nunique() if col_state else 0
        teams_set = set()
        if col_tech: teams_set.update(filtered_m[col_tech].dropna().astype(str))
        if col_sale: teams_set.update(filtered_m[col_sale].dropna().astype(str))
        team_count = len([x for x in teams_set if x.strip() and x.lower() not in ["nan", "none", ""]])

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Projects",         total_proj)
        k2.metric("Active / Ongoing",       active_proj)
        k3.metric("States Covered",         unique_states)
        k4.metric("Tech + Sales Personnel", team_count)
        st.markdown("---")

        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown("##### Projects by State")
            if col_state:
                state_c = filtered_m[col_state].value_counts().rename_axis("State").reset_index(name="Count")
                fig_state = px.bar(state_c, x="State", y="Count", color_discrete_sequence=["#1D9E75"])
                fig_state.update_layout(margin=dict(t=10, b=10), height=280)
                st.plotly_chart(fig_state, use_container_width=True)
        with mc2:
            st.markdown("##### Project Status Distribution")
            if col_stat:
                stat_c = filtered_m[col_stat].value_counts().rename_axis("Status").reset_index(name="Count")
                fig_pstat = px.pie(stat_c, names="Status", values="Count", hole=0.45, color_discrete_sequence=["#185FA5", "#1D9E75", "#EF9F27", "#888780"])
                fig_pstat.update_layout(margin=dict(t=10, b=10), height=280)
                st.plotly_chart(fig_pstat, use_container_width=True)

        st.subheader("Master Projects Directory")
        st.dataframe(filtered_m.astype(str), use_container_width=True)

# ═══════════════════════════════════════════════════════
# TAB 3 · EXECUTIVE PDF REPORT VIEW
# ═══════════════════════════════════════════════════════
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
            floors_col = "FloorsVisited" if "FloorsVisited" in group.columns else "Floors Visited"
            floor_visits = calc_floors(group.get(floors_col, pd.Series(dtype=str)))
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
