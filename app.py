import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import requests
from google.oauth2.service_account import Credentials
from html import escape
from datetime import datetime
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────────────────────────
# 1. PAGE CONFIG & DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="Huliot · Site Analytics", page_icon="📡")

# Chart palette
CHART_COLORS = ["#F59E0B", "#38BDF8", "#10B981", "#F43F5E", "#A78BFA", "#34D399", "#FB923C"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap');

/* ── DESIGN TOKENS ───────────────────────────────────────────────────────── */
:root {
  --bg0: #070B14;
  --bg1: #0C1020;
  --bg2: #111828;
  --bg3: #172135;
  --b1:  #1C2B45;
  --b2:  #243555;
  --amb:    #F59E0B;
  --amb-a:  rgba(245,158,11,0.08);
  --amb-b:  rgba(245,158,11,0.20);
  --sky:    #38BDF8;
  --sky-a:  rgba(56,189,248,0.08);
  --grn:    #10B981;
  --grn-a:  rgba(16,185,129,0.08);
  --red:    #F43F5E;
  --red-a:  rgba(244,63,94,0.08);
  --t0: #F1F5F9;
  --t1: #CBD5E1;
  --t2: #64748B;
  --t3: #334155;
  --mono: 'JetBrains Mono', 'Courier New', monospace;
  --sans: 'Outfit', system-ui, sans-serif;
  --r:  4px;
  --rl: 8px;
}

/* ── APP SHELL ───────────────────────────────────────────────────────────── */
.stApp {
  background-color: var(--bg0) !important;
  background-image:
    linear-gradient(rgba(28,43,69,0.17) 1px, transparent 1px),
    linear-gradient(90deg, rgba(28,43,69,0.17) 1px, transparent 1px);
  background-size: 32px 32px;
  font-family: var(--sans) !important;
  color: var(--t1) !important;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg0); }
::-webkit-scrollbar-thumb { background: var(--b2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--amb); }

/* ── SIDEBAR ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--bg1) !important;
  border-right: 1px solid var(--b1) !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown strong,
[data-testid="stSidebar"] .stMarkdown b {
  color: var(--t1) !important;
  font-family: var(--mono) !important;
  font-size: 0.78rem !important;
}
[data-testid="stSidebar"] hr { border-color: var(--b1) !important; margin: 0.75rem 0 !important; }

/* ── HEADER BAR ──────────────────────────────────────────────────────────── */
[data-testid="stHeader"] {
  background: rgba(7,11,20,0.96) !important;
  border-bottom: 1px solid var(--b1) !important;
  backdrop-filter: blur(12px);
}
[data-testid="stDecoration"] { display: none !important; }

/* ── TYPOGRAPHY ──────────────────────────────────────────────────────────── */
h1 {
  font-family: var(--sans) !important;
  font-weight: 900 !important;
  color: var(--t0) !important;
  font-size: 1.8rem !important;
  letter-spacing: -0.025em !important;
}
h2, h3 {
  font-family: var(--sans) !important;
  font-weight: 700 !important;
  color: var(--t0) !important;
}
h4, h5 {
  font-family: var(--mono) !important;
  font-size: 0.68rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--amb) !important;
}
p { font-family: var(--sans) !important; color: var(--t2) !important; font-size: 0.88rem; }
strong, b { color: var(--t0) !important; }

/* ── TABS ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--b1) !important;
  gap: 0 !important;
  padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--t3) !important;
  font-family: var(--mono) !important;
  font-size: 0.7rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  padding: 0.65rem 1.25rem !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  margin-bottom: -1px !important;
  transition: color 0.18s, background 0.18s !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--t1) !important;
  background: var(--amb-a) !important;
}
.stTabs [aria-selected="true"] {
  color: var(--amb) !important;
  border-bottom-color: var(--amb) !important;
  background: transparent !important;
}
.stTabs [data-baseweb="tab-border"],
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }

/* ── KPI METRIC CONTAINERS ───────────────────────────────────────────────── */
[data-testid="metric-container"] {
  background: var(--bg2) !important;
  border: 1px solid var(--b1) !important;
  border-top: 2px solid var(--amb) !important;
  border-radius: var(--r) !important;
  padding: 1rem 1.25rem !important;
  box-shadow: none !important;
  position: relative;
}
[data-testid="metric-container"] label {
  font-family: var(--mono) !important;
  font-size: 0.62rem !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--t2) !important;
  font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
  font-family: var(--mono) !important;
  font-size: 2rem !important;
  font-weight: 700 !important;
  color: var(--t0) !important;
  letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] { font-family: var(--mono) !important; font-size: 0.7rem !important; }

/* ── SELECTBOX ───────────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
  background: var(--bg2) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
  font-family: var(--mono) !important;
  font-size: 0.8rem !important;
  transition: border-color 0.18s !important;
}
[data-testid="stSelectbox"] > div > div:focus-within {
  border-color: var(--amb) !important;
  box-shadow: 0 0 0 1px var(--amb-b) !important;
}
[data-testid="stSelectbox"] label {
  font-family: var(--mono) !important;
  font-size: 0.62rem !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--t2) !important;
  font-weight: 600 !important;
}
[data-baseweb="list"] {
  background: var(--bg3) !important;
  border: 1px solid var(--b2) !important;
}
[role="option"] { font-family: var(--mono) !important; font-size: 0.8rem !important; color: var(--t1) !important; }
[role="option"]:hover, [aria-selected="true"] { background: var(--amb-a) !important; color: var(--amb) !important; }

/* ── TEXT / PASSWORD INPUTS ──────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
input[type="text"], input[type="password"] {
  background: var(--bg2) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--r) !important;
  color: var(--t0) !important;
  font-family: var(--mono) !important;
  font-size: 0.85rem !important;
}
[data-testid="stTextInput"] input:focus,
input[type="text"]:focus, input[type="password"]:focus {
  border-color: var(--amb) !important;
  box-shadow: 0 0 0 2px var(--amb-b) !important;
  outline: none !important;
}
[data-testid="stTextInput"] label {
  font-family: var(--mono) !important;
  font-size: 0.62rem !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--t2) !important;
  font-weight: 600 !important;
}

/* ── BUTTONS ─────────────────────────────────────────────────────────────── */
.stButton > button {
  background: var(--amb) !important;
  color: #000 !important;
  font-family: var(--mono) !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  border: none !important;
  border-radius: var(--r) !important;
  padding: 0.5rem 1.1rem !important;
  transition: all 0.15s !important;
}
.stButton > button:hover {
  background: #FBBF24 !important;
  box-shadow: 0 0 20px rgba(245,158,11,0.3) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stDownloadButton"] > button {
  background: var(--bg3) !important;
  color: var(--t1) !important;
  border: 1px solid var(--b2) !important;
  font-family: var(--mono) !important;
  font-size: 0.7rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--amb) !important;
  color: var(--amb) !important;
  background: var(--amb-a) !important;
}

