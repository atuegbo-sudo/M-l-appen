import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. KONFIGURATION & STYLING ---
st.set_page_config(page_title="GoalPredictor v11.6 ULTIMATE", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; width: 100%; border: none; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "DIN_OPENWEATHER_NYCKEL" # Valfri för live-väder
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. SÄKRA DATA-FUNKTIONER ---

@st.cache_data(ttl=60)
def get_live_data(league_id):
    try:
        res = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "live": "all"}).json()
        return res.get('response', [])
    except: return []

@st.cache_data(ttl=300)
def get_todays_results(league_id):
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        res = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "date": today}).json()
        return res.get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_standings_safe(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season=2024", headers=HEADERS).json()
        if 'response' in res and len(res['response']) > 0:
            # Universal parser för olika ligastrukturer
            data = res['response'][0]['league']['standings']
            return data[0] if isinstance(data[0], list) else data
        return []
    except: return []

def get_live_weather(city):
    if WEATHER_API_KEY == "7bd889f1cb9cec6e42e15fc106125abe":
        return {"temp": 12, "wind": 4, "cond": "Molnigt", "mod": 1.0}
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        r = requests.get(url, timeout=5).json()
        mod = 0.90 if r['wind']['speed'] > 8 else 1.0
        return {"temp": r['main']['temp'], "wind": r['wind']['speed'], "cond": r['weather'][0]['description'], "mod": mod}
    except: return {"temp": 15, "wind": 2, "cond": "Normalt", "mod": 1.0}

# --- 3. NEURAL SIMULATION ENGINE ---

def run_fusion_sim(h_st, a_st, h2h_mod=1.0, w_mod=1.0):
    try:
        h_avg = h_st['all']['goals']['for'] / h_st['all']['played']
        a_def = a_st['all']['goals']['against'] / a_st['all']['played']
        a_avg = a_st['all']['goals']['for'] / a_st['all']['played']
        h_def = h_st['all']['goals']['against'] / h_st['all']['played']
        
        # xG-modell med justeringar
        h_xg = (h_avg * (a_def / 1.2)) * 1.18 * w_mod * h2h_mod
        a_xg = (a_avg * (h_def / 1.2)) * w_mod * h2h_mod
        
        sims = 150000
        h_sim = np.random.poisson(max(0.1, h_xg), sims)
        a_sim = np.random.poisson(max(0.1, a_xg), sims)
        total_g = h_sim + a_sim
        
        return {
            "o25": np.mean(total_g > 2.5) * 100, "u25": np.mean(total_g < 2.5) * 100,
            "btts": np.mean((h_sim > 0) & (a_sim > 0)) * 100,
            "h_p": np.mean(h_sim > a_sim) * 100, "d_p": np.mean(h_sim == a_sim) * 100, "a_p": np.mean(h_sim < a_sim) * 100,
            "h_dist": [np.mean(h_sim == i) * 100 for i in range(6)], "a_dist": [np.mean(a_sim == i) * 100 for i in range(6)]
        }
    except: return None

# --- 4. HUVUD-APP ---

with st.sidebar:
    st.header("⚙️ Kontrollpanel")
    bankroll = st.number_input("Din Kassa (kr)", value=10000)
    odds_o25 = st.number_input("Odds Över 2.5", value=1.95)
    odds_u25 = st.number_input("Odds Under 2.5", value=1.95)
    min_edge = st.slider("Minsta Edge (%)", 1.0, 15.0, 5.0)
    league_name = st.selectbox("Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

tab1, tab2, tab3 = st.tabs(["🔴 LIVE & RESULTAT", "📅 VALUE HUNTER", "🧠 DJUPANALYS"])

# TAB 1: LIVE
with tab1:
    st.subheader("⏱️ Pågående & Avslutade matcher idag")
    live = get_live_data(curr_league)
    todays = get_todays_results(curr_league)
    
    if live:
        for m in live:
            st.success(f"LIVE: {m['teams']['home']['name']} {m['goals']['home']} - {m['goals']['away']} {m['teams']['away']['name']} ({m['fixture']['status']['elapsed']}')")
    
    finished = [m for m in todays if m['fixture']['status']['short'] == "FT"]
    if finished:
        for m in finished:
            st.write(f"SLUT: {m['teams']['home']['name']} **{m['goals']['home']} - {m['goals']['away']}** {m['teams']['away']['name']}")
    elif not live:
        st.info("Inga matcher i denna liga just nu.")

# TAB 2: VALUE HUNTER
with tab2:
    standings = get_standings_safe(curr_league)
    if standings:
        st.subheader("🔥 Bästa Spelvärde (Kommande)")
        fixtures = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": curr_league, "season": 2024, "next": 10}).json().get('response', [])
        val_list = []
        for f in fixtures:
            h_st = next((t for t in standings if t['team']['name'] == f['teams']['home']['name']), None)
            a_st = next((t for t in standings if t['team']['name'] == f['teams']['away']['name']), None)
            if h_st and a_st:
                res = run_fusion_sim(h_st, a_st)
                e_o = ((res['o25']/100)*odds_o25)-1
                e_u = ((res['u25']/100)*odds_u25)-1
                best_e = max(e_o, e_u)
                if (best_e*100) >= min_edge:
                    typ = "Över 2.5" if e_o > e_u else "Under 2.5"
                    o = odds_o25 if e_o > e_u else odds_u25
                    stake = int(bankroll * (best_e/(o-1)) * 0.2)
                    val_list.append({"Match": f"{h_st['team']['name']}-{a_st['team']['name']}", "Spel": typ, "Edge": f"{round(best_e*100,1)}%", "Insats": f"{stake} kr"})
        if val_list: st.table(pd.DataFrame(val_list))
        else: st.info("Inga stora värden hittades just nu.")

# TAB 3: ANALYS
with tab3:
    if standings:
        t_list = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        with c1:
            h_sel = st.selectbox("Hemmalag", t_list, index=0)
            w = get_live_weather(h_sel)
            st.info(f"🌡️ Väder: {w['temp']}°C, {w['cond']}")
        with c2:
            a_sel = st.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)
        
        if st.button("STARTA ANALYS"):
            h_st = next(t for t in standings if t['team']['name'] == h_sel)
            a_st = next(t for t in standings if t['team']['name'] == a_sel)
            final = run_fusion_sim(h_st, a_st, w_mod=w['mod'])
            if final:
                r1, r2, r3 = st.columns(3)
                r1.metric("Över 2.5%", f"{round(final['o25'],1)}%")
                r2.metric("Under 2.5%", f"{round(final['u25'],1)}%")
                r3.metric("BTTS%", f"{round(final['btts'],1)}%")
                st.bar_chart(pd.DataFrame({'%': [final['h_p'], final['d_p'], final['a_p']]}, index=['1','X','2']))
