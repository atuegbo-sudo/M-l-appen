import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 1. DESIGN & STYLING ---
st.set_page_config(page_title="GLOBAL LIVE SCANNER v150", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .live-card { 
        background: #080808; 
        padding: 15px; 
        border: 1px solid #00ff41; 
        border-radius: 10px; 
        margin-bottom: 10px;
        transition: 0.3s;
    }
    .live-card:hover { border-color: #ffffff; box-shadow: 0 0 15px #00ff41; }
    .status-blink { color: #ff0000; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    .score-box { font-size: 1.8em; font-weight: 900; letter-spacing: 5px; color: #fff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG (TheSportsDB Key: 3) ---
BASE_URL = "https://www.thesportsdb.com"

@st.cache_data(ttl=30)
def get_all_livescores():
    """Hämtar alla live-matcher för fotboll globalt"""
    # Vi använder livescore-endpointen för Soccer
    url = f"{BASE_URL}/latestsoccer.php"
    try:
        res = requests.get(url, timeout=10).json()
        return res.get('teams', []) # Vissa endpoints returnerar 'teams' för live
    except:
        # Fallback till dagens matcher om livescore-endpointen är nere
        try:
            url_today = f"{BASE_URL}/eventsday.php?d={datetime.now().strftime('%Y-%m-%d')}&s=Soccer"
            res_today = requests.get(url_today).json()
            return res_today.get('events', [])
        except: return []

# --- 3. DASHBOARD INTERFACE ---
st.title("🔴 OMNI-GLOBAL LIVE SCANNER")
st.subheader(f"System Time: {datetime.now().strftime('%H:%M:%S')} | Global Coverage Active")

# Knapp för att tvinga uppdatering
if st.sidebar.button("FORCE REFRESH SYSTEM"):
    st.cache_data.clear()
    st.rerun()

live_data = get_all_livescores()

if not live_data:
    st.info("Söker efter matcher... Om listan är tom finns inga pågående matcher i databasen just nu.")
    st.caption("Tips: Testa 'Force Refresh' i sidomenyn.")
else:
    # Skapa kolumner för att visa matcher i ett snyggt rutnät
    col1, col2 = st.columns(2)
    
    for i, match in enumerate(live_data):
        # Hanterar olika namngivning i API-svaren
        home_team = match.get('strHomeTeam') or match.get('strEvent', '').split(' vs ')[0]
        away_team = match.get('strAwayTeam') or match.get('strEvent', '').split(' vs ')[1] if ' vs ' in str(match.get('strEvent')) else "Unknown"
        home_score = match.get('intHomeScore', '0')
        away_score = match.get('intAwayScore', '0')
        league = match.get('strLeague', 'International')
        status = match.get('strStatus', 'LIVE')
        progress = match.get('strProgress', "In Play")

        target_col = col1 if i % 2 == 0 else col2
        
        with target_col:
            st.markdown(f"""
            <div class="live-card">
                <div style="display: flex; justify-content: space-between;">
                    <span class="status-blink">● {status} ({progress})</span>
                    <span style="color: #666; font-size: 0.8em;">{league}</span>
                </div>
                <div style="text-align: center; margin: 10px 0;">
                    <div style="color: #00ff41; font-size: 1.1em;">{home_team}</div>
                    <div class="score-box">{home_score} - {away_score}</div>
                    <div style="color: #00ff41; font-size: 1.1em;">{away_team}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- 4. WORLD EXPLORER (Sökning) ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Sök i världen")
search_country = st.sidebar.text_input("Land (t.ex. Egypt, Saudi, Sweden)")

if search_country:
    st.sidebar.write(f"Söker data för {search_country}...")
    # Här kan du lägga till specifik söklogik för länder om du vill se ligor
