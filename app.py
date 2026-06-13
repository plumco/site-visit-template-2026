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

# --- 2. AUTHENTICATION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 3. DASHBOARD FUNCTION ---
def run_dashboard():
    # ---------------------------------------------------------
    # PASTE YOUR ORIGINAL DASHBOARD CODE HERE (Indented)
    # ---------------------------------------------------------
    # Ensure st.set_page_config(...) is the first line here
    # Ensure all your Google Sheets/Plotly/Data logic is here
    st.write("DASHBOARD CODE IS RUNNING")
    # ---------------------------------------------------------

# --- 4. LOGIN GATEKEEPER ---
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
    # --- IF LOGGED IN, SHOW LOGOUT AND DASHBOARD ---
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    
    # This calls your dashboard logic
    run_dashboard()
