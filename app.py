import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime

# --- 1. PRO-LEVEL STYLING ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-GLOBAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .live-card { background: #080808; padding: 15px; border-left: 5px solid #00ff41; margin-bottom: 10px; border-radius: 5px; }
    .upcoming-card { background: #050505; padding: 15px; border-left: 5px solid #888; margin-bottom: 10px; border-radius: 5px; opacity: 0.8; }
    .status-live { color: #ff0000; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=60)
def get_global_data(mode="live"):
    try:
        if mode == "live":
            # Hämtar ALLA pågående matcher globalt
            url = f"{BASE_URL}/fixtures?live=all"
        else:
            # Hämtar ALLA dagens matcher (kommande)
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{BASE_URL}/fixtures?date={today}"
        
        res = requests.get(url, headers=HEADERS, timeout=15).json()
        return res.get('response', [])
    except: return []

# --- 4. DASHBOARD ---
st.title("🌍 GOALPREDICTOR GLOBAL-LIVE")

t1, t2 = st.tabs(["🔴 LIVE WORLDWIDE", "📅 UPCOMING TODAY"])

with t1:
    live_matches = get_global_data(mode="live")
    if live_matches:
        st.subheader(f"Visar {len(live_matches)} matcher igång just nu")
        for m in live_matches:
            h, a = m['teams']['home']['name'], m['teams']['away']['name']
            hg, ag = m['goals']['home'], m['goals']['away']
            elap = m['fixture']['status']['elapsed']
            st.markdown(f"""
                <div class="live-card">
                    <span class="status-live">LIVE {elap}'</span> | <b>{h} {hg} - {ag} {a}</b><br>
                    <small>{m['league']['name']} ({m['league']['country']})</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Inga matcher live just nu. Vänta på avspark eller se 'Upcoming'.")

with t2:
    upcoming_data = get_global_data(mode="upcoming")
    # Filtrera på matcher som inte startat (Status: NS)
    ns_matches = [m for m in upcoming_data if m['fixture']['status']['short'] == 'NS']
    
    if ns_matches:
        st.subheader(f"Schemalagda matcher idag ({len(ns_matches)} st)")
        for m in ns_matches:
            h, a = m['teams']['home']['name'], m['teams']['away']['name']
            start = datetime.fromisoformat(m['fixture']['date']).strftime('%H:%M')
            st.markdown(f"""
                <div class="upcoming-card">
                    <span style="color: #00ff41;">{start}</span> | <b>{h} vs {a}</b><br>
                    <small>{m['league']['name']} ({m['league']['country']})</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Inga fler schemalagda matcher idag.")

# --- SIDEBAR TOOLS ---
st.sidebar.button("Rensa Cache & Uppdatera", on_click=st.cache_data.clear)
st.sidebar.markdown("""
**Håll koll på kvällens höjdpunkter (20:45):**
- **Ukraina vs Sverige** (VM-kval Play-off)
- **Italien vs Nordirland**
- **Polen vs Albanien**
""")
