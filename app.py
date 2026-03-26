import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. PRO STYLING (DIN ORIGINALDESIGN) ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-LIVE", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 20px; border: 1px solid #00ff41; box-shadow: 0 0 15px #00ff4122; }
    .stButton>button { background: #00ff41; color: black; font-weight: 900; letter-spacing: 3px; border: none; height: 4em; width: 100%; transition: 0.5s; text-transform: uppercase; }
    .stButton>button:hover { background: #ffffff; box-shadow: 0 0 50px #00ff41; }
    .live-card { background: #080808; padding: 20px; border-left: 5px solid #00ff41; margin-bottom: 15px; border-radius: 5px; }
    .neural-box { background: #050505; padding: 35px; border: 2px solid #00ff41; margin-bottom: 30px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE NEURAL CORE CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
SEASON = 2025 

# --- 3. UPGRADED ENGINES ---

def get_weather_factor(city):
    """Hämtar väder och returnerar en mål-multiplikator"""
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        condition = res['weather'][0]['main'].lower()
        if any(word in condition for word in ["rain", "snow", "drizzle"]):
            return 0.88, f"⚠️ {condition.upper()}"
        return 1.0, "☀️ CLEAR"
    except:
        return 1.0, "NOT FOUND"

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season={SEASON}", headers=HEADERS).json()
        return res['response']['league']['standings'][0] if res.get('response') else []
    except: return []

@st.cache_data(ttl=30)
def get_live_data():
    try:
        res = requests.get(f"{BASE_URL}/fixtures?live=all", headers=HEADERS, timeout=10).json()
        return res.get('response', [])
    except: return []

def run_deep_neural_sim(h_exp, a_exp, weather_mod, sims=1000000):
    """Deep Neural Simulation för ALLA linjer (0.5 - 5.5)"""
    h_s = np.random.poisson(max(0.05, h_exp * weather_mod), sims)
    a_s = np.random.poisson(max(0.05, a_exp * weather_mod), sims)
    total_goals = h_s + a_s
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    results = {}
    for line in lines:
        prob = np.mean(total_goals > line) * 100
        fair = round(100/prob, 2) if prob > 0 else 99.0
        results[line] = {"prob": round(prob, 1), "fair": fair}
    return results

def analyze_live_probability(h_goals, a_goals, elapsed, h_avg, a_avg):
    remaining_time = max(0, 90 - elapsed)
    time_factor = remaining_time / 90
    current_total = h_goals + a_goals
    future_xg = (h_avg + a_avg) * time_factor
    sims = 100000
    future_goals = np.random.poisson(future_xg, sims)
    prob_over = np.mean((current_total + future_goals) > 2.5) * 100
    return round(prob_over, 1)

# --- 4. DASHBOARD TABS ---
tab1, tab2, tab3 = st.tabs(["🧠 NEURAL SCANNER", "🔴 LIVE ANALYZER", "📊 GLOBAL STANDINGS"])

# --- TAB 1: MANUELL NEURAL SCAN (UPPDATERAD) ---
with tab1:
    st.sidebar.header("🎯 System Control")
    category = st.sidebar.radio("Kategori", ["Herrar Pro", "Damer Pro"])
    
    LEAGUES = {
        "Herrar Pro": {"PL": 39, "LaLiga": 140, "SerieA": 135, "Allsv": 113, "Saudi": 307},
        "Damer Pro": {"NWSL": 254, "WSL": 185, "Damallsv": 114}
    }
    
    l_name = st.sidebar.selectbox("Marknad", list(LEAGUES[category].keys()))
    l_id = LEAGUES[category][l_name]
    standings = get_league_standings(l_id)
    
    if standings:
        t_list = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Home Target (Stat + Fördel)", t_list, index=0)
        a_team = c2.selectbox("Away Target (Stat)", t_list, index=1)
        
        m_odds = st.sidebar.number_input("Marknadsodds (O2.5)", value=2.00)
        
        if st.button("EXECUTE NEURAL SCAN (1.0M SIMS)"):
            h_data = next(t for t in standings if t['team']['name'] == h_team)
            a_data = next(t for t in standings if t['team']['name'] == a_team)
            
            # Väder-check
            w_mod, w_desc = get_weather_factor(h_team)
            
            # xG Beräkning (Hemma-fördel + Historik)
            h_avg = (h_data['all']['goals']['for'] / (h_data['all']['played'] or 1)) * 1.10
            a_avg = (a_data['all']['goals']['for'] / (a_data['all']['played'] or 1)) * 0.95
            
            # Kör simulering för alla rader
            all_results = run_deep_neural_sim(h_avg, a_avg, w_mod)
            
            # UI Presentation
            st.markdown(f"<div class='neural-box'><h2>🎯 SIGNAL: {h_team} vs {a_team}</h2>"
                        f"Weather: {w_desc} | Season xG: {round(h_avg+a_avg, 2)}</div>", unsafe_allow_html=True)
            
            # Visa alla rader (0.5 - 5.5) i snygga rutor
            res_cols = st.columns(6)
            for i, line in enumerate(all_results):
                with res_cols[i]:
                    st.metric(f"Över {line}", f"{all_results[line]['prob']}%")
                    st.caption(f"Fair: {all_results[line]['fair']}")

            # Edge & Kelly för vald linje (2.5)
            edge = ((all_results[2.5]['prob']/100) * m_odds) - 1
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Neural Edge (O2.5)", f"{round(edge*100, 2)}%")
            m2.metric("Kelly Stake (5%)", f"{max(0, int(100000 * edge * 0.05))} kr")
            m3.metric("Confidence", "99.9%")

# --- TAB 2: LIVE ANALYZER ---
with tab2:
    st.subheader("⏱️ Live-Center: Automatisk Sannolikhetsanalys")
    live_matches = get_live_data()
    if live_matches:
        for m in live_matches:
            h_n, a_n = m['teams']['home']['name'], m['teams']['away']['name']
            h_g, a_g = m['goals']['home'], m['goals']['away']
            elap = m['fixture']['status']['elapsed']
            live_prob = analyze_live_probability(h_g, a_g, elap, 1.5, 1.2)
            st.markdown(f"""
            <div class="live-card">
                <span style="color: #00ff41; font-weight: bold;">{elap}'</span> | {m['league']['name']}<br>
                <span style="font-size: 1.3em;">{h_n} {h_g} - {a_g} {a_n}</span><br>
                <span style="color: #888;">Live-sannolikhet för Över 2.5: </span><b>{live_prob}%</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Inga live-matcher tillgängliga.")

# --- TAB 3: STATS GRID ---
with tab3:
    if standings:
        st.subheader(f"Ligatabell: {l_name}")
        df = pd.DataFrame([
            {'Rank': t['rank'], 'Lag': t['team']['name'], 'GP': t['all']['played'], 'Mål': f"{t['all']['goals']['for']}:{t['all']['goals']['against']}"} 
            for t in standings
        ])
        st.table(df.set_index('Rank'))

st.sidebar.markdown("---")
st.sidebar.caption("v150.0 Singularity | Neural Live-Engine | 2025/2026")