/* ── CHECKBOX ────────────────────────────────────────────────────────────── */
.stCheckbox span[class*="label"] {
  font-family: var(--mono) !important;
  font-size: 0.78rem !important;
  color: var(--t1) !important;
}

/* ── DATAFRAME ───────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--b1) !important;
  border-radius: var(--r) !important;
  overflow: hidden;
}

/* ── ALERTS / WARNINGS ───────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  background: var(--bg2) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--r) !important;
  font-family: var(--mono) !important;
  font-size: 0.78rem !important;
  color: var(--t2) !important;
}

/* ── SPINNER ─────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div { border-top-color: var(--amb) !important; }

/* ── HR / DIVIDERS ───────────────────────────────────────────────────────── */
hr { border-color: var(--b1) !important; margin: 1rem 0 !important; }

/* ── EXECUTIVE HIGHLIGHT CARDS ───────────────────────────────────────────── */
.highlight-card {
  padding: 14px 18px;
  border-radius: var(--r);
  font-family: var(--mono);
  margin-top: 10px;
  border-left: 3px solid;
}
.card-blue  { background: var(--sky-a); color: var(--sky); border-color: var(--sky); border: 1px solid rgba(56,189,248,0.18); border-left: 3px solid var(--sky); }
.card-green { background: var(--grn-a); color: var(--grn); border: 1px solid rgba(16,185,129,0.18); border-left: 3px solid var(--grn); }
.card-red   { background: var(--red-a); color: var(--red); border: 1px solid rgba(244,63,94,0.18);  border-left: 3px solid var(--red); }
.card-title { font-size: 0.6rem; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.65; margin-bottom: 7px; font-weight: 600; }
.card-value { font-size: 0.9rem; font-weight: 700; line-height: 1.45; }

/* ── LOGIN FORM ──────────────────────────────────────────────────────────── */
div[data-testid="stForm"] {
  background: var(--bg2) !important;
  border: 1px solid var(--b1) !important;
  border-radius: var(--rl) !important;
  padding: 2.5rem !important;
  box-shadow: 0 0 80px rgba(245,158,11,0.04) !important;
}

/* ── SECTION LABELS (subheader) ──────────────────────────────────────────── */
.section-label {
  font-family: var(--mono);
  font-size: 0.62rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--t2);
  margin-bottom: 0.6rem;
  margin-top: 1rem;
}

/* ── PAGE HEADER ─────────────────────────────────────────────────────────── */
.page-eyebrow {
  font-family: var(--mono);
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--amb);
  margin-bottom: 0.3rem;
  display: flex;
  align-items: center;
  gap: 10px;
}
.page-eyebrow::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--amb), transparent);
  max-width: 120px;
}

/* ── HORIZONTAL INFO TABLE ───────────────────────────────────────────────── */
.horizontal-info-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
.horizontal-info-table th {
  background: var(--bg3);
  color: var(--t2);
  border: 1px solid var(--b1);
  padding: 7px 10px;
  text-align: left;
  font-family: var(--mono);
  font-size: 0.6rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
  white-space: nowrap;
}
.horizontal-info-table td {
  border: 1px solid var(--b1);
  padding: 7px 10px;
  color: var(--t1);
  font-family: var(--mono);
  font-size: 0.78rem;
  vertical-align: top;
}

