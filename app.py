import streamlit as st
import pyrebase
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from html import escape
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. FIREBASE CONFIG ---
config = {
    "apiKey": st.secrets["firebase"]["apiKey"],
    "authDomain": st.secrets["firebase"]["authDomain"],
    "projectId": st.secrets["firebase"]["projectId"],
    "storageBucket": st.secrets["firebase"]["storageBucket"],
    "messagingSenderId": st.secrets["firebase"]["messagingSenderId"],
    "appId": st.secrets["firebase"]["appId"],
    "databaseURL": st.secrets["firebase"]["databaseURL"]
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- 2. THE DASHBOARD FUNCTION ---
def run_dashboard():
    # --- YOUR ORIGINAL DASHBOARD CODE STARTS HERE ---
    # (The page config must be set inside this function)
    st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")
    
    st.markdown("""
    <style>
        div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 1.5rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .highlight-card { padding: 20px; border-radius: 12px; text-align: left; font-family: sans-serif; font-weight: bold; margin-top: 10px; }
        .card-blue  { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
        .card-green { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
        .card-red   { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
        .card-title { font-size: 0.9rem; margin-bottom: 5px; opacity: 0.8; }
        .card-value { font-size: 1.2rem; }
    </style>
    """, unsafe_allow_html=True)

    @st.cache_resource
    def init_connection():
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        return gspread.authorize(creds)

    client = init_connection()
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"
    
    # ... (Insert ALL your helper functions: safe_text, make_unique_headers, clean_df, etc. HERE) ...
    
    # ... (Insert ALL your Data Loading and UI/Tabs logic HERE) ...
    
    st.title("📊 Site Visit Deep Analytics")
    st.write("Your dashboard is now secured and live!")

# --- 3. LOGIN LOGIC ---
if not st.session_state.user:
    st.title("🔐 Login to Site Visit Analytics")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.user = user['localId']
            st.rerun()
        except:
            st.error("Invalid email or password")
else:
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    run_dashboard()
