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

# ====================== PAGE CONFIG & STYLING ======================
st.set_page_config(layout="wide", page_title="Site Visit Deep Analytics", page_icon="📊")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:radial-gradient(circle at 12% 18%,rgba(56,189,248,0.30) 0%,transparent 40%),radial-gradient(circle at 88% 6%,rgba(129,140,248,0.26) 0%,transparent 38%),radial-gradient(circle at 50% 100%,rgba(34,211,238,0.22) 0%,transparent 45%),radial-gradient(circle at 30% 70%,rgba(99,102,241,0.16) 0%,transparent 40%),linear-gradient(180deg,#060B16 0%,#0B1220 55%,#0A1020 100%) !important;}
h1,h2,h3{font-family:'Sora',sans-serif !important;color:#F1F5F9 !important;}
</style>""", unsafe_allow_html=True)

FIREBASE_API_KEY = "AIzaSyDuf1MozrcpQmlnbJXa-bm5C2htxRzeZOA"

def firebase_sign_in(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    try:
        r = requests.post(url, json={"email":email,"password":password,"returnSecureToken":True}, timeout=10)
        d = r.json()
        if r.status_code == 200:
            return True, d.get("email", email), None
        return False, None, d.get("error",{}).get("message","Authentication failed")
    except Exception as e:
        return False, None, str(e)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None

if not st.session_state["authenticated"]:
    st.markdown('<div style="text-align:center;padding:2.5rem 0;"><h1>🔐 Site Visit Analytics</h1><p>Please sign in</p></div>', unsafe_allow_html=True)
    _, cc, _ = st.columns([1,1.5,1])
    with cc:
        with st.form("login_form"):
            em = st.text_input("📧 Email")
            pw = st.text_input("🔑 Password", type="password")
            if st.form_submit_button("🚀 Sign In", use_container_width=True):
                if em and pw:
                    ok, ue, err = firebase_sign_in(em, pw)
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"] = ue
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
    st.stop()

st.sidebar.markdown(f"👤 **{st.session_state.get('user_email','')}**")
if st.sidebar.button("🚪 Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

# ====================== CONNECTION ======================
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

client = init_connection()
SHEET_URL = "https://docs.google.com/spreadsheets/d/1J1K31wLOepJMO6DPHySUGR43GpV2sV7PqSHetO_EFjo/edit?gid=502709304#gid=502709304"

# ====================== HELPER FUNCTIONS ======================
def safe_text(v):
    v = str(v).strip()
    return "-" if v.lower() in ["nan","none","null","nat",""] else escape(v)

def make_unique_headers(raw):
    seen = {}; out = []
    for h in raw:
        h = str(h).strip() or "Blank"
        if h in seen:
            seen[h] += 1
            out.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            out.append(h)
    return out

def clean_df(df):
    if df.empty: return df
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).replace({"nan":"","None":"","NaT":"","NaN":"","null":"","Null":""}).str.strip()
    return df

def safe_col(df, opts):
    if df.empty: return None
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

# ====================== GEOCODING ======================
CITY_COORDS = { ... }  # Keep your original dictionary here
AREA_COORDS = { ... }  # Keep your original dictionary here
STATE_COORDS = { ... } # Keep your original dictionary here

def improved_geocode(proj_name, city, state):
    pn = str(proj_name).lower().strip()
    c = str(city).lower().strip()
    s = str(state).lower().strip()
    combined = f"{pn} {c} {s}"
    
    for key, (lat, lon) in AREA_COORDS.items():
        if key in combined or key.replace(" ","") in combined.replace(" ",""):
            return lat, lon, "area"
    for key, (lat, lon) in CITY_COORDS.items():
        if key in combined or key in c or c in key:
            return lat, lon, "city"
    for key, (lat, lon) in STATE_COORDS.items():
        if key in s or s in key:
            return lat, lon, "state"
    return None, None, None

# ====================== LOAD DATA ======================
@st.cache_data(ttl=120)
def load_data():
    try:
        spreadsheet = client.open_by_url(SHEET_URL)
    except Exception as e:
        st.error(f"Could not open Google Sheet: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    visit_dfs = []
    master_df = pd.DataFrame()
    for ws in spreadsheet.worksheets():
        title = ws.title.lower()
        raw = ws.get_all_values()
        if not raw or len(raw) < 2: continue
        df = clean_df(pd.DataFrame(raw[1:], columns=make_unique_headers(raw[0])))
        if "master" in title:
            master_df = df
            master_df["Source Sheet"] = ws.title
            continue
        if any(skip in title for skip in ["setting","config","associate","siteissues"]): continue
        if not df.empty and ("Site Name" in df.columns or "Visit ID" in df.columns):
            df["Source Sheet"] = ws.title
            visit_dfs.append(df)
    
    visits_df = clean_df(pd.concat(visit_dfs, ignore_index=True)) if visit_dfs else pd.DataFrame()
    return visits_df, master_df

visits_df, master_df = load_data()

with st.sidebar:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Last load: {datetime.now().strftime('%H:%M:%S')}")

if not visits_df.empty:
    visits_df["Status"] = visits_df.apply(get_visit_status, axis=1)
    dc = safe_col(visits_df, ["Date of Visit","Visit Date","Date"])
    if dc:
        visits_df["Date Parsed"] = pd.to_datetime(visits_df[dc], errors="coerce")
        visits_df["Month"] = visits_df["Date Parsed"].dt.strftime("%b %Y").fillna("Unknown")
    fc = safe_col(visits_df, ["FloorsVisited","Floors Visited","Floor Visited","Floor"])
    visits_df["Num_Floors"] = visits_df[fc].apply(parse_floor) if fc else 0

# ====================== TABS ======================
st.title("📊 Site Visit Deep Analytics")

tab_visits, tab_master, tab_exec, tab_site_card, tab_issues, tab_map = st.tabs([
    "📊 Visit Analytics", "📈 Master Projects", "👔 Executive Dashboard",
    "🏢 Site Report Card", "🚨 Site Issues", "🗺️ Site Map"
])

# ==================== TAB 6: IMPROVED MAP ====================
with tab_map:
    st.markdown("### 🗺️ West Zone Project Map")
    st.info("✅ Improved geocoding + Search + Navigation")

    if master_df.empty:
        st.warning("No MasterProject data found.")
    else:
        mc_s = find_master_site_col(master_df)
        mc_st = safe_col(master_df, ["STATE","State"])
        mc_di = safe_col(master_df, ["DISTRICT / CITY","DISTRICT","District","CITY","City"])
        mc_sp = safe_col(master_df, ["STATUS OF PROJECT","Status","STATUS"])
        mc_te = safe_col(master_df, ["Technical Person","TECHNICAL PERSON NAME","TECHNICAL PERSON"])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            f_mst = st.selectbox("State", ["All"] + (clean_options(master_df[mc_st]) if mc_st else []), key="map_state")
        with col2:
            f_mci = st.selectbox("City / District", ["All"] + (clean_options(master_df[mc_di]) if mc_di else []), key="map_city")
        with col3:
            f_msp = st.selectbox("Project Status", ["All"] + (clean_options(master_df[mc_sp]) if mc_sp else []), key="map_status")
        with col4:
            f_mte = st.selectbox("Technical Person", ["All"] + (clean_options(master_df[mc_te]) if mc_te else []), key="map_tech")

        fmap = master_df.copy()
        if mc_st and f_mst != "All": fmap = fmap[fmap[mc_st].astype(str) == f_mst]
        if mc_di and f_mci != "All": fmap = fmap[fmap[mc_di].astype(str) == f_mci]
        if mc_sp and f_msp != "All": fmap = fmap[fmap[mc_sp].astype(str) == f_msp]
        if mc_te and f_mte != "All": fmap = fmap[fmap[mc_te].astype(str) == f_mte]

        sites_json = []
        for _, row in fmap.iterrows():
            proj = str(row.get(mc_s, "")).strip()
            if not proj: continue
            state = str(row.get(mc_st, ""))
            city = str(row.get(mc_di, ""))
            status = str(row.get(mc_sp, "Unknown"))
            tech = str(row.get(mc_te, "-"))

            lat, lon, level = improved_geocode(proj, city, state)
            if lat is None: continue

            h = int(hashlib.md5(proj.encode()).hexdigest(), 16)
            if level != "area":
                lat += ((h % 15) - 7) * 0.006
                lon += ((h % 11) - 5) * 0.006

            sites_json.append({
                "name": proj,
                "state": state or "-",
                "city": city or "-",
                "status": status,
                "tech": tech,
                "level": level,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "highlight": f_mte != "All" and tech == f_mte
            })

        if sites_json:
            if f_mci != "All" and f_mci.lower() in CITY_COORDS:
                center = CITY_COORDS[f_mci.lower()]
                zoom = 12
            elif f_mst != "All" and f_mst.lower() in STATE_COORDS:
                center = STATE_COORDS[f_mst.lower()]
                zoom = 8
            else:
                center = [sum(s["lat"] for s in sites_json)/len(sites_json),
                         sum(s["lon"] for s in sites_json)/len(sites_json)]
                zoom = 7

            sites_js = json.dumps(sites_json, ensure_ascii=False)

            leaflet_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <style>
        #map {{ width:100%; height:680px; }}
        .leaflet-popup-content-wrapper {{ border-radius: 10px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var sites = {sites_js};
        var map = L.map('map', {{ center: [{center[0]}, {center[1]}], zoom: {zoom} }});
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png').addTo(map);
        
        var cluster = L.markerClusterGroup();
        sites.forEach(function(s) {{
            var color = s.status.toLowerCase().includes('complete') ? '#22c55e' : 
                       (s.status.toLowerCase().includes('ongoing') ? '#38BDF8' : '#94a3b8');
            var marker = L.marker([s.lat, s.lon], {{
                icon: L.divIcon({{
                    html: `<div style="background:${{color}}; width:16px; height:16px; border-radius:50%; border:3px solid white;"></div>`,
                    iconSize: [16,16]
                }})
            }});
            marker.bindPopup(`<b>${{s.name}}</b><br>City: ${{s.city}}<br>Status: ${{s.status}}<br>Tech: ${{s.tech}}`);
            cluster.addLayer(marker);
        }});
        map.addLayer(cluster);
    </script>
</body>
</html>
"""
            components.html(leaflet_html, height=700)

            st.success(f"✅ {len(sites_json)} sites plotted successfully!")
        else:
            st.warning("No sites could be geocoded with current filters.")

st.caption("Map improved with better location detection and navigation.")
