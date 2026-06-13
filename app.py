import streamlit as st
import pyrebase
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from html import escape
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. FIREBASE SETUP ---
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

# --- 3. YOUR DASHBOARD LOGIC ---
def run_dashboard():
    # --- PASTE YOUR DASHBOARD CODE HERE ---
    # NOTE: You MUST include your st.set_page_config() and all your original functions
    # (init_connection, load_data, helper functions, and all tab logic) inside this function.
    st.write("DASHBOARD LOADED SUCCESSFULLY")

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
    # --- RUN DASHBOARD IF AUTHENTICATED ---
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    
    run_dashboard()
