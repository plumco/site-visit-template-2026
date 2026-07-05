import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import gspread
import requests
import json
import io
from google.oauth2.service_account import Credentials
from html import escape
from datetime import datetime
import streamlit.components.v1 as components
import hashlib

# ====================== CONFIG ======================
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');
h1,h2,h3{font-family:'Sora',sans-serif;color:#F1F5F9;}
</style>""", unsafe_allow_html=True)

# ====================== AUTH ======================
FIREBASE_API_KEY = "AIzaSyDuf1MozrcpQmlnbJXa-bm5C2htxRzeZOA"

def firebase_sign_in(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    try:
        r = requests.post(url, json={"email":email,"password":password,"returnSecureToken":True}, timeout=10)
        d = r.json()
        if r.status_code == 200:
            return True, d.get("email", email), None
        return False, None, d.get("error",{}).get("message","Authentication failed")
    except:
        return False, None, "Connection error"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 style="text-align:center">🔐 Site Visit Analytics</h1>', unsafe_allow_html=True)
    _, col, _ = st.columns([1,1.5,1])
    with col:
        with st.form("login"):
            em = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                ok, ue, err = firebase_sign_in(em, pw)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = ue
                    st.rerun()
                else:
                    st.error("Invalid login")
    st.stop()

# ====================== GOOGLE SHEET ======================
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

client = init_connection()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"

# ====================== HELPERS ======================
def safe_text(v):
    v = str(v).strip()
    return "-" if v.lower() in ["nan","none","null","nat",""] else escape(v)

def make_unique_headers(raw):
    seen = {}; out = []
    for h in raw:
        h = str(h).strip() or "Blank"
        out.append(f"{h}_{seen[h]}" if h in seen else h)
        seen[h] = seen.get(h, 0) + 1
    return out

def clean_df(df):
    if df.empty: return df
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).replace({"nan":"","None":"","NaT":"","NaN":"","null":"","Null":""}).str.strip()
    return df

def safe_col(df, opts):
    for o in opts:
        if o in df.columns: return o
    return None

def clean_options(s):
    return sorted(s.astype(str).str.strip().replace(["nan","None","NaT","","null","Null"], pd.NA).dropna().unique().tolist())

def get_visit_status(row):
    ir = str(row.get("Is Report Visit?","")).strip().lower()
    sd = str(row.get("Report Submitted Date","")).strip()
    if ir in ["no","n","false","n/a","na"]: return "Technical (NA)"
    if sd and sd.lower() not in ["nan","none","","nat"]: return "Submitted"
    return "Pending"

def parse_floor(val):
    v = str(val).strip()
    if not v or v.lower() in ["nan","none","null","n/a","na","-"]: return 0
    try: return int(float(v))
    except: return 1

def find_master_site_col(df):
    return safe_col(df, ["PROJECT","Project","PROJECT NAME","Project Name","Site Name","SITE NAME","Site"])

def find_visit_site_col(df):
    return safe_col(df, ["Site Name","SITE NAME","PROJECT","Project","PROJECT NAME","Project Name"])

# ====================== GEOCODING DICTIONARIES ======================
CITY_COORDS = {
    "mumbai":(19.0760,72.8777),"pune":(18.5204,73.8567),"nagpur":(21.1458,79.0882),
    "nashik":(19.9975,73.7898),"thane":(19.2183,72.9781),"aurangabad":(19.8762,75.3433),
    "ahmedabad":(23.0225,72.5714),"surat":(21.1702,72.8311),"indore":(22.7196,75.8577),
    # Add more as needed
}

AREA_COORDS = {
    "baner":(18.5590,73.7868),"wakad":(18.5994,73.7614),"hadapsar":(18.5018,73.9395),
    "andheri":(19.1136,72.8697),"bandra":(19.0596,72.8295),"borivali":(19.2307,72.8567),
    # Add more as needed
}

STATE_COORDS = {
    "maharashtra":(19.7515,75.7139),"gujarat":(22.2587,71.1924),
    "madhya pradesh":(22.9734,78.6569),
}

def improved_geocode(proj_name, city, state):
    pn = str(proj_name).lower().strip()
    c = str(city).lower().strip()
    s = str(state).lower().strip()
    combined = f"{pn} {c} {s}"
    
    for key, (lat, lon) in AREA_COORDS.items():
        if key in combined:
            return lat, lon, "area"
    for key, (lat, lon) in CITY_COORDS.items():
        if key in combined or key in c:
            return lat, lon, "city"
    for key, (lat, lon) in STATE_COORDS.items():
        if key in s:
            return lat, lon, "state"
    return None, None, None

# ====================== LOAD DATA ======================
@st.cache_data(ttl=120)
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Sheet error: {e}")
        return pd.DataFrame(), pd.DataFrame()

    visit_dfs = []
    master_df = pd.DataFrame()
    for ws in spreadsheet.worksheets():
        title = ws.title.lower()
        raw = ws.get_all_values()
        if len(raw) < 2: continue
        df = clean_df(pd.DataFrame(raw[1:], columns=make_unique_headers(raw[0])))
        if "master" in title:
            master_df = df
            master_df["Source Sheet"] = ws.title
            continue
        if any(x in title for x in ["setting","config","associate","issue"]): continue
        if not df.empty:
            visit_dfs.append(df)

    visits_df = clean_df(pd.concat(visit_dfs, ignore_index=True)) if visit_dfs else pd.DataFrame()
    return visits_df, master_df

visits_df, master_df = load_data()

with st.sidebar:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ====================== DATA PROCESSING ======================
if not visits_df.empty:
    visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)
    dc = safe_col(visits_df, ["Date of Visit","Visit Date","Date"])
    if dc:
        visits_df["Date Parsed"] = pd.to_datetime(visits_df[dc], errors="coerce")
        visits_df["Month"] = visits_df["Date Parsed"].dt.strftime("%b %Y").fillna("Unknown")
    fc = safe_col(visits_df, ["FloorsVisited","Floors Visited","Floor"])
    if fc:
        visits_df["Num_Floors"] = visits_df[fc].apply(parse_floor)

# ====================== UI ======================
st.title("📊 Site Visit Deep Analytics")

tab_visits, tab_master, tab_exec, tab_site_card, tab_issues, tab_map = st.tabs([
    "📊 Visit Analytics","📈 Master Projects","👔 Executive Dashboard",
    "🏢 Site Report Card","🚨 Site Issues","🗺️ Site Map"
])

# ====================== MAP TAB ======================
with tab_map:
    st.markdown("### 🗺️ West Zone Project Map (Fixed)")
    st.caption("Improved location detection + navigation")

    if master_df.empty:
        st.warning("No Master data found")
    else:
        mc_s = find_master_site_col(master_df)
        mc_st = safe_col(master_df, ["STATE","State"])
        mc_di = safe_col(master_df, ["DISTRICT / CITY","DISTRICT","District","CITY","City"])
        mc_te = safe_col(master_df, ["Technical Person","TECHNICAL PERSON"])

        c1,c2,c3,c4 = st.columns(4)
        f_mst = c1.selectbox("State", ["All"] + clean_options(master_df[mc_st]) if mc_st else ["All"], key="mst")
        f_mci = c2.selectbox("City", ["All"] + clean_options(master_df[mc_di]) if mc_di else ["All"], key="mci")
        f_mte = c4.selectbox("Tech Person", ["All"] + clean_options(master_df[mc_te]) if mc_te else ["All"], key="mte")

        fmap = master_df.copy()
        if f_mst != "All" and mc_st: fmap = fmap[fmap[mc_st].astype(str) == f_mst]
        if f_mci != "All" and mc_di: fmap = fmap[fmap[mc_di].astype(str) == f_mci]
        if f_mte != "All" and mc_te: fmap = fmap[fmap[mc_te].astype(str) == f_mte]

        sites_json = []
        for _, row in fmap.iterrows():
            proj = str(row.get(mc_s, "")).strip()
            if not proj: continue
            city = str(row.get(mc_di, ""))
            state = str(row.get(mc_st, ""))
            tech = str(row.get(mc_te, "-"))

            lat, lon, level = improved_geocode(proj, city, state)
            if lat is None: continue

            h = int(hashlib.md5(proj.encode()).hexdigest(), 16)
            lat += ((h % 12) - 6) * 0.005
            lon += ((h % 10) - 5) * 0.005

            sites_json.append({
                "name": proj,
                "city": city or "-",
                "tech": tech,
                "lat": round(lat,6),
                "lon": round(lon,6)
            })

        if sites_json:
            center_lat = sum(s["lat"] for s in sites_json) / len(sites_json)
            center_lon = sum(s["lon"] for s in sites_json) / len(sites_json)

            sites_js = json.dumps(sites_json)

            html_map = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <style>#map {{height: 680px; width: 100%;}}</style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], 7);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png').addTo(map);
        var cluster = L.markerClusterGroup();
        var sites = {sites_js};
        sites.forEach(s => {{
            var marker = L.marker([s.lat, s.lon]);
            marker.bindPopup("<b>" + s.name + "</b><br>City: " + s.city);
            cluster.addLayer(marker);
        }});
        map.addLayer(cluster);
    </script>
</body>
</html>
"""
            components.html(html_map, height=700)
            st.success(f"✅ {len(sites_json)} sites plotted!")
        else:
            st.warning("No sites could be located. Try adding more coordinates to dictionaries.")

st.caption("Map fixed with proper geocoding")
