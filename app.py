import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. KONFIGURATION & STYLING ---
st.set_page_config(page_title="GoalPredictor v11.8 WEATHER-HUNTER", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; width: 100%; border: none; height: 2.5em; }
    .match-card { background-color: #161b22; padding: 15px; border-radius: 10px; border-left: 5px solid #30363d; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" # <--- Valfri för exakt väder
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. DATA ENGINES ---

def get_weather_data(city):
    """Hämtar väder och returnerar en xG-modifikator"""
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL":
        return {"temp": 12, "wind": 4, "cond": "Molnigt", "mod": 1.0}
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        r = requests.get(url, timeout=3).json()
        wind = r['wind']['speed']
        # Logik: Vind över 8 m/s sänker xG med 12%
        mod = 0.88 if wind > 8 else 1.0
        return {"temp": r['main']['temp'], "wind": wind, "cond": r['weather'][0]['description'], "mod": mod}
    except:
        return {"temp": 15, "wind": 2, "cond": "Normalt", "mod": 1.0}

@st.cache_data(ttl=3600)
def get_standings_safe(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season=2024", headers=HEADERS).json()
        return res['response'][0]['league']['standings'][0]
    except: return []

def run_fusion_sim(h_st, a_st, w_mod=1.0):
    h_avg = h_st['all']['goals']['for'] / h_st['all']['played']
    a_def = a_st['all']['goals']['against'] / a_st['all']['played']
    a_avg = a_st['all']['goals']['for'] / a_st['all']['played']
    h_def = h_st['all']['goals']['against'] / h_st['all']['played']
    
    h_xg = (h_avg * (a_def / 1.2)) * 1.18 * w_mod
    a_xg = (a_avg * (h_def / 1.2)) * w_mod
    
    sims = 100000
    h_sim = np.random.poisson(max(0.1, h_xg), sims)
    a_sim = np.random.poisson(max(0.1, a_xg), sims)
    return {"o25": np.mean((h_sim + a_sim) > 2.5) * 100, "h_p": np.mean(h_sim > a_sim) * 100, "d_p": np.mean(h_sim == a_sim) * 100, "a_p": np.mean(h_sim < a_sim) * 100}

# --- 3. HUVUD-APP ---

with st.sidebar:
    st.header("⚙️ Inställningar")
    bankroll = st.number_input("Din Kassa (kr)", value=10000)
    odds_o25 = st.number_input("Marknadsodds (Ö2.5)", value=1.95)
    league_name = st.selectbox("Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

st.title("🛡️ GoalPredictor v11.8 Weather-Hunter")

standings = get_standings_safe(curr_league)
if standings:
    st.subheader(f"📅 Kommande matcher i {league_name}")
    fixtures = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": curr_league, "season": 2024, "next": 8}).json().get('response', [])
    
    for f in fixtures:
        h_n, a_n = f['teams']['home']['name'], f['teams']['away']['name']
        city = f['fixture']['venue']['city'] if f['fixture']['venue']['city'] else h_n
        
        # Hämta väder direkt för matchkortet
        w = get_weather_data(city)
        w_icon = "🚩" if w['wind'] > 8 else "🌤️"
        
        # Design av Match-kort
        with st.container():
            col_info, col_weather, col_btn = st.columns([3, 2, 1])
            
            with col_info:
                st.markdown(f"**{h_n}** vs **{a_n}**")
                st.caption(f"Stad: {city} | Datum: {f['fixture']['date'][:10]}")
            
            with col_weather:
                st.markdown(f"{w_icon} {w['temp']}°C | Vind: {w['wind']} m/s")
                if w['mod'] < 1.0: st.caption("⚠️ Vind påverkar xG negativt")
            
            # Klicka för att köra analys
            if col_btn.button("ANALYS", key=f"btn_{f['fixture']['id']}"):
                h_st = next(t for t in standings if t['team']['name'] == h_n)
                a_st = next(t for t in standings if t['team']['name'] == a_n)
                res = run_fusion_sim(h_st, a_st, w_mod=w['mod'])
                
                st.session_state.last_res = {
                    "match": f"{h_n} - {a_n}", "o25": res['o25'], 
                    "1": res['h_p'], "X": res['d_p'], "2": res['a_p'], "w_mod": w['mod']
                }

    # Visa resultatet av klickad analys längst ner
    if 'last_res' in st.session_state:
        r = st.session_state.last_res
        st.divider()
        st.markdown(f"### 📊 Deep Scan: {r['match']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sannolikhet Ö2.5", f"{round(r['o25'], 1)}%")
        
        edge = (r['o25']/100 * odds_o25) - 1
        c2.metric("Edge mot marknad", f"{round(edge*100, 1)}%")
        
        stake = int(bankroll * (edge/(odds_o25-1)) * 0.2) if edge > 0 else 0
        c3.metric("Rek. Insats", f"{stake} kr")
        
        st.bar_chart(pd.DataFrame({'%': [r['1'], r['X'], r['2']]}, index=['1','X','2']))
