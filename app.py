import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from html import escape
from datetime import datetime
import streamlit.components.v1 as components
import pyrebase

# --- 0. Firebase Setup ---
config = {
    "apiKey": st.secrets["firebase"]["apiKey"],
    "authDomain": st.secrets["firebase"]["authDomain"],
    "projectId": st.secrets["firebase"]["projectId"],
    "storageBucket": st.secrets["firebase"]["storageBucket"],
    "messagingSenderId": st.secrets["firebase"]["messagingSenderId"],
    "appId": st.secrets["firebase"]["appId"]
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()

# Session State for User
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 1. Dashboard Logic Function ---
def run_dashboard():
    # --- Page Config ---
    st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

    # [CSS BLOCK - Paste your original CSS style block here]
    st.markdown("""
    <style>
        div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 1.5rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }
        .highlight-card { padding: 20px; border-radius: 12px; text-align: left; font-family: sans-serif; font-weight: bold; margin-top: 10px; }
        .card-blue  { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
        .card-green { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
        .card-red   { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
        .card-title { font-size: 0.9rem; margin-bottom: 5px; opacity: 0.8; }
        .card-value { font-size: 1.2rem; }
    </style>
    """, unsafe_allow_html=True)

    # --- Paste your original functions (init_connection, load_data, helper functions, etc.) below ---
    # [PASTE EVERYTHING FROM YOUR ORIGINAL #2 GOOGLE SHEETS CONNECTION TO THE END]
    # Note: Remove the original st.set_page_config from the pasted code
    
    # Ensure you are using the logic inside this function block!

# --- 2. Auth Flow ---
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
    # Sidebar logout
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
        
    # Render full dashboard
    run_dashboard()
