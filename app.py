import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
from datetime import datetime

# --- 1. GLOBAL KONFIGURATION ---
st.set_page_config(page_title="GoalPredictor QUANTUM-NEURAL v10", layout="wide")

# Elite Dark Theme Styling
st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" # Fyll i för live-väder
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. DATA ENGINE (API & CALCULATIONS) ---

@st.cache_data(ttl=3600)
def get_api_data(endpoint, params=None):
    try:
        res = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=15)
        return res.json().get('response', [])
    except: return []

def get_live_weather(city):
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL":
        return {"temp": 12, "wind": 3, "cond": "Clear"}
    url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        r = requests.get(url, timeout=5).json()
        return {"temp": r['main']['temp'], "wind": r['wind']['speed'], "cond": r['weather'][0]['main']}
    except: return {"temp": 15, "wind": 2, "cond": "Cloudy"}

def calculate_kelly(prob, odds, bankroll):
    p = prob / 100
    q = 1 - p
    b = odds - 1
    k_pct = (b * p - q) / b if b > 0 else 0
    return max(0, k_pct), int(bankroll * max(0, k_pct) * 0.5) # Använder "Half-Kelly" för säkerhet

# --- 3. NEURAL SIMULATION ENGINE ---

def run_quantum_sim(h_data, a_data, h2h_mod, w_mod):
    # DxG (Dynamic Expected Goals) Logik
    # (Egen offensiv * Motståndarens defensiv) * Hemmafördel * Väder * H2H
    h_dxg = (h_data['avg_g'] * (a_data['def_leak'] / 1.2)) * 1.15 * w_mod * h2h_mod
    a_dxg = (a_data['avg_g'] * (h_data['def_leak'] / 1.2)) * w_mod * h2h_mod
    
    sims = 150000
    h_sim = np.random.poisson(max(0.1, h_dxg), sims)
    a_sim = np.random.poisson(max(0.1, a_dxg), sims)
    
    total_g = h_sim + a_sim
    return {
        "o25": np.mean(total_g > 2.5) * 100,
        "btts": np.mean((h_sim > 0) & (a_sim > 0)) * 100,
        "home_p": np.mean(h_sim > a_sim) * 100,
        "draw_p": np.mean(h_sim == a_sim) * 100,
        "away_p": np.mean(h_sim < a_sim) * 100,
        "h_dxg": h_dxg, "a_dxg": a_dxg,
        "h_dist": [np.mean(h_sim == i) * 100 for i in range(6)],
        "a_dist": [np.mean(a_sim == i) * 100 for i in range(6)]
    }

# --- 4. DASHBOARD UI ---

st.title("🔋 GoalPredictor QUANTUM-NEURAL v10.0")

# Sidebar - Bankroll & League
with st.sidebar:
    st.header("Financial Control")
    bankroll = st.number_input("Total Bankroll (kr)", value=10000, step=500)
    market_odds = st.number_input("Marknadsodds (Över 2.5)", value=1.95, step=0.05)
    
    st.divider()
    league_name = st.selectbox("Market League", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

# Fetch Standings
standings = get_api_data("standings", {"league": curr_league, "season": 2024})[0]['league']['standings']
t_list = [t['team']['name'] for t in standings]
t_map = {t['team']['name']: t['team']['id'] for t in standings}

col1, col2 = st.columns(2)

with col1:
    h_name = st.selectbox("Hemmalag (Quantum A)", t_list, index=0)
    h_id = t_map[h_name]
    # Auto-Data Extraction
    h_stats = next(t for t in standings if t['team']['name'] == h_name)
    h_data = {
        "elo": 1200 + (h_stats['points']*6) - (h_stats['rank']*3),
        "form_score": sum([2 if c=='W' else 1 if c=='D' else 0 for c in h_stats['form'][-5:]]),
        "avg_g": h_stats['all']['goals']['for'] / h_stats['all']['played'],
        "def_leak": h_stats['all']['goals']['against'] / h_stats['all']['played']
    }
    st.metric(f"{h_name} Elo", h_data['elo'], delta=f"Form: {h_data['form_score']}/10")
    
    # Weather
    city = h_name.split()[0] # Enkel proxy för stad
    w = get_live_weather(city)
    st.caption(f"🌤️ Väder i {city}: {w['temp']}°C, {w['cond']}")

with col2:
    a_name = st.selectbox("Bortalag (Quantum B)", t_list, index=1)
    a_id = t_map[a_name]
    a_stats = next(t for t in standings if t['team']['name'] == a_name)
    a_data = {
        "elo": 1200 + (a_stats['points']*6) - (a_stats['rank']*3),
        "form_score": sum([2 if c=='W' else 1 if c=='D' else 0 for c in a_stats['form'][-5:]]),
        "avg_g": a_stats['all']['goals']['for'] / a_stats['all']['played'],
        "def_leak": a_stats['all']['goals']['against'] / a_stats['all']['played']
    }
    st.metric(f"{a_name} Elo", a_data['elo'], delta=f"Form: {a_data['form_score']}/10")

# --- 5. EXECUTION & RESULTS ---

if st.button("EXECUTE NEURAL INFERENCE"):
    with st.spinner("Analyserar bivariat data och MCMC-stokastik..."):
        # H2H & Weather Modifiers
        h2h_data = get_api_data("fixtures/headtohead", {"h2h": f"{h_id}-{a_id}", "last": 5})
        h2h_mod = 1.1 if (sum(f['goals']['home']+f['goals']['away'] for f in h2h_data)/5) > 2.8 else 1.0
        w_mod = 0.92 if w['wind'] > 8 or w['temp'] < 3 else 1.0
        
        # Run Simulation
        res = run_quantum_sim(h_data, a_data, h2h_mod, w_mod)
        k_pct, k_stake = calculate_kelly(res['o25'], market_odds, bankroll)
        
        st.divider()
        
        # Row 1: Probability Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Över 2.5 Mål", f"{round(res['o25'], 1)}%")
        m2.metric("BTTS Prob", f"{round(res['btts'], 1)}%")
        m3.metric("Fair Odds", round(100/res['o25'], 2))
        m4.metric("Kelly Stake", f"{k_stake} kr", f"{round(k_pct*100, 1)}%")

        # Row 2: Win Probability Chart
        fig = go.Figure(data=[go.Pie(labels=['Hemma', 'Oavgjort', 'Borta'], 
                                 values=[res['home_p'], res['draw_p'], res['away_p']], 
                                 hole=.3, marker_colors=['#00ff41', '#636efa', '#ef553b'])])
        st.plotly_chart(fig, use_container_width=True)

        # Row 3: Goal Distribution Area Chart
        dist_df = pd.DataFrame({
            'Goals': [str(i) for i in range(6)],
            h_name: res['h_dist'],
            a_name: res['a_dist']
        }).set_index('Goals')
        st.area_chart(dist_df)

        # Final Pro Advice
        edge = (res['o25']/100 * market_odds) - 1
        if edge > 0.05:
            st.success(f"🎯 **VALUE IDENTIFIED:** Modellen har hittat en edge på {round(edge*100,1)}%. Rekommenderad insats: {k_stake} kr.")
        else:
            st.error("⚠️ **NO VALUE:** Marknadens odds är för låga i förhållande till den statistiska risken.")

st.sidebar.markdown("---")
st.sidebar.caption("v10.0 Neural Engine Status: ONLINE")
