import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen, MarkerCluster
from streamlit_folium import st_folium
import gspread
import requests
import json
import io
import urllib.parse
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit.components.v1 as components
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- Set Page Config ---
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

# (Keep your existing CSS style block here exactly as it was in your original file)
st.markdown("""<style>.stApp {background: #0B1220;}</style>""", unsafe_allow_html=True)

# --- Logic: Initialization ---
@st.cache_resource
def init_connection():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    return gspread.authorize(creds)

client = init_connection()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit#gid=502709304"

@st.cache_data(ttl=60)
def load_all_data():
    spreadsheet = client.open_by_url(SHEET_URL)
    master_df = pd.DataFrame(spreadsheet.worksheet("MasterProject").get_all_records())
    # Add your other sheet loading logic here
    return master_df

master_df = load_all_data()

# --- Sidebar Summary ---
with st.sidebar:
    st.title("📊 Project Overview")
    status_counts = master_df["STATUS OF PROJECT"].value_counts()
    for status, count in status_counts.items():
        st.metric(label=status, value=count)
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# --- Main App Tabs ---
tab_map, tab_visits, tab_master = st.tabs(["🗺️ Site Map", "📊 Visit Analytics", "📈 Master Projects"])

with tab_map:
    st.subheader("🗺️ Site Map (Google Maps View)")
    
    def get_coords(city):
        coords = {"pune": [18.5204, 73.8567], "mumbai": [19.0760, 72.8777], "nagpur": [21.1458, 79.0882]}
        return coords.get(city.lower(), [20.5937, 78.9629])

    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, 
                   tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
    Fullscreen().add_to(m)

    marker_cluster = MarkerCluster(
        options={'spiderfyOnMaxZoom': False, 'zoomToBoundsOnClick': True}
    ).add_to(m)

    for _, row in master_df.iterrows():
        city = str(row.get("DISTRICT / CITY", ""))
        lat = row.get("Latitude", None)
        lon = row.get("Longitude", None)
        coords = [lat, lon] if pd.notna(lat) else get_coords(city)
        
        status = str(row["STATUS OF PROJECT"]).lower()
        color = "blue" if "ongoing" in status else ("green" if "complete" in status else "orange")
        
        query = urllib.parse.quote(f"{row['PROJECT']}, {city}")
        url = f"https://www.google.com/maps/dir/?api=1&destination={query}"
        
        popup_html = f"<b>{row['PROJECT']}</b><br>Status: {row['STATUS OF PROJECT']}<br><a href='{url}' target='_blank'>📍 Get Directions</a>"
        
        folium.Marker(
            location=coords,
            popup=folium.Popup(popup_html, max_width=200),
            icon=folium.Icon(color=color, icon="location-arrow", prefix="fa")
        ).add_to(marker_cluster)

    st_folium(m, width=1400, height=600)

with tab_visits:
    st.write("Existing Visit Analytics logic goes here.")

with tab_master:
    st.dataframe(master_df)
