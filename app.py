import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. PRO-TERMINAL STYLING ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-GLOBAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; border-radius: 5px; }
    .stButton>button { background: #00ff41; color: black; font-weight: 900; width: 100%; height: 3.5em; border: none; transition: 0.3s; }
    .stButton>button:hover { background: #ffffff; box-shadow: 0 0 30px #00ff41; }
    .live-card { background: #080808; padding: 20px; border-left: 5px solid #00ff41; margin-bottom: 15px; border-radius: 8px; border: 1px solid #111; }
    .status-live { color: #ff0000; font-weight: bold; animation: blinker 1.5s linear infinite; font-size: 0.9em; }
    @keyframes blinker { 50% { opacity: 0; } }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; text-align: center; margin-bottom: 25px; }
    h2, h3 { color: #00ff41 !important; letter-spacing: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG (SÄKERHETSHANTERING) ---
# För att köra detta på GitHub/Streamlit Cloud: 
# Lägg till dina nycklar i Streamlit Cloud Dashboard under "Secrets".
try:
    FOOTBALL_API_KEY = st.secrets["FOOTBALL_API_KEY"]
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
except:
    st.error("⚠️ API-nycklar saknas! Lägg till dem i Streamlit Secrets.")
    st.stop()

SPORTSDB_KEY = "3" # Offentlig testnyckel (Säker för GitHub)
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 3. DEEP SCAN ENGINES ---

@st.cache_data(ttl=60)
def get_global_leagues():
    url = f"https://www.thesportsdb.com{SPORTSDB_KEY}/all_leagues.php"
    try:
        res = requests.get(url).json()
        return res.get('leagues', [])
    except: return []

@st.cache_data(ttl=20)
def get_deep_live_scan():
    try:
        url_live = f"{BASE_URL}/fixtures?live=all"
        res_live = requests.get(url_live, headers=HEADERS, timeout=15).json()
        return res_live.get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    for season in [2025, 2024, 2023]:
        try:
            res = requests.get(f"{BASE_URL}/standings?league={league_id}&season={season}", headers=HEADERS).json()
            if res.get('response'):
                return res['response'][0]['league']['standings'][0], season
        except: continue
    return None, None

def get_weather_multiplier(city):
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        if res.get('main'):
            cond = res['weather'][0]['main'].lower()
            mod = 0.85 if any(x in cond for x in ["rain", "snow", "storm"]) else 1.0
            return mod, f"{cond.upper()} ({res['main']['temp']}°C)"
    except: return 1.0, "WEATHER: NEUTRAL"

def run_neural_simulation(h_exp, a_exp, w_mod, sims=100000):
    h_sim = np.random.poisson(max(0.1, h_exp * w_mod), sims)
    a_sim = np.random.poisson(max(0.1, a_exp * w_mod), sims)
    totals = h_sim + a_sim
    results = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        prob = np.mean(totals > line) * 100
        fair = round(100/prob, 2) if prob > 0 else 99.0
        results[line] = {"prob": round(prob, 1), "fair": fair}
    return results

# --- 4. DASHBOARD TABS ---
st.title("🌍 GOALPREDICTOR OMNI-GLOBAL v150.0")
tab1, tab2, tab3, tab4 = st.tabs(["🧠 NEURAL SCANNER", "🔴 GLOBAL LIVE", "📊 STANDINGS", "🗺️ WORLD EXPLORER"])

with tab1:
    st.sidebar.header("🎯 System Control")
    LEAGUES = {
        "Allsvenskan (SWE)": 113, "Premier League (ENG)": 39, "La Liga (ESP)": 140, 
        "Serie A (ITA)": 135, "Bundesliga (GER)": 78, "Saudi Pro League (KSA)": 307,
        "Egypt Premier League (EGY)": 233, "J1 League (JPN)": 98
    }
    l_name = st.sidebar.selectbox("Välj Marknad", list(LEAGUES.keys()))
    
    standings, active_season = get_league_standings(LEAGUES[l_name])
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        col1, col2 = st.columns(2)
        h_team = col1.selectbox("Home Team", teams, index=0)
        a_team = col2.selectbox("Away Team", teams, index=1)
        m_odds = st.sidebar.number_input("Marknadsodds (Över 2.5)", value=2.00, step=0.01)
        
        if st.button("EXECUTE OMNI-SCAN"):
            h_stats = next(t for t in standings if t['team']['name'] == h_team)
            a_stats = next(t for t in standings if t['team']['name'] == a_team)
            w_mod, w_desc = get_weather_multiplier(h_team)
            
            h_exp = (h_stats['all']['goals']['for'] / (h_stats['all']['played'] or 1)) * 1.10
            a_exp = (a_stats['all']['goals']['for'] / (a_stats['all']['played'] or 1)) * 0.95
            
            probs = run_neural_simulation(h_exp, a_exp, w_mod)
            st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2><p>{w_desc}</p></div>", unsafe_allow_html=True)
            
            res_cols = st.columns(6)
            for i, line in enumerate(probs):
                res_cols[i].metric(f"Över {line}", f"{probs[line]['prob']}%")
    else:
        st.warning("Välj en liga för att starta analysen.")

with tab2:
    live_matches = get_deep_live_scan()
    if live_matches:
        for m in live_matches[:10]: # Visar de 10 första live-matcherna
            st.write(f"🔴 {m['teams']['home']['name']} {m['goals']['home']} - {m['goals']['away']} {m['teams']['away']['name']}")
    else:
        st.info("Inga live-matcher just nu.")

with tab4:
    st.subheader("🗺️ Global Explorer")
    search = st.text_input("Sök efter land (t.ex. Nigeria, Thailand)")
    leagues = get_global_leagues()
    if search and leagues:
        found = [l for l in leagues if search.lower() in l['strLeague'].lower()]
        st.write(found)

st.sidebar.button("REFRESH DATA", on_click=st.cache_data.clear)
