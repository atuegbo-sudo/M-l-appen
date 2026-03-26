import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. PRO-TERMINAL STYLING ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-WEATHER", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; border-radius: 5px; }
    .stButton>button { background: #00ff41; color: black; font-weight: 900; width: 100%; height: 3.5em; border: none; transition: 0.3s; }
    .stButton>button:hover { background: #ffffff; box-shadow: 0 0 30px #00ff41; }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; text-align: center; margin-bottom: 25px; }
    h2, h3 { color: #00ff41 !important; letter-spacing: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG ---
# TheSportsDB använder testnyckel "3" (Offentlig)
SPORTSDB_KEY = "3"
BASE_URL = f"https://www.thesportsdb.com{SPORTSDB_KEY}"

# Väder-API (Hämtas säkert från Streamlit Secrets på GitHub)
try:
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
except:
    WEATHER_API_KEY = None # Fallback om nyckel saknas

# --- 3. DATA ENGINES ---

@st.cache_data(ttl=3600)
def get_all_leagues():
    url = f"{BASE_URL}/all_leagues.php"
    try:
        res = requests.get(url).json()
        return [l for l in res.get('leagues', []) if l['strSport'] == 'Soccer']
    except: return []

@st.cache_data(ttl=3600)
def get_teams(league_name):
    url = f"{BASE_URL}/search_all_teams.php?l={league_name.replace(' ', '%20')}"
    try:
        res = requests.get(url).json()
        return res.get('teams', [])
    except: return []

def get_weather_impact(city):
    """Hämtar väderdata och beräknar en multiplikator för målprognosen"""
    if not WEATHER_API_KEY or not city:
        return 1.0, "WEATHER: DATA UNAVAILABLE"
    
    try:
        w_url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(w_url, timeout=5).json()
        if res.get('main'):
            temp = res['main']['temp']
            cond = res['weather'][0]['main'].lower()
            # Minskar förväntade mål vid regn/oväder (Debuff)
            mod = 0.88 if any(x in cond for x in ["rain", "snow", "storm"]) else 1.0
            return mod, f"{cond.upper()} | {temp}°C"
    except: pass
    return 1.0, "WEATHER: NEUTRAL"

def run_neural_simulation(h_exp, a_exp, w_mod, sims=100000):
    """Neural simulation baserat på väderjusterad xG"""
    h_sim = np.random.poisson(max(0.1, h_exp * w_mod), sims)
    a_sim = np.random.poisson(max(0.1, a_exp * w_mod), sims)
    totals = h_sim + a_sim
    results = {line: round(np.mean(totals > line) * 100, 1) for line in [0.5, 1.5, 2.5, 3.5]}
    return results

# --- 4. INTERFACE ---
st.title("🌍 GOALPREDICTOR OMNI (WEATHER + SPORTS-DB)")

tab1, tab2 = st.tabs(["🧠 NEURAL SCANNER", "🗺️ WORLD EXPLORER"])

with tab1:
    leagues = get_all_leagues()
    if leagues:
        l_names = [l['strLeague'] for l in leagues]
        sel_league = st.sidebar.selectbox("Välj Liga", l_names)
        
        teams = get_teams(sel_league)
        if teams:
            t_names = [t['strTeam'] for t in teams]
            col1, col2 = st.columns(2)
            h_team = col1.selectbox("Home Team", t_names, index=0)
            a_team = col2.selectbox("Away Team", t_names, index=min(1, len(t_names)-1))
            
            # Hitta stad för väderkoll
            h_team_data = next(t for t in teams if t['strTeam'] == h_team)
            city = h_team_data.get('strLocation', '')

            if st.button("EXECUTE OMNI-SCAN"):
                w_mod, w_desc = get_weather_impact(city)
                
                # Grund-xG (Hemmafördel inräknat)
                h_exp, a_exp = 1.7, 1.3 
                probs = run_neural_simulation(h_exp, a_exp, w_mod)
                
                st.markdown(f"""
                <div class='neural-box'>
                    <h2>{h_team} vs {a_team}</h2>
                    <p style='color: #fff;'>{sel_league} | {city.upper()}</p>
                    <h3 style='color: #ff00ff;'>{w_desc}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                res_cols = st.columns(4)
                for i, line in enumerate(probs):
                    res_cols[i].metric(f"Över {line}", f"{probs[line]}%")
        else:
            st.info("Inga lag hittades i denna liga.")

with tab2:
    st.subheader("🗺️ Global Search")
    q = st.text_input("Sök land (t.ex. 'Saudi Arabia', 'Egypt', 'Sweden')")
    if leagues:
        filtered = [l for l in leagues if q.lower() in l['strLeague'].lower() or q.lower() in (l.get('strCountry') or "").lower()]
        st.table(pd.DataFrame(filtered)[['strLeague', 'strCountry']].head(15))

st.sidebar.caption("v150.0 | Engine: TheSportsDB + OpenWeather")
if st.sidebar.button("REFRESH"):
    st.cache_data.clear()
    st.rerun()
