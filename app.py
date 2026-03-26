import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="GoalPredictor v150.0 FELSÄKER", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; border-radius: 5px; }
    .stButton>button { background: #00ff41; color: black; font-weight: 900; width: 100%; border-radius: 0; }
    .neural-box { background: #050505; padding: 20px; border: 2px solid #00ff41; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API KEYS (Verifiera dessa på dina dashboards!) ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}

# --- 3. ROBUST DATA ENGINE ---

@st.cache_data(ttl=3600)
def get_league_data(l_id):
    # Prova 2025 först, annars 2024
    for season in [2025, 2024]:
        try:
            url = f"https://v3.football.api-sports.io{l_id}&season={season}"
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            if res.get('response') and res['response'][0]['league']['standings'][0]:
                return res['response'][0]['league']['standings'][0], season
        except: continue
    return None, None

def get_weather_multiplier(team_name):
    try:
        # Vi gissar stad från lagnamnet
        city = team_name.split(" ")[0]
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=3).json()
        if res.get('main'):
            temp = res['main']['temp']
            cond = res['weather'][0]['main'].lower()
            if any(w in cond for w in ["rain", "snow", "clouds"]): return 0.88, f"☁️ {cond.upper()} ({temp}°C)"
            return 1.0, f"☀️ CLEAR ({temp}°C)"
    except: pass
    return 1.0, "Väder: Neutralt (Data saknas)"

def run_sim(h_exp, a_exp, w_mod, sims=1000000):
    h_s = np.random.poisson(max(0.1, h_exp * w_mod), sims)
    a_s = np.random.poisson(max(0.1, a_exp * w_mod), sims)
    t = h_s + a_s
    res = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        p = np.mean(t > line) * 100
        res[line] = {"prob": round(p, 1), "fair": round(100/p, 2) if p > 0 else 99}
    return res

# --- 4. UI ---
st.title("🧠 GOALPREDICTOR v150.0")

tab1, tab2 = st.tabs(["🔍 SCANNER", "🔴 LIVE"])

with tab1:
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135}
    l_name = st.selectbox("Välj Liga", list(LEAGUES.keys()))
    
    standings, active_season = get_league_data(LEAGUES[l_name])
    
    if standings:
        st.success(f"Data laddad för säsong: {active_season}")
        teams = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Hemmalag", teams, index=0)
        a_team = c2.selectbox("Bortalag", teams, index=1)
        
        if st.button("KÖR NEURAL ANALYS"):
            h_data = next(t for t in standings if t['team']['name'] == h_team)
            a_data = next(t for t in standings if t['team']['name'] == a_team)
            
            # Beräkna xG (Hemma +10%, Borta -5%)
            h_exp = (h_data['all']['goals']['for'] / (h_data['all']['played'] or 1)) * 1.10
            a_exp = (a_data['all']['goals']['for'] / (a_data['all']['played'] or 1)) * 0.95
            
            w_mod, w_txt = get_weather_multiplier(h_team)
            probs = run_sim(h_exp, a_exp, w_mod)
            
            st.info(w_txt)
            st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2></div>", unsafe_allow_html=True)
            
            grid = st.columns(6)
            for i, line in enumerate(probs):
                grid[i].metric(f"Över {line}", f"{probs[line]['prob']}%")
                grid[i].caption(f"Odds: {probs[line]['fair']}")
    else:
        st.error("Kunde inte hämta tabellen. Detta beror ofta på att API-nyckeln är ogiltig eller att du gjort för många anrop idag.")

with tab2:
    st.subheader("Aktiva matcher (Live)")
    st.write("Söker efter live-data...")
    # Här kan du lägga till live-loopen från tidigare, 
    # men kontrollera först att Scanner-fliken fungerar!

