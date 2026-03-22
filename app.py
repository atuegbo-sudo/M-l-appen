import streamlit as st
import requests
import pandas as pd
import numpy as np
import math

# --- 1. KONFIGURATION & STYLING ---
st.set_page_config(page_title="GoalPredictor v10.9 SOLID FUSION", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; width: 100%; border: none; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. DATA ENGINES (SÄKRA) ---

@st.cache_data(ttl=60)
def get_live_scores(league_id):
    try:
        res = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "live": "all"}).json()
        return res.get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_full_api_res(endpoint, params=None):
    try:
        return requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params).json()
    except: return {}

def get_live_weather(city):
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL":
        return {"temp": 12, "wind": 4, "cond": "Molnigt", "mod": 1.0}
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        r = requests.get(url, timeout=5).json()
        mod = 0.90 if r['wind']['speed'] > 8 else 1.0
        return {"temp": r['main']['temp'], "wind": r['wind']['speed'], "cond": r['weather'][0]['description'], "mod": mod}
    except: return {"temp": 15, "wind": 2, "cond": "Normalt", "mod": 1.0}

def run_fusion_sim(h_stats, a_stats, h2h_mod=1.0, w_mod=1.0):
    try:
        h_played = h_stats['all']['played']
        a_played = a_stats['all']['played']
        if h_played == 0 or a_played == 0: return None
        
        h_avg = h_stats['all']['goals']['for'] / h_played
        a_def = a_stats['all']['goals']['against'] / a_played
        a_avg = a_stats['all']['goals']['for'] / a_played
        h_def = h_stats['all']['goals']['against'] / h_played
        
        h_xg = (h_avg * (a_def / 1.2)) * 1.18 * w_mod * h2h_mod
        a_xg = (a_avg * (h_def / 1.2)) * w_mod * h2h_mod
        
        sims = 100000
        h_sim = np.random.poisson(max(0.1, h_xg), sims)
        a_sim = np.random.poisson(max(0.1, a_xg), sims)
        total_g = h_sim + a_sim
        
        return {
            "o25": np.mean(total_g > 2.5) * 100,
            "u25": np.mean(total_g < 2.5) * 100,
            "btts": np.mean((h_sim > 0) & (a_sim > 0)) * 100,
            "h_p": np.mean(h_sim > a_sim) * 100, "d_p": np.mean(h_sim == a_sim) * 100, "a_p": np.mean(h_sim < a_sim) * 100,
            "h_dist": [np.mean(h_sim == i) * 100 for i in range(6)], "a_dist": [np.mean(a_sim == i) * 100 for i in range(6)]
        }
    except: return None

# --- 3. DASHBOARD UI ---

with st.sidebar:
    st.header("⚙️ Kontroll")
    bankroll = st.number_input("Kassa (kr)", value=10000)
    odds_o25 = st.number_input("Odds Över 2.5", value=1.95)
    odds_u25 = st.number_input("Odds Under 2.5", value=1.95)
    min_edge = st.slider("Minsta Edge (%)", 1.0, 15.0, 5.0)
    league_name = st.selectbox("Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

# 1. LIVE SCORES
live_matches = get_live_scores(curr_league)
if live_matches:
    st.subheader("⏱️ Live Just Nu")
    for m in live_matches:
        cols = st.columns(4)
        cols.write(m['teams']['home']['name'])
        cols.write(f"**{m['goals']['home']} - {m['goals']['away']}**")
        cols.write(m['teams']['away']['name'])
        cols.write(f"⚽ {m['fixture']['status']['elapsed']}'")
    st.divider()

# 2. STANDINGS & VALUE HUNTER (FIXAD TYPERROR)
st.subheader(f"🔥 Spelvärde i {league_name}")
full_res = get_full_api_res("standings", {"league": curr_league, "season": 2024})

standings = []
if full_res.get('response'):
    # Extrahera tabellen säkert
    try:
        data = full_res['response'][0]['league']['standings']
        standings = data[0] if isinstance(data[0], list) else data
    except (KeyError, IndexError):
        st.error("Kunde inte tolka tabellformatet.")

if standings:
    t_list = sorted([t['team']['name'] for t in standings])
    t_map = {t['team']['name']: t['team']['id'] for t in standings}
    
    # Kör Value Hunter
    fixtures = get_full_api_res("fixtures", {"league": curr_league, "season": 2024, "next": 10}).get('response', [])
    val_bets = []
    for f in fixtures:
        h_st = next((t for t in standings if t['team']['name'] == f['teams']['home']['name']), None)
        a_st = next((t for t in standings if t['team']['name'] == f['teams']['away']['name']), None)
        if h_st and a_st:
            res = run_fusion_sim(h_st, a_st)
            if res:
                e_o = ((res['o25']/100)*odds_o25)-1
                e_u = ((res['u25']/100)*odds_u25)-1
                best_e = max(e_o, e_u)
                if (best_e*100) >= min_edge:
                    typ = "Över 2.5" if e_o > e_u else "Under 2.5"
                    o = odds_o25 if e_o > e_u else odds_u25
                    stake = int(bankroll * (best_e/(o-1)) * 0.2)
                    val_bets.append({"Match": f"{h_st['team']['name']}-{a_st['team']['name']}", "Spel": typ, "Edge": f"{round(best_e*100,1)}%", "Insats": f"{stake} kr"})
    
    if val_bets: st.table(pd.DataFrame(val_bets))
    else: st.info("Inga värdespel hittades just nu.")

    # 3. MANUELL ANALYS
    st.divider()
    st.subheader("🔍 Djupanalys")
    c1, c2 = st.columns(2)
    with c1:
        h_sel = st.selectbox("Hemmalag", t_list, index=0)
        w = get_live_weather(h_sel)
        st.info(f"🌡️ Väder: {w['temp']}°C, {w['cond']}")
    with c2:
        a_sel = st.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)

    if st.button("KÖR ANALYS"):
        h_st = next(t for t in standings if t['team']['name'] == h_sel)
        a_st = next(t for t in standings if t['team']['name'] == a_sel)
        final = run_fusion_sim(h_st, a_st, w_mod=w['mod'])
        if final:
            r1, r2, r3 = st.columns(3)
            r1.metric("Över 2.5%", f"{round(final['o25'],1)}%")
            r2.metric("Under 2.5%", f"{round(final['u25'],1)}%")
            r3.metric("BTTS%", f"{round(final['btts'],1)}%")
            st.bar_chart(pd.DataFrame({'Resultat': ['Hemma', 'Oavgjort', 'Borta'], 'Chans': [final['h_p'], final['d_p'], final['a_p']]}).set_index('Resultat'))
else:
    st.warning("Väntar på data från API...")
