import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. PRO STYLING (MATRIX DESIGN) ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-LIVE", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; box-shadow: 0 0 10px #00ff4122; border-radius: 5px; text-align: center; }
    .stButton>button { background: #00ff41 !important; color: black !important; font-weight: 900; letter-spacing: 3px; border: none; height: 4em; width: 100%; transition: 0.5s; text-transform: uppercase; }
    .stButton>button:hover { background: #ffffff !important; box-shadow: 0 0 50px #00ff41; }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; margin-bottom: 25px; border-radius: 10px; text-align: center; }
    .live-card { background: #080808; padding: 15px; border-left: 5px solid #00ff41; margin-bottom: 10px; border-radius: 5px; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 1.6rem !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 0.8rem !important; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
SEASON = 2025 

# --- 3. NEURAL ENGINE ---

def get_weather(city):
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        cond = res['weather'][0]['main'].lower()
        if any(w in cond for w in ["rain", "snow", "storm"]): return 0.88, f"⚠️ {cond.upper()}"
        return 1.0, "☀️ CLEAR"
    except: return 1.0, "WEATHER N/A"

@st.cache_data(ttl=3600)
def get_standings(l_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={l_id}&season={SEASON}", headers=HEADERS).json()
        return res['response'][0]['league']['standings'][0] if res.get('response') else []
    except: return []

@st.cache_data(ttl=30)
def get_live_data():
    try:
        res = requests.get(f"{BASE_URL}/fixtures?live=all", headers=HEADERS, timeout=10).json()
        return res.get('response', [])
    except: return []

def run_simulation(h_exp, a_exp, w_mod, sims=1000000):
    # Bias: Hemma +10%, Borta -5%
    h_f = h_exp * 1.10 * w_mod
    a_f = a_exp * 0.95 * w_mod
    h_s = np.random.poisson(max(0.1, h_f), sims)
    a_s = np.random.poisson(max(0.1, a_f), sims)
    totals = h_s + a_s
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    results = {}
    for line in lines:
        prob = np.mean(totals > line) * 100
        fair = round(100/prob, 2) if prob > 0 else 99.0
        results[line] = {"prob": round(prob, 1), "fair": fair}
    return results

# --- 4. TABS ---
tab1, tab2, tab3 = st.tabs(["🧠 NEURAL SCANNER", "🔴 LIVE MONITOR", "📊 STANDINGS"])

with tab1:
    st.sidebar.header("🎯 System Control")
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135, "Bundesliga": 78}
    l_name = st.sidebar.selectbox("Välj Liga", list(LEAGUES.keys()))
    l_id = LEAGUES[l_name]
    standings = get_standings(l_id)
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Hemma", teams, index=0)
        a_team = c2.selectbox("Borta", teams, index=1)
        m_odds = st.sidebar.number_input("Odds Över 2.5", value=2.00)
        
        if st.button("EXECUTE OMNI-SCAN (0.5 - 5.5)"):
            with st.spinner("⚡ SIMULATING..."):
                h_d = next(t for t in standings if t['team']['name'] == h_team)
                a_d = next(t for t in standings if t['team']['name'] == a_team)
                w_mod, w_desc = get_weather(h_team)
                
                h_avg = h_d['all']['goals']['for'] / (h_d['all']['played'] or 1)
                a_avg = a_d['all']['goals']['for'] / (a_d['all']['played'] or 1)
                
                probs = run_simulation(h_avg, a_avg, w_mod)
                
                st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2>VÄDER: {w_desc}</div>", unsafe_allow_html=True)
                
                # --- ALLA MÅLLINJER I ETT SVEP (6 KOLUMNER) ---
                res_cols = st.columns(6)
                lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
                for i, line in enumerate(lines):
                    with res_cols[i]:
                        st.metric(f"ÖVER {line}", f"{probs[line]['prob']}%")
                        st.caption(f"Fair: {probs[line]['fair']}")
                
                edge = ((probs[2.5]['prob']/100) * m_odds) - 1
                st.divider()
                v1, v2 = st.columns(2)
                v1.metric("Neural Edge (O2.5)", f"{round(edge*100, 2)}%")
                v2.metric("Kelly Stake (5%)", f"{max(0, int(100000 * edge * 0.05))} kr")

with tab2:
    st.subheader("🔴 Live Feed")
    live_matches = get_live_data()
    if live_matches:
        for m in live_matches:
            h_n, a_n = m['teams']['home']['name'], m['teams']['away']['name']
            h_g, a_g = m['goals']['home'], m['goals']['away']
            st.markdown(f'<div class="live-card">{h_n} {h_g} - {a_g} {a_n} ({m["league"]["name"]})</div>', unsafe_allow_html=True)
    else:
        st.info("Inga matcher live just nu.")

with tab3:
    if standings:
        df = pd.DataFrame([{'Rank': t['rank'], 'Team': t['team']['name'], 'GP': t['all']['played']} for t in standings])
        st.table(df.set_index('Rank'))
