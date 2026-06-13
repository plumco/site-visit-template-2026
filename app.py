import streamlit as st
import pyrebase
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from html import escape
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

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

# --- 2. SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 3. LOGIN PAGE ---
def login_page():
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

# --- 4. DASHBOARD (YOUR ORIGINAL CODE) ---
def run_dashboard():
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Paste your original UI CSS here
    st.markdown("""<style>...</style>""", unsafe_allow_html=True)

    # Paste all your helper functions (init_connection, clean_df, etc.) here
    # Paste all your Data Loading and Tab logic here
    st.write("Your dashboard is loaded!")

# --- 5. MAIN GATEKEEPER ---
if st.session_state.user:
    run_dashboard()
else:
    login_page()
