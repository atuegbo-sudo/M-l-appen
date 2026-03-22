import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. KONFIGURATION & STYLING ---
st.set_page_config(page_title="GoalPredictor v11.9 SOVEREIGN", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; width: 100%; border: none; height: 3em; }
    .match-card { background-color: #161b22; padding: 15px; border-radius: 10px; border-left: 5px solid #30363d; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" # Valfri
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. DATA ENGINES (SÄKRA & DYNAMISKA) ---

@st.cache_data(ttl=60)
def get_live_and_today(league_id):
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        live = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "live": "all"}).json().get('response', [])
        todays = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "date": today}).json().get('response', [])
        return live, todays
    except: return [], []

@st.cache_data(ttl=3600)
def get_standings_safe(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season=2024", headers=HEADERS).json()
        if 'response' in res and len(res['response']) > 0:
            data = res['response']['league']['standings']
            return data if isinstance(data, list) else data
        return []
    except: return []

def get_weather_impact(city):
    if WEATHER_API_KEY == "7bd889f1cb9cec6e42e15fc106125abe":
        return {"temp": 12, "wind": 4, "cond": "Molnigt", "mod": 1.0}
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        r = requests.get(url, timeout=3).json()
        mod = 0.88 if r['wind']['speed'] > 8 else 1.0
        return {"temp": r['main']['temp'], "wind": r['wind']['speed'], "cond": r['weather'][0]['description'], "mod": mod}
    except: return {"temp": 15, "wind": 2, "cond": "Normalt", "mod": 1.0}

def run_quantum_sim(h_st, a_st, w_mod=1.0):
    h_avg = h_st['all']['goals']['for'] / h_st['all']['played']
    a_def = a_st['all']['goals']['against'] / a_st['all']['played']
    a_avg = a_st['all']['goals']['for'] / a_st['all']['played']
    h_def = h_st['all']['goals']['against'] / h_st['all']['played']
    h_xg = (h_avg * (a_def / 1.2)) * 1.18 * w_mod
    a_xg = (a_avg * (h_def / 1.2)) * w_mod
    sims = 100000
    h_s = np.random.poisson(max(0.1, h_xg), sims)
    a_s = np.random.poisson(max(0.1, a_xg), sims)
    return {
        "o25": np.mean((h_s + a_s) > 2.5) * 100, "btts": np.mean((h_s > 0) & (a_s > 0)) * 100,
        "h_p": np.mean(h_s > a_s) * 100, "d_p": np.mean(h_s == a_s) * 100, "a_p": np.mean(h_s < a_s) * 100
    }

# --- 3. HUVUD-APP ---

with st.sidebar:
    st.header("⚙️ Inställningar")
    bankroll = st.number_input("Din Kassa (kr)", value=10000)
    odds_o25 = st.number_input("Marknadsodds (Ö2.5)", value=1.95)
    league_name = st.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

tab1, tab2 = st.tabs(["🔴 LIVE & MATCH-VÄLJARE", "🧠 MANUELL ANALYS"])

# Hämtning av data
live_data, today_data = get_live_and_today(curr_league)
standings = get_standings_safe(curr_league)

with tab1:
    # 1. Live Scoreboard
    if live_data:
        st.subheader("⏱️ Live Just Nu")
        for m in live_data:
            st.success(f"**{m['teams']['home']['name']} {m['goals']['home']} - {m['goals']['away']} {m['teams']['away']['name']}** ({m['fixture']['status']['elapsed']}')")
        st.divider()

    # 2. Match-väljare (Klickbara kort)
    if standings:
        st.subheader("📅 Kommande Matchalternativ")
        fixtures = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": curr_league, "season": 2024, "next": 8}).json().get('response', [])
        
        for f in fixtures:
            h_n, a_n = f['teams']['home']['name'], f['teams']['away']['name']
            city = f['fixture']['venue']['city'] if f['fixture']['venue']['city'] else h_n
            w = get_weather_impact(city)
            
            with st.container():
                c_info, c_weather, c_btn = st.columns([2, 1, 1])
                c_info.markdown(f"**{h_n}** vs **{a_n}**\n\n*{f['fixture']['date'][:16]}*")
                c_weather.markdown(f"{'🚩' if w['wind']>8 else '🌤️'} {w['temp']}°C\nVind: {w['wind']} m/s")
                
                if c_btn.button("ANALYS", key=f"btn_{f['fixture']['id']}"):
                    h_st = next(t for t in standings if t['team']['name'] == h_n)
                    a_st = next(t for t in standings if t['team']['name'] == a_n)
                    res = run_quantum_sim(h_st, a_st, w_mod=w['mod'])
                    
                    st.session_state.current_scan = {
                        "match": f"{h_n}-{a_n}", "o25": res['o25'], "btts": res['btts'],
                        "1X2": [res['h_p'], res['d_p'], res['a_p']], "w_info": w
                    }

        # Visa klickat resultat
        if 'current_scan' in st.session_state:
            s = st.session_state.current_scan
            st.divider()
            st.markdown(f"### 📊 Scan Resultat: {s['match']}")
            res_c1, res_c2, res_c3 = st.columns(3)
            res_c1.metric("Över 2.5%", f"{round(s['o25'], 1)}%")
            res_c2.metric("BTTS%", f"{round(s['btts'], 1)}%")
            
            edge = (s['o25']/100 * odds_o25) - 1
            stake = int(bankroll * (edge/(odds_o25-1)) * 0.2) if edge > 0 else 0
            res_c3.metric("Rek. Insats", f"{stake} kr", f"Edge: {round(edge*100, 1)}%")
            st.bar_chart(pd.DataFrame({'%': s['1X2']}, index=['1','X','2']))

with tab2:
    if standings:
        t_list = sorted([t['team']['name'] for t in standings])
        st.subheader("Manuell Djupdykning")
        sc1, sc2 = st.columns(2)
        h_man = sc1.selectbox("Hemmalag", t_list, index=0)
        a_man = sc2.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)
        
        if st.button("KÖR MANUELL ANALYS"):
            h_st = next(t for t in standings if t['team']['name'] == h_man)
            a_st = next(t for t in standings if t['team']['name'] == a_man)
            m_res = run_quantum_sim(h_st, a_st)
            st.metric("Sannolikhet Över 2.5", f"{round(m_res['o25'], 1)}%")
