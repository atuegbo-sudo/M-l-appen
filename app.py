import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. PRO STYLING (MATRIX OPTIMIZED) ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-LIVE", layout="wide")

st.markdown("""
    <style>
    /* Bakgrund och Matrix-känsla */
    .stApp { background-color: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    
    /* Behållare för mållinjer (Grid) */
    .goal-grid { display: flex; justify-content: space-between; gap: 10px; margin: 20px 0; }
    .goal-item { background: #050505; border: 1px solid #00ff41; padding: 15px; border-radius: 5px; flex: 1; text-align: center; box-shadow: 0 0 10px #00ff4133; }
    
    /* Metrics-styling */
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 1.6rem !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 0.8rem !important; }
    
    /* Knappar och Boxar */
    .stButton>button { background: #00ff41 !important; color: black !important; font-weight: 900; height: 3.5em; width: 100%; border: none; text-transform: uppercase; }
    .stButton>button:hover { background: #ffffff !important; box-shadow: 0 0 30px #00ff41; }
    .neural-box { background: #050505; padding: 20px; border: 2px solid #00ff41; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
SEASON = 2025

# --- 3. ENGINES ---
def get_weather(city):
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        main = res['weather'][0]['main'].lower()
        if any(x in main for x in ["rain", "snow", "storm"]): return 0.85, f"⚠️ {main.upper()}"
        return 1.0, "☀️ CLEAR"
    except: return 1.0, "N/A"

@st.cache_data(ttl=3600)
def get_standings(l_id):
    res = requests.get(f"{BASE_URL}/standings?league={l_id}&season={SEASON}", headers=HEADERS).json()
    return res['response']['league']['standings'] if res.get('response') else []

def run_simulation(h_exp, a_exp, w_mod):
    h_final, a_final = h_exp * 1.10 * w_mod, a_exp * 0.95 * w_mod
    h_s = np.random.poisson(max(0.1, h_final), 1000000)
    a_s = np.random.poisson(max(0.1, a_final), 1000000)
    totals = h_s + a_s
    res = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        p = np.mean(totals > line) * 100
        res[line] = {"prob": round(p, 1), "fair": round(100/p, 2) if p > 0 else 99}
    return res

# --- 4. UI ---
tab1, tab2, tab3 = st.tabs(["🧠 SCANNER", "🔴 LIVE", "📊 STATS"])

with tab1:
    l_id = st.sidebar.selectbox("Liga", {"Allsvenskan": 113, "Premier League": 39, "VM-kval": 3}.values())
    standings = get_standings(l_id)
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        h_t, a_t = st.columns(2)
        h_team = h_t.selectbox("Hemma", teams, index=0)
        a_team = a_t.selectbox("Borta", teams, index=1)
        m_odds = st.sidebar.number_input("Odds O2.5", value=2.0)
        
        if st.button("EXECUTE OMNI-SCAN"):
            h_d = next(t for t in standings if t['team']['name'] == h_team)
            a_d = next(t for t in standings if t['team']['name'] == a_team)
            w_mod, w_txt = get_weather(h_team)
            
            h_avg = h_d['all']['goals']['for'] / (h_d['all']['played'] or 1)
            a_avg = a_d['all']['goals']['for'] / (a_d['all']['played'] or 1)
            
            probs = run_simulation(h_avg, a_avg, w_mod)
            
            # --- MATRIX-LINJEN (ALLA MÅL I ETT SVEP) ---
            st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2>VÄDER: {w_txt}</div>", unsafe_allow_html=True)
            
            # Här skapas de 6 kolumnerna på en rad
            cols = st.columns(6)
            for i, line in enumerate(probs):
                with cols[i]:
                    st.metric(f"ÖVER {line}", f"{probs[line]['prob']}%")
                    st.caption(f"Fair: {probs[line]['fair']}")
            
            edge = ((probs[2.5]['prob']/100) * m_odds) - 1
            st.divider()
            st.metric("Neural Edge (O2.5)", f"{round(edge*100, 2)}%", delta=f"{round(edge*100, 1)}%")

with tab2:
    st.info("Söker live-matcher... Prova vid matchstart kl 20:45.")
