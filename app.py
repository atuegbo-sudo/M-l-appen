import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. GLOBAL KONFIGURATION & STYLING ---
st.set_page_config(page_title="GoalPredictor PLATINUM v10.2", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; width: 100%; border: none; height: 3.5em; }
    .status-v { color: #00ff41; font-weight: bold; }
    .status-f { color: #ff4b4b; font-weight: bold; }
    .status-o { color: #ffbd45; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# API-NYCKLAR
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" # Valfri
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. AVANCERAD DATA-MOTOR ---

@st.cache_data(ttl=3600)
def get_api_data(endpoint, params=None):
    try:
        res = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=15).json()
        return res.get('response', [])
    except: return []

def get_live_weather(city):
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL":
        return {"temp": 12, "wind": 3, "cond": "Klar himmel", "icon": "☀️"}
    url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric&lang=se"
    try:
        r = requests.get(url, timeout=5).json()
        return {"temp": r['main']['temp'], "wind": r['wind']['speed'], "cond": r['weather'][0]['description'], "icon": "☁️"}
    except: return {"temp": 15, "wind": 2, "cond": "Normalt", "icon": "🌤️"}

def get_recent_results_table(team_id, league_id):
    """Skapar tabellen med V/O/F och ikoner"""
    data = get_api_data("fixtures", {"team": team_id, "league": league_id, "last": 5, "status": "FT"})
    results = []
    for item in data:
        is_home = item['teams']['home']['id'] == team_id
        t_goals = item['goals']['home'] if is_home else item['goals']['away']
        o_goals = item['goals']['away'] if is_home else item['goals']['home']
        opp = item['teams']['away']['name'] if is_home else item['teams']['home']['name']
        
        if t_goals > o_goals: res = "✅ V"
        elif t_goals < o_goals: res = "❌ F"
        else: res = "➖ O"
        
        results.append({"Datum": item['fixture']['date'][:10], "Motstånd": opp, "Resultat": f"{item['goals']['home']}-{item['goals']['away']}", "Status": res})
    return pd.DataFrame(results)

# --- 3. NEURAL QUANTUM ENGINE ---

def run_neural_engine(h_data, a_data, h2h_mod, w_mod):
    # DxG (Dynamic Expected Goals) - Kraftigt viktad modell
    h_dxg = (h_data['avg_g'] * (a_data['def_leak'] / 1.2)) * 1.18 * h2h_mod * w_mod
    a_dxg = (a_data['avg_g'] * (h_data['def_leak'] / 1.2)) * h2h_mod * w_mod
    
    sims = 150000
    h_sim = np.random.poisson(max(0.1, h_dxg), sims)
    a_sim = np.random.poisson(max(0.1, a_dxg), sims)
    
    return {
        "o25": np.mean((h_sim + a_sim) > 2.5) * 100,
        "btts": np.mean((h_sim > 0) & (a_sim > 0)) * 100,
        "home_p": np.mean(h_sim > a_sim) * 100,
        "draw_p": np.mean(h_sim == a_sim) * 100,
        "away_p": np.mean(h_sim < a_sim) * 100,
        "h_dxg": h_dxg, "a_dxg": a_dxg,
        "h_dist": [np.mean(h_sim == i) * 100 for i in range(6)],
        "a_dist": [np.mean(a_sim == i) * 100 for i in range(6)]
    }

# --- 4. HUVUD-GRÄNSSNITT ---

st.title("🛡️ GoalPredictor PLATINUM v10.2")
st.subheader("Quantum-Neural Match Analysis & Risk Assessment")

with st.sidebar:
    st.header("💳 Bankroll Management")
    bankroll = st.number_input("Din Kassa (kr)", value=10000)
    market_odds = st.number_input("Odds för Över 2.5", value=1.95, step=0.05)
    st.divider()
    league_name = st.selectbox("Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

# Hämta Master-data (Felsäker)
with st.spinner("Ansluter till Quantum-databasen..."):
    raw_res = get_api_data("standings", {"league": curr_league, "season": 2024})
    standings = []
    if raw_res:
        # Hanterar både listor och nästlade listor [[...]]
        data = raw_res[0]['league']['standings']
        standings = data[0] if isinstance(data[0], list) else data
    
    if not standings:
        st.error("Kunde inte hämta data. Prova en annan liga.")
        st.stop()

    t_list = sorted([t['team']['name'] for t in standings])
    t_map = {t['team']['name']: t['team']['id'] for t in standings}

col1, col2 = st.columns(2)

with col1:
    h_name = st.selectbox("Hemmalag", t_list, index=0)
    h_id = t_map[h_name]
    h_stats = next(t for t in standings if t['team']['name'] == h_name)
    
    # Auto-Elo & Form
    h_elo = 1200 + (h_stats['points']*7) - (h_stats['rank']*4)
    h_form_score = sum([2 if c=='W' else 1 if c=='D' else 0 for c in h_stats['form'][-5:]]) if h_stats['form'] else 5
    h_avg = h_stats['all']['goals']['for'] / h_stats['all']['played'] if h_stats['all']['played'] > 0 else 1.3
    h_def = h_stats['all']['goals']['against'] / h_stats['all']['played'] if h_stats['all']['played'] > 0 else 1.3
    
    st.metric(f"{h_name} Power Index", h_elo, delta=f"Form: {h_form_score}/10")
    
    # Väder (Hämtas för hemmalagets stad)
    w = get_live_weather(h_name)
    st.info(f"{w['icon']} **Väder:** {w['temp']}°C, {w['cond']}")
    
    st.write("**Senaste resultat:**")
    st.dataframe(get_recent_results_table(h_id, curr_league), hide_index=True)

with col2:
    a_name = st.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)
    a_id = t_map[a_name]
    a_stats = next(t for t in standings if t['team']['name'] == a_name)
    
    a_elo = 1200 + (a_stats['points']*7) - (a_stats['rank']*4)
    a_form_score = sum([2 if c=='W' else 1 if c=='D' else 0 for c in a_stats['form'][-5:]]) if a_stats['form'] else 5
    a_avg = a_stats['all']['goals']['for'] / a_stats['all']['played'] if a_stats['all']['played'] > 0 else 1.2
    a_def = a_stats['all']['goals']['against'] / a_stats['all']['played'] if a_stats['all']['played'] > 0 else 1.2
    
    st.metric(f"{a_name} Power Index", a_elo, delta=f"Form: {a_form_score}/10")
    st.write("") # Spacer
    st.write("")
    st.write("**Senaste resultat:**")
    st.dataframe(get_recent_results_table(a_id, curr_league), hide_index=True)

# --- 5. ANALYS-KÖRNING ---

if st.button("KÖR FULLSTÄNDIG PLATINUM-ANALYS"):
    with st.spinner("Kör 150 000 Neurala simuleringar..."):
        # 1. H2H Check
        h2h_raw = get_api_data("fixtures/headtohead", {"h2h": f"{h_id}-{a_id}", "last": 5})
        h2h_mod = 1.12 if h2h_raw and (sum(f['goals']['home']+f['goals']['away'] for f in h2h_raw)/5) > 2.7 else 1.0
        
        # 2. Väder-modifier (Vind över 8 m/s sänker mål)
        w_mod = 0.90 if w['wind'] > 8 else 1.0
        
        # 3. Neural Engine
        h_data = {'avg_g': h_avg, 'def_leak': h_def}
        a_data = {'avg_g': a_avg, 'def_leak': a_def}
        res = run_neural_engine(h_data, a_data, h2h_mod, w_mod)
        
        # 4. Kelly Criterion (25% fractional)
        edge = (res['o25']/100 * market_odds) - 1
        k_pct = (market_odds * (res['o25']/100) - 1) / (market_odds - 1) if edge > 0 else 0
        suggested_stake = int(bankroll * k_pct * 0.25)

        st.divider()
        
        # Metrics Display
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Över 2.5 Mål", f"{round(res['o25'], 1)}%")
        m2.metric("BTTS (Båda gör mål)", f"{round(res['btts'], 1)}%")
        m3.metric("Rättvist Odds", round(100/res['o25'], 2))
        m4.metric("Edge", f"{round(edge*100, 1)}%")

        # Resultat-visualisering
        c1, c2 = st.columns([1, 2])
        with c1:
            st.write("### Sannolikhet 1X2")
            win_df = pd.DataFrame({'Val': ['Hemma', 'Oavgjort', 'Borta'], 'Chans': [res['home_p'], res['draw_p'], res['away_p']]}).set_index('Val')
            st.bar_chart(win_df)
        with c2:
            st.write("### Målfördelning (DxG)")
            dist_df = pd.DataFrame({'Mål': [str(i) for i in range(6)], h_name: res['h_dist'], a_name: res['a_dist']}).set_index('Mål')
            st.area_chart(dist_df)

        # Betting Advice
        if edge > 0.03:
            st.success(f"🔥 **VÄRDE IDENTIFIERAT!** Rekommenderad insats: **{suggested_stake} kr** ({round(k_pct*25, 1)}% av kassa).")
        else:
            st.error("⚠️ **INGET VÄRDE.** Marknadens odds är för låga för denna risknivå.")

st.sidebar.markdown("---")
st.sidebar.caption("v10.2 Platinum Engine: Online")
