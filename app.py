import streamlit as st
import pyrebase
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
# ... keep your other imports ...

# --- 1. FIREBASE CONFIG ---
# (Your keys are already saved in Streamlit Cloud Secrets, so this will work)
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

# --- 2. AUTHENTICATION GATEKEEPER ---
if 'user' not in st.session_state:
    st.session_state.user = None

def run_dashboard():
    # --- PASTE ALL YOUR DASHBOARD CODE HERE ---
    # Example: 
    # st.set_page_config(layout="wide", ...) 
    # client = init_connection()
    # ... all your existing tabs, charts, and dataframe logic ...
    st.write("Welcome to the Dashboard!")

# --- 3. LOGIN LOGIC ---
if not st.session_state.user:
    st.title("🔐 Login")
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
    # --- IF LOGGED IN, RUN THE DASHBOARD ---
    run_dashboard()
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
