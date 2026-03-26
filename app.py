import streamlit as st
import requests
import numpy as np
import pandas as pd

# --- 1. SETUP & STYLE ---
st.set_page_config(page_title="GoalPredictor OMNI", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stButton>button { 
        background: #00ff41 !important; color: black !important; 
        font-weight: 900; width: 100%; height: 5em; border: 2px solid #ffffff;
        font-size: 20px !important; text-transform: uppercase; margin-bottom: 20px;
    }
    .metric-container { background: #050505; border: 1px solid #00ff41; padding: 15px; border-radius: 10px; text-align: center; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE CONFIG ---
API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': API_KEY}

@st.cache_data(ttl=3600)
def get_data(l_id):
    url = f"https://v3.football.api-sports.io{l_id}&season=2025"
    res = requests.get(url, headers=HEADERS).json()
    return res['response'][0]['league']['standings'][0] if res.get('response') else []

def run_sim(h_xg, a_xg):
    # Simulera 1 miljon matcher
    h_s = np.random.poisson(h_xg * 1.10, 1000000)
    a_s = np.random.poisson(a_xg * 0.95, 1000000)
    t = h_s + a_s
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    return {line: round(np.mean(t > line) * 100, 1) for line in lines}

# --- 3. UI LAYOUT ---
tab1, tab2 = st.tabs(["🧠 NEURAL SCANNER", "🔴 LIVE MONITOR"])

with tab1:
    st.sidebar.header("LIGA-VAL")
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135}
    l_name = st.sidebar.selectbox("Välj Liga", list(LEAGUES.keys()))
    
    standings = get_data(LEAGUES[l_name])
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Välj Hemmalag", teams, index=0)
        a_team = c2.selectbox("Välj Bortalag", teams, index=1)
        
        # --- DEN STORA GRÖNA KNAPPEN ---
        if st.button("KÖR NEURAL ANALYS (VISA PROCENT 0.5 - 5.5)"):
            h_d = next(t for t in standings if t['team']['name'] == h_team)
            a_d = next(t for t in standings if t['team']['name'] == a_team)
            
            # Beräkna målsnitt
            h_avg = h_d['all']['goals']['for'] / (h_d['all']['played'] or 1)
            a_avg = a_d['all']['goals']['for'] / (a_d['all']['played'] or 1)
            
            probs = run_sim(h_avg, a_avg)
            
            st.markdown(f"### 🎯 Analys: {h_team} vs {a_team}")
            
            # --- VISA ALLA PROCENT I ETT SVEP ---
            cols = st.columns(6)
            for i, line in enumerate(probs):
                with cols[i]:
                    st.metric(f"ÖVER {line}", f"{probs[line]}%")
                    st.caption(f"Odds: {round(100/probs[line], 2) if probs[line] > 0 else 'N/A'}")
            
            st.success("Simulering av 1 000 000 matcher slutförd.")
    else:
        st.warning("Kunde inte hämta ligan. Kontrollera att säsongen 2025 har startat för denna liga.")

with tab2:
    st.write("Live-matcher dyker upp här när de startar (t.ex. ikväll kl. 20:45).")