/* ── FILTER CONTAINER ────────────────────────────────────────────────────── */
.filter-bar {
  background: var(--bg1);
  border: 1px solid var(--b1);
  border-radius: var(--r);
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FIREBASE AUTH
# ─────────────────────────────────────────────────────────────────────────────
FIREBASE_API_KEY = "AIzaSyDuf1MozrcpQmlnbJXa-bm5C2htxRzeZOA"

def firebase_sign_in(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if response.status_code == 200:
            return True, data.get("email", email), None
        else:
            error_message = data.get("error", {}).get("message", "Authentication failed")
            return False, None, error_message
    except Exception as e:
        return False, None, str(e)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN GATE
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    st.markdown("""
    <style>
    .login-eyebrow {
        text-align: center;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: #F59E0B;
        margin-bottom: 0.9rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
    }
    .login-eyebrow::before, .login-eyebrow::after {
        content: "";
        display: inline-block;
        width: 36px;
        height: 1px;
        background: #F59E0B;
        opacity: 0.6;
    }
    .login-title {
        text-align: center;
        font-family: 'Outfit', sans-serif;
        font-size: 2.1rem;
        font-weight: 900;
        color: #F1F5F9;
        letter-spacing: -0.03em;
        margin-bottom: 0.35rem;
        line-height: 1.1;
    }
    .login-sub {
        text-align: center;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #334155;
        letter-spacing: 0.06em;
        margin-bottom: 0;
    }
    .login-wrapper { padding: 2.5rem 0 1.5rem 0; }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1.5, 1])
    with col_center:
        st.markdown("""
        <div class="login-wrapper">
            <div class="login-eyebrow">HULIOT FIELD SYSTEMS</div>
            <div class="login-title">Site Analytics</div>
            <div class="login-sub">authentication required · west zone</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            email    = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="Your password")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            submit   = st.form_submit_button("SIGN IN →", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("Enter both email and password.")
                else:
                    with st.spinner("Authenticating…"):
                        success, user_email, error = firebase_sign_in(email, password)
                    if success:
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"]    = user_email
                        st.rerun()
                    else:
                        error_messages = {
                            "INVALID_LOGIN_CREDENTIALS": "❌ Invalid email or password.",
                            "EMAIL_NOT_FOUND":           "❌ No account found with this email.",
                            "INVALID_PASSWORD":          "❌ Incorrect password.",
                            "USER_DISABLED":             "❌ This account has been disabled.",
                            "TOO_MANY_ATTEMPTS_TRY_LATER": "❌ Too many attempts. Try again later.",
                        }
                        st.error(error_messages.get(error, f"❌ {error}"))

    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
user_email = st.session_state.get("user_email", "")
st.sidebar.markdown(f"<span style='font-family:var(--mono,monospace);font-size:0.72rem;color:#64748B;letter-spacing:0.06em;text-transform:uppercase;'>SIGNED IN AS</span><br><strong style='color:#CBD5E1;font-size:0.82rem;'>{user_email}</strong>", unsafe_allow_html=True)
st.sidebar.markdown("")
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["user_email"]    = None
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()
st.sidebar.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# CHART HELPER
# ─────────────────────────────────────────────────────────────────────────────
def style_chart(fig):
    """Apply Field Command dark theme to every Plotly figure."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="JetBrains Mono, monospace", color="#64748B", size=10),
        margin=dict(l=0, r=0, t=28, b=4),
        legend=dict(
            font=dict(family="JetBrains Mono, monospace", size=9, color="#94A3B8"),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
        ),
    )
    fig.update_xaxes(
        gridcolor="#1C2B45", linecolor="#1C2B45", zeroline=False,
        tickfont=dict(family="JetBrains Mono", size=9, color="#475569"),
    )
    fig.update_yaxes(
        gridcolor="#1C2B45", linecolor="rgba(0,0,0,0)", zeroline=False,
        tickfont=dict(family="JetBrains Mono", size=9, color="#475569"),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def init_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

client    = init_connection()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS  (unchanged logic)
# ─────────────────────────────────────────────────────────────────────────────
def safe_text(value):
    value = str(value).strip()
    if value.lower() in ["nan", "none", "null", "nat", ""]:
        return "-"
    return escape(value)

def make_unique_headers(raw_headers):
    seen, headers = {}, []
    for h in raw_headers:
        h = str(h).strip() or "Blank"
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
            df[col].astype(str)
            .replace({"nan":"","None":"","NaT":"","NaN":"","null":"","Null":""})
            .str.strip()
        )
    return df

def safe_col(df, options):
    if df.empty:
        return None
    for o in options:
        if o in df.columns:
            return o
    return None

def clean_options(series):
    return sorted(
        series.astype(str).str.strip()
        .replace(["nan","None","NaT","","null","Null"], pd.NA)
        .dropna().unique().tolist()
    )

def get_visit_status(row):
    is_report = str(row.get("Is Report Visit?","")).strip().lower()
    sub_date  = str(row.get("Report Submitted Date","")).strip()
    if is_report in ["no","n","false","n/a","na"]:
        return "Technical (NA)"
    if sub_date and sub_date.lower() not in ["nan","none","","nat"]:
        return "Submitted"
    return "Pending"

def parse_floor(val):
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan","none","null","n/a","na","-"]:
        return 0
    try:
        return int(float(val_str))
    except Exception:
        return 1

def find_master_site_col(master_df):
    return safe_col(master_df, ["PROJECT","Project","PROJECT NAME","Project Name","Site Name","SITE NAME","Site"])

def find_visit_site_col(visits_df):
    return safe_col(visits_df, ["Site Name","SITE NAME","PROJECT","Project","PROJECT NAME","Project Name"])

def filter_site(df, site_col, selected_site):
    if df.empty or not site_col:
        return pd.DataFrame()
    return df[df[site_col].astype(str).str.strip().str.lower() == str(selected_site).strip().lower()].copy()

def get_row_value(row, col):
    if col and col in row.index:
        value = str(row.get(col,"")).strip()
        if value and value.lower() not in ["nan","none","null","nat"]:
            return value
    return "-"

def build_horizontal_table(row, columns):
    html = "<table class='horizontal-info-table'><tr>"
    for label, col in columns:
        html += f"<th>{safe_text(label)}</th>"
    html += "</tr><tr>"
    for label, col in columns:
        html += f"<td>{safe_text(get_row_value(row, col))}</td>"
    html += "</tr></table>"
    return html

def df_to_html_table(df):
    if df.empty:
        return "<p>No data found.</p>"
    html = "<table border='1' style='border-collapse:collapse;width:100%;font-size:12px;'>"
    html += "<tr>"
    for col in df.columns:
        html += f"<th style='background:#172135;color:#64748B;padding:8px;text-align:left;border:1px solid #1C2B45;font-size:10px;letter-spacing:0.06em;text-transform:uppercase;'>{safe_text(col)}</th>"
    html += "</tr>"
    for _, row in df.astype(str).iterrows():
        html += "<tr>"
        for col in df.columns:
            html += f"<td style='padding:8px;vertical-align:top;border:1px solid #1C2B45;color:#CBD5E1;font-size:12px;'>{safe_text(row[col])}</td>"
        html += "</tr>"
    html += "</table>"
    return html

def create_excel_compatible_report(site_name, master_df, visit_df, summary_df, last_comment):
    html = f"""
    <html><head><meta charset="UTF-8"></head><body>
        <h2>{safe_text(site_name)} - Site Visit Report</h2>
        <p>Generated On: {datetime.now().strftime("%d-%m-%Y %I:%M %p")}</p>
        <h3>Site Summary</h3>{df_to_html_table(summary_df)}
        <h3>Last Comment</h3><p>{safe_text(last_comment)}</p>
        <h3>MasterProject Details</h3>{df_to_html_table(master_df)}
        <h3>VisitLog Details</h3>{df_to_html_table(visit_df)}
    </body></html>
    """
    return html.encode("utf-8")

def create_print_html_report(site_name, master_row, master_cols_1, master_cols_2, summary_df, visit_df, last_comment):
    html = f"""
    <html><head><meta charset="UTF-8"><title>{safe_text(site_name)} Site Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; color: #111827; }}
        .header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #F59E0B; padding-bottom: 12px; margin-bottom: 18px; }}
        .title {{ font-size: 26px; font-weight: 800; }}
        .subtitle {{ color: #6b7280; font-size: 13px; margin-top: 5px; }}
        .badge {{ background: #F59E0B; color: #000; padding: 8px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; font-family: monospace; }}
        h3 {{ border-left: 4px solid #F59E0B; padding-left: 10px; margin-top: 22px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 14px; }}
        th {{ background: #f3f4f6; border: 1px solid #d1d5db; padding: 7px; text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; }}
        td {{ border: 1px solid #d1d5db; padding: 7px; vertical-align: top; }}
        .comment {{ background: #fffbeb; border: 1px solid #F59E0B; padding: 12px; border-radius: 4px; color: #78350f; font-size: 13px; }}
    </style></head><body>
        <div class="header">
            <div>
                <div class="title">{safe_text(site_name)}</div>
                <div class="subtitle">Site Visit Report | Generated On {datetime.now().strftime("%d-%m-%Y %I:%M %p")}</div>
            </div>
            <div class="badge">HULIOT SITE REPORT</div>
        </div>
        <h3>1. Site Master Information</h3>
        {build_horizontal_table(master_row, master_cols_1)}
        {build_horizontal_table(master_row, master_cols_2)}
        <h3>2. Visit Summary</h3>{df_to_html_table(summary_df)}
        <h3>3. Last Visit Comment</h3>
        <div class="comment">{safe_text(last_comment)}</div>
        <h3>4. VisitLog Details</h3>{df_to_html_table(visit_df)}
    </body></html>
    """
    return html.encode("utf-8")

def create_site_card_html(
    selected_site, master_row_for_report,
    master_cols_1, master_cols_2,
    total_visit_records, total_floor_visits,
    submitted_reports, pending_reports, technical_na, total_towers,
    last_visit_date, last_visit_by, last_visit_comment
):
    html = f"""
<!DOCTYPE html><html>
<head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@700;800;900&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ margin: 0; padding: 0; font-family: 'JetBrains Mono', monospace; background: transparent; }}

.card {{
  background: #0C1020;
  color: #CBD5E1;
  border: 1px solid #1C2B45;
  border-radius: 8px;
  padding: 22px 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  width: 100%;
}}
.card-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #1C2B45;
  padding-bottom: 14px;
  margin-bottom: 18px;
}}
.card-title {{
  font-family: 'Outfit', sans-serif;
  font-size: 26px;
  font-weight: 900;
  color: #F1F5F9;
  letter-spacing: -0.02em;
  margin-bottom: 4px;
}}
.card-sub {{
  font-size: 11px;
  color: #475569;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}}
.badge {{
  background: #F59E0B;
  color: #000;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}}
.section-title {{
  font-size: 10px;
  font-weight: 700;
  color: #F59E0B;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-top: 18px;
  margin-bottom: 8px;
  padding-left: 8px;
  border-left: 3px solid #F59E0B;
}}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 12px; }}
th {{
  background: #172135;
  color: #64748B;
  border: 1px solid #1C2B45;
  padding: 7px 10px;
  text-align: left;
  font-size: 10px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  white-space: nowrap;
}}
td {{
  border: 1px solid #1C2B45;
  padding: 7px 10px;
  color: #CBD5E1;
  vertical-align: top;
}}
.kpi-strip {{
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  margin: 10px 0 14px 0;
}}
.kpi-box {{
  background: #111828;
  border: 1px solid #1C2B45;
  border-top: 2px solid #F59E0B;
  border-radius: 4px;
  padding: 10px 12px;
}}
.kpi-label {{
  font-size: 9px;
  color: #475569;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 5px;
}}
.kpi-value {{
  font-size: 22px;
  font-weight: 700;
  color: #F1F5F9;
  letter-spacing: -0.02em;
}}
.last-comment-box {{
  background: rgba(245,158,11,0.07);
  border: 1px solid rgba(245,158,11,0.25);
  color: #FCD34D;
  padding: 12px 14px;
  border-radius: 4px;
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
}}
.last-comment-box strong {{ color: #F59E0B; }}
@media (max-width: 900px) {{ .kpi-strip {{ grid-template-columns: repeat(3, 1fr); }} }}
@media (max-width: 600px) {{ .kpi-strip {{ grid-template-columns: repeat(2, 1fr); }} .card-header {{ flex-direction: column; gap: 10px; }} }}
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <div>
      <div class="card-title">{safe_text(selected_site)}</div>
      <div class="card-sub">Site Visit Report · Live Google Sheet Data</div>
    </div>
    <div class="badge">HULIOT REPORT</div>
  </div>

  <div class="section-title">Site Master Information</div>
  {build_horizontal_table(master_row_for_report, master_cols_1)}
  {build_horizontal_table(master_row_for_report, master_cols_2)}

  <div class="section-title">Visit Summary</div>
  <div class="kpi-strip">
    <div class="kpi-box"><div class="kpi-label">Visit Records</div><div class="kpi-value">{total_visit_records}</div></div>
    <div class="kpi-box"><div class="kpi-label">Floor Visits</div><div class="kpi-value">{total_floor_visits}</div></div>
    <div class="kpi-box"><div class="kpi-label">Submitted</div><div class="kpi-value">{submitted_reports}</div></div>
    <div class="kpi-box"><div class="kpi-label">Pending</div><div class="kpi-value">{pending_reports}</div></div>
    <div class="kpi-box"><div class="kpi-label">Tech NA</div><div class="kpi-value">{technical_na}</div></div>
    <div class="kpi-box"><div class="kpi-label">Towers</div><div class="kpi-value">{total_towers}</div></div>
  </div>

  <div class="section-title">Last Visit Comment</div>
  <div class="last-comment-box">
    <strong>Date:</strong> {safe_text(last_visit_date)} &nbsp;·&nbsp; <strong>By:</strong> {safe_text(last_visit_by)}<br><br>
    <strong>Comment:</strong> {safe_text(last_visit_comment)}
  </div>
</div>
</body></html>
"""
    return html

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Could not open Google Sheet. Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    worksheets       = spreadsheet.worksheets()
    visit_dataframes = []
    master_df        = pd.DataFrame()

    for ws in worksheets:
        title    = ws.title.lower()
        raw_data = ws.get_all_values()
        if not raw_data or len(raw_data) < 2:
            continue
        headers = make_unique_headers(raw_data[0])
        df      = pd.DataFrame(raw_data[1:], columns=headers)
        df      = clean_df(df)

        if "master" in title:
            master_df = df
            master_df["Source Sheet"] = ws.title
            continue
        if any(skip in title for skip in ["setting","config","associate"]):
            continue
        if not df.empty and ("Site Name" in df.columns or "Visit ID" in df.columns):
            df["Source Sheet"] = ws.title
            visit_dataframes.append(df)

    visits_df = pd.concat(visit_dataframes, ignore_index=True) if visit_dataframes else pd.DataFrame()
    visits_df = clean_df(visits_df)
    master_df = clean_df(master_df)
    return visits_df, master_df

if "data_loaded" not in st.session_state:
    visits_df, master_df = load_data()
    st.session_state["visits_df"] = visits_df
    st.session_state["master_df"] = master_df
    st.session_state["data_loaded"] = True

visits_df = st.session_state["visits_df"]
master_df = st.session_state["master_df"]

if st.sidebar.button("↺ Refresh Data"):
    st.cache_data.clear()
    visits_df, master_df = load_data()
    st.session_state["visits_df"] = visits_df
    st.session_state["master_df"] = master_df
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PREPARE VISIT DATA
# ─────────────────────────────────────────────────────────────────────────────
if not visits_df.empty:
    visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)

    date_col_global = safe_col(visits_df, ["Date of Visit","Visit Date","Date"])
    if date_col_global:
        visits_df["Date Parsed"] = pd.to_datetime(visits_df[date_col_global], errors="coerce")
        visits_df["Month"]       = visits_df["Date Parsed"].dt.strftime("%b %Y").fillna("Unknown")
    else:
        visits_df["Date Parsed"] = pd.NaT
        visits_df["Month"]       = "Unknown"

    floors_col_global = safe_col(visits_df, ["FloorsVisited","Floors Visited","Floor Visited","Floor"])
    if floors_col_global:
        visits_df["Num_Floors"] = visits_df[floors_col_global].apply(parse_floor)
    else:
        visits_df["Num_Floors"] = 0

    if "Is Report Visit?" in visits_df.columns:
        visits_df["Clean_Report_Mark"] = visits_df["Is Report Visit?"].astype(str).str.strip().str.upper()
    else:
        visits_df["Clean_Report_Mark"] = ""

# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:1.4rem;">
  <div class="page-eyebrow">HULIOT FIELD SYSTEMS</div>
  <h1 style="margin:0 0 0.2rem 0;">Site Visit Analytics</h1>
  <p style="margin:0;">Live data synchronised directly from Google Sheets</p>
</div>
""", unsafe_allow_html=True)

tab_visits, tab_master, tab_exec, tab_site_card = st.tabs([
    "Visit Analytics",
    "Master Projects",
    "Executive Dashboard",
    "Site Report Card"
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — VISIT ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
with tab_visits:
    if visits_df.empty:
        st.warning("No Visit Log data found.")
    else:
        st.markdown("<div class='section-label'>DATA FILTERS</div>", unsafe_allow_html=True)
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

        assoc_col = safe_col(visits_df, ["Associate ID","Associate","Technical Person"])
        site_col  = find_visit_site_col(visits_df)

        with col4:
            associates = ["All"] + clean_options(visits_df[assoc_col]) if assoc_col else ["All"]
            f_assoc = st.selectbox("Associate", associates, key="t1_assoc")
        with col5:
            sites = ["All"] + clean_options(visits_df[site_col]) if site_col else ["All"]
            f_site = st.selectbox("Site Name", sites, key="t1_site")

        filtered_v = visits_df.copy()
        if f_source != "All": filtered_v = filtered_v[filtered_v["Source Sheet"].astype(str) == f_source]
        if f_month  != "All": filtered_v = filtered_v[filtered_v["Month"].astype(str) == f_month]
        if f_status != "All": filtered_v = filtered_v[filtered_v["Status"].astype(str) == f_status]
        if assoc_col and f_assoc != "All": filtered_v = filtered_v[filtered_v[assoc_col].astype(str) == f_assoc]
        if site_col  and f_site  != "All": filtered_v = filtered_v[filtered_v[site_col].astype(str) == f_site]

        total_visits_floors   = int(filtered_v["Num_Floors"].sum())
        pending_count         = len(filtered_v[filtered_v["Status"] == "Pending"])
        submitted_count       = len(filtered_v[filtered_v["Status"] == "Submitted"])
        tech_na_floors        = int(filtered_v[filtered_v["Status"] == "Technical (NA)"]["Num_Floors"].sum())
        submitted_floors_sum  = int(filtered_v[filtered_v["Clean_Report_Mark"].isin(["YES","Y","TRUE"])]["Num_Floors"].sum())

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Total Visits",     total_visits_floors)
        kpi2.metric("Pending Reports",  pending_count)
        kpi3.metric("Technical (NA)",   tech_na_floors)
        kpi4.metric("Submitted",        submitted_count)
        kpi5.metric("Submitted Floors", submitted_floors_sum)

        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("##### Visits Per Month")
            month_counts = filtered_v["Month"].value_counts().reset_index()
            month_counts.columns = ["Month","Visits"]
            fig1 = px.bar(month_counts, x="Month", y="Visits", color_discrete_sequence=[CHART_COLORS[0]])
            st.plotly_chart(style_chart(fig1), use_container_width=True, key="chart_t1_month")

        with chart_col2:
            st.markdown("##### Top Sites / Zones")
            if site_col:
                site_counts = filtered_v[site_col].value_counts().nlargest(6).reset_index()
                site_counts.columns = ["Site Name","Visits"]
                fig2 = px.pie(site_counts, names="Site Name", values="Visits", hole=0.42,
                              color_discrete_sequence=CHART_COLORS)
                st.plotly_chart(style_chart(fig2), use_container_width=True, key="chart_t1_pie")

        st.markdown("<div class='section-label'>VISIT RECORDS</div>", unsafe_allow_html=True)

        display_cols = []
        for c in ["Source Sheet","Visit ID",site_col,"Tower Name","FloorsVisited","Floors Visited",
                  assoc_col,"Date of Visit","Status","Report Submitted Date","Comment"]:
            if c and c in filtered_v.columns and c not in display_cols:
                display_cols.append(c)

        st.dataframe(filtered_v[display_cols].astype(str), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — MASTER PROJECTS
# ═════════════════════════════════════════════════════════════════════════════
with tab_master:
    if master_df.empty:
        st.warning("No Master Project data found.")
    else:
        col_state = safe_col(master_df, ["STATE","State"])
        col_dist  = safe_col(master_df, ["DISTRICT / CITY","DISTRICT","District"])
        col_stat  = safe_col(master_df, ["STATUS OF PROJECT","Status","STATUS"])
        col_tech  = safe_col(master_df, ["Technical Person","TECHNICAL PERSON NAME","TECHNICAL PERSON"])
        col_sale  = safe_col(master_df, ["Sells Person","SALES PERSON NAME","SALES PERSON","Sales Person"])
        col_distr = safe_col(master_df, ["Distributer","DISTRIBUTOR NANE","DISTRIBUTOR","Distributor"])
        col_ong   = safe_col(master_df, ["VISIT ONGOING","Visit Ongoing"])

        st.markdown("<div class='section-label'>MASTER FILTERS</div>", unsafe_allow_html=True)
        m_c1, m_c2, m_c3, m_c4, m_c5, m_c6 = st.columns(6)
        filtered_m = master_df.copy()

        if col_state:
            f_state = m_c1.selectbox("State",    ["All"] + clean_options(filtered_m[col_state]), key="t2_state")
            if f_state != "All": filtered_m = filtered_m[filtered_m[col_state].astype(str) == f_state]
        if col_dist:
            f_dist  = m_c2.selectbox("District", ["All"] + clean_options(filtered_m[col_dist]),  key="t2_dist")
            if f_dist  != "All": filtered_m = filtered_m[filtered_m[col_dist].astype(str) == f_dist]
        if col_stat:
            f_stat  = m_c3.selectbox("Status",   ["All"] + clean_options(filtered_m[col_stat]),  key="t2_stat")
            if f_stat  != "All": filtered_m = filtered_m[filtered_m[col_stat].astype(str) == f_stat]
        if col_tech:
            f_tech  = m_c4.selectbox("Tech",     ["All"] + clean_options(filtered_m[col_tech]),  key="t2_tech")
            if f_tech  != "All": filtered_m = filtered_m[filtered_m[col_tech].astype(str) == f_tech]
        if col_sale:
            f_sale  = m_c5.selectbox("Sales",    ["All"] + clean_options(filtered_m[col_sale]),  key="t2_sale")
            if f_sale  != "All": filtered_m = filtered_m[filtered_m[col_sale].astype(str) == f_sale]
        if col_distr:
            f_distr = m_c6.selectbox("Distrib",  ["All"] + clean_options(filtered_m[col_distr]), key="t2_distr")
            if f_distr != "All": filtered_m = filtered_m[filtered_m[col_distr].astype(str) == f_distr]

        total_proj    = len(filtered_m)
        active_proj   = len(filtered_m[filtered_m[col_ong].astype(str).str.lower().isin(["yes","y","ongoing"])]) if col_ong else 0
        unique_states = filtered_m[col_state].nunique() if col_state else 0
        teams_set     = set()
        if col_tech: teams_set.update(filtered_m[col_tech].dropna().astype(str).tolist())
        if col_sale: teams_set.update(filtered_m[col_sale].dropna().astype(str).tolist())

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Projects",        total_proj)
        k2.metric("Active (Ongoing)",      active_proj)
        k3.metric("States Covered",        unique_states)
        k4.metric("Tech / Sales Members",  len([x for x in teams_set if x.strip() and x.lower() not in ["nan","none",""]]))

        st.markdown("---")
        m_chart1, m_chart2 = st.columns(2)

        with m_chart1:
            st.markdown("##### Projects by State")
            if col_state:
                state_c = filtered_m[col_state].value_counts().reset_index()
                state_c.columns = ["State","Count"]
                fig3 = px.bar(state_c, x="State", y="Count", color_discrete_sequence=[CHART_COLORS[1]])
                st.plotly_chart(style_chart(fig3), use_container_width=True, key="chart_t2_state")

        with m_chart2:
            st.markdown("##### Project Status")
            if col_stat:
                stat_c = filtered_m[col_stat].value_counts().reset_index()
                stat_c.columns = ["Status","Count"]
                fig4 = px.pie(stat_c, names="Status", values="Count", hole=0.42,
                              color_discrete_sequence=CHART_COLORS)
                st.plotly_chart(style_chart(fig4), use_container_width=True, key="chart_t2_pie")

        st.markdown("<div class='section-label'>MASTER PROJECTS DIRECTORY</div>", unsafe_allow_html=True)
        st.dataframe(filtered_m.astype(str), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — EXECUTIVE DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
with tab_exec:
    exec_col1, exec_col2 = st.columns([4, 1])
    with exec_col1:
        st.markdown("""
        <div style="margin-bottom:0.2rem;">
            <div class="page-eyebrow">WEST ZONE OPERATIONS</div>
            <h3 style="margin:0;">Executive Dashboard</h3>
        </div>
        <p>Multi-month associate performance tracking &amp; field analytics</p>
        """, unsafe_allow_html=True)
    with exec_col2:
        if not visits_df.empty:
            exec_months   = ["All"] + clean_options(visits_df["Month"])
            selected_month = st.selectbox("Month", exec_months, label_visibility="collapsed", key="t3_month")
        else:
            selected_month = "All"

    if visits_df.empty:
        st.warning("No Visit Log data found.")
    else:
        exec_filtered_df = visits_df.copy()
        if selected_month != "All":
            exec_filtered_df = exec_filtered_df[exec_filtered_df["Month"] == selected_month]

        assoc_col_exec = safe_col(exec_filtered_df, ["Associate ID","Associate","Technical Person"])
        site_col_exec  = find_visit_site_col(exec_filtered_df)

        if not assoc_col_exec:
            st.error("Associate ID column not found.")
        else:
            summary_rows = []
            for assoc, group in exec_filtered_df.groupby(assoc_col_exec):
                if pd.isna(assoc) or str(assoc).strip() == "":
                    continue
                floor_visit_sum   = group["Num_Floors"].sum()
                site_tower_count  = group[site_col_exec].count() if site_col_exec else len(group)
                mask_yes          = group["Clean_Report_Mark"].isin(["YES","Y","TRUE"])
                mask_no           = group["Clean_Report_Mark"].isin(["NO","N","FALSE"])
                report_yes_sum    = group[mask_yes]["Num_Floors"].sum()
                report_no_sum     = group[mask_no]["Num_Floors"].sum()
                report_pending    = len(group[group["Status"] == "Pending"])
                client_sent_floors = group[mask_yes]["Num_Floors"].sum()
                summary_rows.append({
                    "Associate ID":            assoc,
                    "Floor Visit":             int(floor_visit_sum),
                    "Site Tower visit":        int(site_tower_count),
                    "Report Mark (YES)":       int(report_yes_sum),
                    "Suggestion Visit (NO)":   int(report_no_sum),
                    "Report Pending":          report_pending,
                    "Report sent to the client": int(client_sent_floors),
                    "March Month(Pending)":    0,
                    "Report total with Pend":  int(client_sent_floors),
                })

            summary_df = pd.DataFrame(summary_rows)

            if not summary_df.empty:
                total_floors  = summary_df["Floor Visit"].sum()
                total_sites   = summary_df["Site Tower visit"].sum()
                total_sent    = summary_df["Report sent to the client"].sum()
                total_pending = summary_df["Report Pending"].sum()
            else:
                total_floors = total_sites = total_sent = total_pending = 0

            kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
            kpi_col1.metric("Total Floor Visits",   total_floors)
            kpi_col2.metric("Total Site Visits",    total_sites)
            kpi_col3.metric("Reports Sent",         total_sent)
            kpi_col4.metric("Pending Reports",      total_pending)

            st.markdown("---")
            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.markdown("##### Reports Sent to Client")
                if not summary_df.empty:
                    sorted_df1 = summary_df.sort_values("Report sent to the client", ascending=True)
                    fig_left = px.bar(
                        sorted_df1, x="Report sent to the client", y="Associate ID",
                        orientation="h", text="Report sent to the client",
                        color_discrete_sequence=[CHART_COLORS[0]]
                    )
                    fig_left.update_traces(textposition="outside",
                                          textfont=dict(family="JetBrains Mono", size=10, color="#94A3B8"))
                    st.plotly_chart(style_chart(fig_left), use_container_width=True, key="chart_t3_reports")

            with chart_col2:
                st.markdown("##### Tower vs Site Visits")
                if not summary_df.empty:
                    df_melted = summary_df.melt(
                        id_vars="Associate ID",
                        value_vars=["Floor Visit","Site Tower visit"],
                        var_name="Visit Type", value_name="Count"
                    )
                    fig_right = px.bar(
                        df_melted, x="Count", y="Associate ID",
                        color="Visit Type", barmode="group", orientation="h",
                        color_discrete_map={"Floor Visit": CHART_COLORS[0], "Site Tower visit": CHART_COLORS[1]}
                    )
                    st.plotly_chart(style_chart(fig_right), use_container_width=True, key="chart_t3_breakdown")

            st.markdown("<div class='section-label'>DETAILED PERFORMANCE BREAKDOWN</div>", unsafe_allow_html=True)

            if not summary_df.empty:
                total_row = pd.DataFrame([{
                    "Associate ID":              "TEAM TOTALS",
                    "Floor Visit":               total_floors,
                    "Site Tower visit":          total_sites,
                    "Report Mark (YES)":         summary_df["Report Mark (YES)"].sum(),
                    "Suggestion Visit (NO)":     summary_df["Suggestion Visit (NO)"].sum(),
                    "Report Pending":            total_pending,
                    "Report sent to the client": total_sent,
                    "March Month(Pending)":      0,
                    "Report total with Pend":    summary_df["Report total with Pend"].sum(),
                }])
                display_df = pd.concat([summary_df, total_row], ignore_index=True)
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                highest_coverage_str = highest_prod_str = critical_gaps_str = "None"
                if len(summary_df) > 0:
                    idx_max_site = summary_df["Site Tower visit"].idxmax()
                    highest_coverage_str = f"{summary_df.loc[idx_max_site,'Associate ID']} ({summary_df.loc[idx_max_site,'Site Tower visit']} Sites)"
                    idx_max_floor = summary_df["Floor Visit"].idxmax()
                    highest_prod_str = f"{summary_df.loc[idx_max_floor,'Associate ID']} ({summary_df.loc[idx_max_floor,'Floor Visit']} Floors)"
                    zero_sent_df = summary_df[summary_df["Report sent to the client"] == 0]
                    critical_gaps_str = (", ".join(zero_sent_df["Associate ID"].astype(str).tolist()) + " (0 Sent)") if not zero_sent_df.empty else "All Associates Active"

                h_col1, h_col2, h_col3 = st.columns(3)
                with h_col1:
                    st.markdown(f'<div class="highlight-card card-blue"><div class="card-title">🌎 Highest Coverage</div><div class="card-value">{highest_coverage_str}</div></div>', unsafe_allow_html=True)
                with h_col2:
                    st.markdown(f'<div class="highlight-card card-green"><div class="card-title">🚀 Highest Productivity</div><div class="card-value">{highest_prod_str}</div></div>', unsafe_allow_html=True)
                with h_col3:
                    st.markdown(f'<div class="highlight-card card-red"><div class="card-title">⏳ Critical Gaps</div><div class="card-value">{critical_gaps_str}</div></div>', unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — SITE REPORT CARD
# ═════════════════════════════════════════════════════════════════════════════
with tab_site_card:
    st.markdown("""
    <div class="page-eyebrow" style="margin-bottom:0.5rem;">PER-SITE DEEP DIVE</div>
    <h3 style="margin:0 0 0.4rem 0;">Site Report Card</h3>
    <p>Select one site to generate a clean report card for sharing.</p>
    """, unsafe_allow_html=True)

    if master_df.empty and visits_df.empty:
        st.warning("No MasterProject or VisitLog data found.")
    else:
        master_site_col = find_master_site_col(master_df)
        visit_site_col  = find_visit_site_col(visits_df)

        all_sites = []
        if master_site_col: all_sites += clean_options(master_df[master_site_col])
        if visit_site_col:  all_sites += clean_options(visits_df[visit_site_col])
        all_sites = sorted(list(set([x for x in all_sites if str(x).strip()])))

        if not all_sites:
            st.warning("No site names found.")
        else:
            c1, c2 = st.columns([3, 1])
            with c1:
                selected_site = st.selectbox("Select Site Name", all_sites, key="site_card_selected_site")
            with c2:
                st.write(""); st.write("")
                show_all_columns = st.checkbox("Show all columns", value=True, key="site_card_show_all")

            site_master = filter_site(master_df, master_site_col, selected_site) if master_site_col else pd.DataFrame()
            site_visits = filter_site(visits_df, visit_site_col,  selected_site) if visit_site_col  else pd.DataFrame()

            master_row = site_master.iloc[0] if not site_master.empty else pd.Series(dtype="object")

            col_project      = master_site_col
            col_state        = safe_col(master_df, ["STATE","State"])
            col_dist         = safe_col(master_df, ["DISTRICT / CITY","DISTRICT","District","CITY","City"])
            col_area         = safe_col(master_df, ["Area","AREA"])
            col_status       = safe_col(master_df, ["STATUS OF PROJECT","Status","STATUS"])
            col_visit_ongoing = safe_col(master_df, ["VISIT ONGOING","Visit Ongoing"])
            col_tech         = safe_col(master_df, ["Technical Person","TECHNICAL PERSON NAME","TECHNICAL PERSON"])
            col_sales        = safe_col(master_df, ["Sells Person","SALES PERSON NAME","SALES PERSON","Sales Person"])
            col_distributor  = safe_col(master_df, ["Distributer","DISTRIBUTOR NANE","DISTRIBUTOR","Distributor"])

            assoc_col_site   = safe_col(site_visits, ["Associate ID","Associate","Technical Person"])
            date_col_site    = safe_col(site_visits, ["Date of Visit","Visit Date","Date"])
            comment_col_site = safe_col(site_visits, ["Comment","Remarks","Observation"])
            tower_col_site   = safe_col(site_visits, ["Tower Name","Tower","Building"])
            floor_col_site   = safe_col(site_visits, ["FloorsVisited","Floors Visited","Floor Visited","Floor"])

            last_visit_date = last_visit_by = last_visit_comment = "-"

            if not site_visits.empty:
                sorted_visits = (
                    site_visits.sort_values("Date Parsed", ascending=False)
                    if "Date Parsed" in site_visits.columns
                    else (site_visits.sort_values(date_col_site, ascending=False) if date_col_site else site_visits.copy())
                )
                last_row = sorted_visits.iloc[0]
                if date_col_site:    last_visit_date    = last_row.get(date_col_site,"- ")
                if assoc_col_site:   last_visit_by      = last_row.get(assoc_col_site,"-")
                if comment_col_site: last_visit_comment = last_row.get(comment_col_site,"-")

            total_visit_records  = len(site_visits)
            total_floor_visits   = int(site_visits["Num_Floors"].sum()) if not site_visits.empty and "Num_Floors" in site_visits.columns else 0
            submitted_reports    = len(site_visits[site_visits["Status"] == "Submitted"]) if not site_visits.empty and "Status" in site_visits.columns else 0
            pending_reports      = len(site_visits[site_visits["Status"] == "Pending"])   if not site_visits.empty and "Status" in site_visits.columns else 0
            technical_na         = len(site_visits[site_visits["Status"] == "Technical (NA)"]) if not site_visits.empty and "Status" in site_visits.columns else 0
            total_towers         = site_visits[tower_col_site].nunique() if tower_col_site and not site_visits.empty else 0

            master_row_for_report = master_row.copy()
            master_row_for_report["Last Visit Date"] = last_visit_date
            master_row_for_report["Last Visit By"]   = last_visit_by

            master_cols_1 = [
                ("Project / Site Name", col_project),
                ("State",               col_state),
                ("District / City",     col_dist),
                ("Area",                col_area),
                ("Project Status",      col_status),
                ("Visit Ongoing",       col_visit_ongoing),
            ]
            master_cols_2 = [
                ("Technical Person",  col_tech),
                ("Sales Person",      col_sales),
                ("Distributor",       col_distributor),
                ("Source Sheet",      "Source Sheet"),
                ("Last Visit Date",   "Last Visit Date"),
                ("Last Visit By",     "Last Visit By"),
            ]
            summary_df = pd.DataFrame([{
                "Site Name":           selected_site,
                "Total Visit Records": total_visit_records,
                "Total Floor Visits":  total_floor_visits,
                "Submitted Reports":   submitted_reports,
                "Pending Reports":     pending_reports,
                "Technical NA":        technical_na,
                "Total Towers":        total_towers,
                "Last Visit Date":     last_visit_date,
                "Last Visit By":       last_visit_by,
            }])

            site_card_html = create_site_card_html(
                selected_site, master_row_for_report,
                master_cols_1, master_cols_2,
                total_visit_records, total_floor_visits,
                submitted_reports, pending_reports, technical_na, total_towers,
                last_visit_date, last_visit_by, last_visit_comment
            )
            components.html(site_card_html, height=620, scrolling=True)

            # ── VISIT LOG ──────────────────────────────────────────────────
            st.markdown("<div class='section-label' style='margin-top:1.2rem;'>VISITLOG DATA</div>", unsafe_allow_html=True)

            if site_visits.empty:
                st.warning("No VisitLog records found for selected site.")
            else:
                f1, f2, f3, f4 = st.columns(4)
                with f1:
                    site_months = ["All"] + clean_options(site_visits["Month"]) if "Month" in site_visits.columns else ["All"]
                    sf_month = st.selectbox("Month",     site_months, key="site_card_month")
                with f2:
                    site_statuses = ["All"] + clean_options(site_visits["Status"]) if "Status" in site_visits.columns else ["All"]
                    sf_status = st.selectbox("Status",   site_statuses, key="site_card_status")
                with f3:
                    site_associates = ["All"] + clean_options(site_visits[assoc_col_site]) if assoc_col_site else ["All"]
                    sf_assoc = st.selectbox("Associate", site_associates, key="site_card_assoc")
                with f4:
                    site_towers = ["All"] + clean_options(site_visits[tower_col_site]) if tower_col_site else ["All"]
                    sf_tower = st.selectbox("Tower",     site_towers, key="site_card_tower")

                site_visit_filtered = site_visits.copy()
                if sf_month  != "All" and "Month"  in site_visit_filtered.columns:
                    site_visit_filtered = site_visit_filtered[site_visit_filtered["Month"] == sf_month]
                if sf_status != "All" and "Status" in site_visit_filtered.columns:
                    site_visit_filtered = site_visit_filtered[site_visit_filtered["Status"] == sf_status]
                if assoc_col_site and sf_assoc != "All":
                    site_visit_filtered = site_visit_filtered[site_visit_filtered[assoc_col_site].astype(str) == sf_assoc]
                if tower_col_site and sf_tower != "All":
                    site_visit_filtered = site_visit_filtered[site_visit_filtered[tower_col_site].astype(str) == sf_tower]

                preferred_visit_cols = []
                for c in ["Source Sheet","Visit ID",visit_site_col,tower_col_site,floor_col_site,
                          assoc_col_site,date_col_site,"Is Report Visit?","Status",
                          "Report Submitted Date",comment_col_site,"CreatedAt"]:
                    if c and c in site_visit_filtered.columns and c not in preferred_visit_cols:
                        preferred_visit_cols.append(c)

                visit_display_df = site_visit_filtered.copy() if show_all_columns else site_visit_filtered[preferred_visit_cols].copy()

                chart_1, chart_2 = st.columns(2)
                with chart_1:
                    st.markdown("##### Site Visits by Month")
                    if "Month" in site_visit_filtered.columns:
                        month_chart = site_visit_filtered["Month"].value_counts().reset_index()
                        month_chart.columns = ["Month","Visits"]
                        fig_month = px.bar(month_chart, x="Month", y="Visits", color_discrete_sequence=[CHART_COLORS[0]])
                        st.plotly_chart(style_chart(fig_month), use_container_width=True, key="site_card_month_chart")
                with chart_2:
                    st.markdown("##### Status Breakdown")
                    if "Status" in site_visit_filtered.columns:
                        status_chart = site_visit_filtered["Status"].value_counts().reset_index()
                        status_chart.columns = ["Status","Count"]
                        fig_status = px.pie(status_chart, names="Status", values="Count", hole=0.42,
                                            color_discrete_sequence=CHART_COLORS)
                        st.plotly_chart(style_chart(fig_status), use_container_width=True, key="site_card_status_chart")

                st.dataframe(visit_display_df.astype(str), use_container_width=True, hide_index=True)

                # ── MASTER PROJECT ─────────────────────────────────────────
                st.markdown("<div class='section-label' style='margin-top:1rem;'>FULL MASTER PROJECT DATA</div>", unsafe_allow_html=True)
                if site_master.empty:
                    st.warning("Selected site not found in MasterProject.")
                    master_download_df = pd.DataFrame()
                else:
                    master_download_df = site_master.copy()
                    st.dataframe(master_download_df.astype(str), use_container_width=True, hide_index=True)

                # ── DOWNLOADS ──────────────────────────────────────────────
                safe_file_name = selected_site.replace("/","_").replace("\\","_").replace(" ","_")

                excel_file = create_excel_compatible_report(
                    selected_site, master_download_df, visit_display_df, summary_df, last_visit_comment)
                html_file  = create_print_html_report(
                    selected_site, master_row_for_report, master_cols_1, master_cols_2,
                    summary_df, visit_display_df, last_visit_comment)
                csv_file   = visit_display_df.to_csv(index=False).encode("utf-8")

                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                d1, d2, d3 = st.columns(3)
                with d1:
                    st.download_button("⬇ Download Excel Report", data=excel_file,
                                       file_name=f"{safe_file_name}_Report.xls",
                                       mime="application/vnd.ms-excel", key="dl_excel")
                with d2:
                    st.download_button("⬇ Download Print Report", data=html_file,
                                       file_name=f"{safe_file_name}_PrintReport.html",
                                       mime="text/html", key="dl_html")
                with d3:
                    st.download_button("⬇ Download CSV", data=csv_file,
                                       file_name=f"{safe_file_name}_VisitLog.csv",
                                       mime="text/csv", key="dl_csv")
