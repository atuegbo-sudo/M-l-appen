import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime

# --- 1. GLOBAL SETUP & STYLE ---
st.set_page_config(page_title="GoalPredictor v150.0 GLOBAL", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .live-card { background: #080808; padding: 15px; border-left: 5px solid #00ff41; margin-bottom: 10px; border-radius: 5px; }
    .upcoming-card { background: #050505; padding: 15px; border-left: 5px solid #555; margin-bottom: 10px; border-radius: 5px; }
    .neural-box { background: #050505; padding: 20px; border: 2px solid #00ff41; text-align: center; }
    h3 { color: #00ff41 !important; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# API CONFIG
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}

# --- 2. GLOBAL DATA ENGINE ---

@st.cache_data(ttl=60)
def get_global_matches(mode="live"):
    """Hämtar matcher globalt utan ligafilter"""
    try:
        if mode == "live":
            # Hämtar ALLA pågående matcher i världen
            url = "https://v3.football.api-sports.io"
        else:
            # Hämtar ALLA dagens matcher i världen
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"https://v3.football.api-sports.io{today}"
            
        res = requests.get(url, headers=HEADERS, timeout=15).json()
        return res.get('response', [])
    except: return []

# --- 3. DASHBOARD UI ---
st.title("🌍 GOALPREDICTOR GLOBAL-SCAN")
st.caption(f"Status: Connected | Date: {datetime.now().strftime('%Y-%m-%d')}")

live_tab, upcoming_tab = st.tabs(["🔴 LIVE WORLDWIDE", "📅 UPCOMING TODAY"])

with live_tab:
    live_data = get_global_matches(mode="live")
    
    if live_data:
        st.subheader(f"Visar {len(live_data)} pågående matcher")
        for m in live_data:
            h, a = m['teams']['home']['name'], m['teams']['away']['name']
            hg, ag = m['goals']['home'], m['goals']['away']
            time = m['fixture']['status']['elapsed']
            league = m['league']['name']
            country = m['league']['country']
            
            st.markdown(f"""
                <div class="live-card">
                    <span style="color: #00ff41;">{time}'</span> | <b>{h} {hg} - {ag} {a}</b><br>
                    <small>{league} ({country})</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Inga matcher spelas live just nu. Vänta på avspark eller kolla 'Upcoming'.")

with upcoming_tab:
    upcoming_data = get_global_matches(mode="upcoming")
    
    # Filtrera på matcher som inte startat (Status: NS)
    to_be_played = [m for m in upcoming_data if m['fixture']['status']['short'] == 'NS']
    
    if to_be_played:
        st.subheader(f"Schemalagda matcher idag ({len(to_be_played)} st)")
        
        # Gruppera efter land för bättre översikt
        countries = sorted(list(set([m['league']['country'] for m in to_be_played])))
        selected_country = st.selectbox("Filtrera efter land (Valfritt)", ["ALLA LÄNDER"] + countries)
        
        for m in to_be_played:
            if selected_country != "ALLA LÄNDER" and m['league']['country'] != selected_country:
                continue
                
            h, a = m['teams']['home']['name'], m['teams']['away']['name']
            start = datetime.fromisoformat(m['fixture']['date']).strftime('%H:%M')
            
            st.markdown(f"""
                <div class="upcoming-card">
                    <span style="color: #00ff41;">{start}</span> | <b>{h} vs {a}</b><br>
                    <small>{m['league']['name']} ({m['league']['country']})</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Inga fler schemalagda matcher hittades för idag.")

# --- SIDEBAR TOOLS ---
st.sidebar.header("🛠️ Global Tools")
if st.sidebar.button("FORCE REFRESH WORLD DATA"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("""
**Dagens Toppmatcher (CET):**
- 18:00: Turkiet - Rumänien
- 20:00: Brasilien - Frankrike
- 20:45: **Ukraina - Sverige**
- 20:45: Italien - Nordirland
""")
