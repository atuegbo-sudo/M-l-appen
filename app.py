import streamlit as st
import requests
import numpy as np
from datetime import datetime

# --- 1. UI SETUP ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-GLOBAL", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .live-card { 
        background: #080808; 
        padding: 20px; 
        border-left: 5px solid #00ff41; 
        margin-bottom: 12px; 
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,255,65,0.1);
    }
    .status-live { color: #ff0000; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    .neural-text { color: #00ff41; font-size: 0.85em; }
    </style>
    """, unsafe_allow_html=True)

# API CONFIG
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}

# --- 2. GLOBAL LIVE ENGINE ---

@st.cache_data(ttl=30) # Uppdateras var 30:e sekund för maximal live-känsla
def get_all_live_now():
    """Hämtar ALLA matcher som pågår i hela världen just nu"""
    try:
        # Ingen filtrering på liga = vi får rubbet (U21, Träningsmatcher, Kval, etc.)
        url = "https://v3.football.api-sports.io"
        res = requests.get(url, headers=HEADERS, timeout=15).json()
        return res.get('response', [])
    except:
        return []

def calculate_neural_live(hg, ag, elapsed):
    """Snabb-analys av målchans baserat på tid kvar"""
    rem_time = 90 - elapsed
    if rem_time <= 0: return 0
    # xG-baserad projektion för resten av matchen
    current_total = hg + ag
    if current_total >= 3: return 100
    
    # Neural projektion (förenklad för live-listan)
    projected = current_total + (1.2 * (rem_time/90))
    prob = min(99.9, round((projected / 2.5) * 65, 1))
    return prob

# --- 3. DASHBOARD ---
st.title("🌍 OMNI-GLOBAL LIVE TRACKER")
st.write(f"Söker av världsmarknaden... {datetime.now().strftime('%H:%M:%S')}")

live_matches = get_all_live_now()

if live_matches:
    st.subheader(f"🔴 {len(live_matches)} MATCHER IGÅNG JUST NU")
    
    # Skapa kolumner för att visa fler matcher samtidigt
    col1, col2 = st.columns(2)
    
    for i, m in enumerate(live_matches):
        h, a = m['teams']['home']['name'], m['teams']['away']['name']
        hg, ag = m['goals']['home'], m['goals']['away']
        elapsed = m['fixture']['status']['elapsed']
        league = m['league']['name']
        country = m['league']['country']
        
        # Neural analys för varje live-match
        prob = calculate_neural_live(hg, ag, elapsed)
        
        # Fördela i kolumnerna
        target_col = col1 if i % 2 == 0 else col2
        
        with target_col:
            st.markdown(f"""
                <div class="live-card">
                    <div style="display: flex; justify-content: space-between;">
                        <span class="status-live">LIVE {elapsed}'</span>
                        <span style="color: #888; font-size: 0.8em;">{league} ({country})</span>
                    </div>
                    <div style="font-size: 1.4em; margin: 10px 0;">
                        <b>{h} {hg} - {ag} {a}</b>
                    </div>
                    <div class="neural-text">
                        🧠 Neural sannolikhet Över 2.5: <b>{prob}%</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.warning("Just nu hittades inga live-matcher i API:et. Det kan bero på att matcher pausats eller att din API-kvot är nådd.")
    if st.button("Försök igen (Force Refresh)"):
        st.cache_data.clear()
        st.rerun()

# --- 4. UPCOMING SHORTLIST (Sverige-fokus) ---
st.sidebar.header("🏆 IKVÄLL: VM-KVAL PLAY-OFF")
st.sidebar.markdown("""
- **20:45** | Ukraina vs Sverige
- **20:45** | Italien vs Nordirland
- **20:45** | Polen vs Albanien
- **20:45** | Wales vs Bosnien
""")

if st.sidebar.button("Rensa Cache & Uppdatera"):
    st.cache_data.clear()
    st.rerun()
