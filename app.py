  import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. PRO STYLING (MATRIX & GRID OPTIMIZATION) ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-LIVE", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; box-shadow: 0 0 10px #00ff4122; border-radius: 5px; text-align: center; }
    .stButton>button { background: #00ff41; color: black; font-weight: 900; letter-spacing: 3px; border: none; height: 3.5em; width: 100%; transition: 0.5s; text-transform: uppercase; margin-top: 20px; }
    .stButton>button:hover { background: #ffffff; box-shadow: 0 0 40px #00ff41; }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; margin-bottom: 25px; border-radius: 10px; }
    .live-card { background: #080808; padding: 15px; border-left: 5px solid #00ff41; margin-bottom: 10px; }
    /* Gör siffrorna i metrics mer synliga */
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 0.9rem !important; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
SEASON = 2025 

# --- 3. NEURAL ENGINES (MULTILINE + WEATHER + BIAS) ---

def get_weather_factor(city):
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        condition = res['weather'][0]['main'].lower()
        if any(word in condition for word in ["rain", "snow", "drizzle", "clouds"]):
            return 0.90, f"⛈️ {condition.upper()}"
        return 1.0, "☀️ CLEAR"
    except: return 1.0, "N/A"

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season={SEASON}", headers=HEADERS).json()
        return res['response'][0]['league']['standings'][0] if res.get('response') else []
    except: return []

def run_full_spectrum_sim(h_exp, a_exp, weather_mod, sims=1000000):
    # Hemma/Borta bias + Väder
    h_final = h_exp * 1.10 * weather_mod
    a_final = a_exp * 0.95 * weather_mod
    
    h_s = np.random.poisson(max(0.1, h_final), sims)
    a_s = np.random.poisson(max(0.1, a_final), sims)
    totals = h_s + a_s
    
    results = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        prob = np.mean(totals > line) * 100
        results[line] = {"prob": round(prob, 1), "fair": round(100/prob, 2) if prob > 0 else 99}
    return results

# --- 4. DASHBOARD ---
tab1, tab2, tab3 = st.tabs(["🧠 NEURAL SCANNER", "🔴 LIVE ANALYZER", "📊 STANDINGS"])

with tab1:
    st.sidebar.header("🎯 System Control")
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135, "Bundesliga": 78}
    l_name = st.sidebar.selectbox("Välj Liga", list(LEAGUES.keys()))
    l_id = LEAGUES[l_name]
    
    standings = get_league_standings(l_id)
    
    if standings:
        t_list = sorted([t['team']['name'] for t in standings])
        col_h, col_a = st.columns(2)
        h_team = col_h.selectbox("Hemmalag", t_list, index=0)
        a_team = col_a.selectbox("Bortalag", t_list, index=1)
        
        m_odds = st.sidebar.number_input("Marknadsodds (Över 2.5)", value=2.00)
        
        if st.button("EXECUTE OMNI-SCAN (ALL LINES)"):
            with st.spinner("⚡ SIMULATING 1,000,000 MATCHES..."):
                h_data = next(t for t in standings if t['team']['name'] == h_team)
                a_data = next(t for t in standings if t['team']['name'] == a_team)
                
                w_mod, w_desc = get_weather_factor(h_team)
                
                # Grund-xG från historik
                h_avg = (h_data['all']['goals']['for'] / (h_data['all']['played'] or 1))
                a_avg = (a_data['all']['goals']['for'] / (a_data['all']['played'] or 1))
                
                # Kör simulering
                probs = run_full_spectrum_sim(h_avg, a_avg, w_mod)
                
                # --- ALLT I ETT SVEP VISNING ---
                st.markdown(f"<div class='neural-box'><h2 style='text-align:center; color:#00ff41;'>{h_team} vs {a_team}</h2>"
                            f"<p style='text-align:center;'>Väder: {w_desc} | Hemmafördel: AKTIV | Historik: Inkluderad</p></div>", unsafe_allow_html=True)
                
                # 6 Kolumner för att se allt samtidigt
                res_cols = st.columns(6)
                lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
                
                for i, line in enumerate(lines):
                    with res_cols[i]:
                        st.metric(f"ÖVER {line}", f"{probs[line]['prob']}%")
                        st.caption(f"Fair: {probs[line]['fair']}")
                
                # Edge-analys
                edge = ((probs[2.5]['prob']/100) * m_odds) - 1
                st.divider()
                v1, v2 = st.columns(2)
                v1.metric("Neural Edge (O2.5)", f"{round(edge*100, 2)}%")
                v2.metric("Kelly Stake (5%)", f"{max(0, int(100000 * edge * 0.05))} kr")

# --- TAB 2 & 3 (Förenklat för prestanda) ---
with tab2:
    st.info("Live-analys baseras på realtids-API. Öppna fliken när matcher pågår.")
with tab3:
    if standings:
        st.dataframe(pd.DataFrame([{'Rank': t['rank'], 'Team': t['team']['name'], 'Points': t['points']} for t in standings]).set_index('Rank'), use_container_width=True)
           
