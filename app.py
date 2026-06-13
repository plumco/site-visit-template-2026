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
    # PASTE YOUR ENTIRE ORIGINAL DASHBOARD CODE HERE
    # ---------------------------------------------------------
    st.title("📊 Site Visit Deep Analytics")
    st.write("Your original dashboard charts and data tables go here.")
    # Ensure all your original logic (sheets, tabs, plots) is indented here.
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
    # --- LOGOUT BUTTON ---
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    
    # --- CALL YOUR DASHBOARD ---
    run_dashboard()
