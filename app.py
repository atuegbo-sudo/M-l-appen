import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. PRO STYLING (Från din första version + Pro Upgrade) ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-GLOBAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 20px; border: 1px solid #00ff41; box-shadow: 0 0 15px #00ff4122; }
    .stButton>button { background: #00ff41; color: black; font-weight: 900; letter-spacing: 3px; border: none; height: 3.5em; width: 100%; transition: 0.5s; text-transform: uppercase; }
    .stButton>button:hover { background: #ffffff; box-shadow: 0 0 50px #00ff41; }
    .live-card { background: #080808; padding: 20px; border-left: 5px solid #00ff41; margin-bottom: 15px; border-radius: 5px; }
    .neural-box { background: #050505; padding: 35px; border: 2px solid #00ff41; margin-bottom: 30px; text-align: center; }
    .status-live { color: #ff0000; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 3. NEURAL ENGINES ---

@st.cache_data(ttl=30)
def get_all_live_global():
    """Hämtar ALLA live-matcher i hela världen (utan filter)"""
    try:
        res = requests.get(f"{BASE_URL}/fixtures?live=all", headers=HEADERS, timeout=15).json()
        return res.get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    """Hämtar tabell (testar 2025 först, sen 2024)"""
    for season in [2025, 2024]:
        try:
            res = requests.get(f"{BASE_URL}/standings?league={league_id}&season={season}", headers=HEADERS).json()
            if res.get('response'): return res['response']['league']['standings'][0], season
        except: continue
    return None, None

def get_weather_impact(city):
    """Väder-analys för mål-debuff"""
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        w = requests.get(url, timeout=5).json()
        cond = w['weather'][0]['main'].lower()
        temp = w['main']['temp']
        mod = 0.88 if any(x in cond for x in ["rain", "snow", "storm"]) else 1.0
        return mod, f"{cond.upper()} ({temp}°C)"
    except: return 1.0, "Väder: Neutralt"

def run_neural_sim(h_exp, a_exp, w_mod, sims=1000000):
    """Neural 1M Simulation för alla mållinjer"""
    h_s = np.random.poisson(max(0.1, h_exp * w_mod), sims)
    a_s = np.random.poisson(max(0.1, a_exp * w_mod), sims)
    totals = h_s + a_s
    results = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        p = np.mean(totals > line) * 100
        results[line] = {"prob": round(p, 1), "fair": round(100/p, 2) if p > 0 else 99}
    return results

# --- 4. MAIN DASHBOARD ---
tab1, tab2, tab3 = st.tabs(["🧠 NEURAL SCANNER", "🔴 GLOBAL LIVE", "📊 STANDINGS"])

with tab1:
    st.sidebar.header("🎯 System Control")
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135, "Bundesliga": 78}
    l_name = st.sidebar.selectbox("Marknad", list(LEAGUES.keys()))
    
    standings, active_yr = get_league_standings(LEAGUES[l_name])
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Home (Hämta Väder)", teams, index=0)
        a_team = c2.selectbox("Away Target", teams, index=1)
        m_odds = st.sidebar.number_input("Ditt Odds (O2.5)", value=2.00)
        
        if st.button("EXECUTE OMNI-SCAN (1.0M SIMS)"):
            h_data = next(t for t in standings if t['team']['name'] == h_team)
            a_data = next(t for t in standings if t['team']['name'] == a_team)
            
            # Väder + Hemma/Borta fördel
            w_mod, w_txt = get_weather_impact(h_team)
            h_exp = (h_data['all']['goals']['for'] / (h_data['all']['played'] or 1)) * 1.10
            a_exp = (a_data['all']['goals']['for'] / (a_data['all']['played'] or 1)) * 0.95
            
            probs = run_neural_sim(h_exp, a_exp, w_mod)
            
            st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2><p>{w_txt} | Säsong: {active_yr}</p></div>", unsafe_allow_html=True)
            
            res_cols = st.columns(6)
            for i, line in enumerate(probs):
                res_cols[i].metric(f"Över {line}", f"{probs[line]['prob']}%")
                res_cols[i].caption(f"Fair: {probs[line]['fair']}")
            
            # Value & Kelly
            edge = ((probs[2.5]['prob']/100) * m_odds) - 1
            st.divider()
            m1, m2 = st.columns(2)
            m1.metric("Neural Edge (O2.5)", f"{round(edge*100, 2)}%")
            m2.metric("Kelly Stake (5%)", f"{max(0, int(100000 * edge * 0.05))} kr")

with tab2:
    st.subheader("🔴 Global Live Tracker (Alla länder/ligor)")
    live_matches = get_all_live_global()
    
    if live_matches:
        col_l, col_r = st.columns(2)
        for i, m in enumerate(live_matches):
            h, a = m['teams']['home']['name'], m['teams']['away']['name']
            hg, ag = m['goals']['home'], m['goals']['away']
            elap = m['fixture']['status']['elapsed']
            target = col_l if i % 2 == 0 else col_r
            
            with target:
                st.markdown(f"""
                <div class="live-card">
                    <span class="status-live">LIVE {elap}'</span> | <small>{m['league']['name']} ({m['league']['country']})</small><br>
                    <span style="font-size: 1.3em;">{h} {hg} - {ag} {a}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Inga live-matcher hittades just nu. Systemet är redo för nästa avspark.")

with tab3:
    if standings:
        st.subheader(f"Tabell: {l_name} ({active_yr})")
        df = pd.DataFrame([{'Rank': t['rank'], 'Lag': t['team']['name'], 'GP': t['all']['played'], 'Mål': f"{t['all']['goals']['for']}:{t['all']['goals']['against']}", 'P': t['points']} for t in standings])
        st.table(df.set_index('Rank'))

st.sidebar.markdown("---")
if st.sidebar.button("FORCE REFRESH"):
    st.cache_data.clear()
    st.rerun()
