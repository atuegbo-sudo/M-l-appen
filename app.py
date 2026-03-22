import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. CONFIG & PRO STYLING ---
st.set_page_config(page_title="GoalPredictor v15.5 ARBITRAGE", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 20px; border-radius: 12px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; width: 100%; border: none; height: 3.5em; border-radius: 8px; }
    .best-bet-box { background-color: #161b22; padding: 25px; border-radius: 15px; border: 2px solid #00ff41; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
SEASON = 2025 

# --- 2. THE ARBITRAGE & NEURAL ENGINE ---

@st.cache_data(ttl=60)
def get_live_data(league_id):
    try:
        return requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "live": "all"}).json().get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_standings_safe(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season={SEASON}", headers=HEADERS).json()
        if 'response' in res and len(res['response']) > 0:
            data = res['response']['league']['standings']
            return data if isinstance(data, list) else data
        return []
    except: return []

def run_quantum_analysis(h_st, a_st, h2h_mod=1.0, w_mod=1.0):
    """Bivariat DxG Simulation"""
    h_xg = (h_st['all']['goals']['for']/h_st['all']['played']) * (a_st['all']['goals']['against']/a_st['all']['played']/1.2) * 1.15 * w_mod * h2h_mod
    a_xg = (a_st['all']['goals']['for']/a_st['all']['played']) * (h_st['all']['goals']['against']/h_st['all']['played']/1.2) * w_mod * h2h_mod
    sims = 150000
    h_s, a_s = np.random.poisson(max(0.1, h_xg), sims), np.random.poisson(max(0.1, a_xg), sims)
    prob_o25 = np.mean((h_s + a_s) > 2.5) * 100
    return {"o25": prob_o25, "u25": 100 - prob_o25, "h_p": np.mean(h_s > a_s)*100, "d_p": np.mean(h_s == a_s)*100, "a_p": np.mean(h_s < a_s)*100}

# --- 3. DASHBOARD UI ---

with st.sidebar:
    st.header("🎯 System Control")
    bankroll = st.number_input("Din Kassa (kr)", value=10000)
    odds_o25 = st.number_input("Odds Över 2.5", value=1.95)
    odds_u25 = st.number_input("Odds Under 2.5", value=1.95)
    st.divider()
    league_name = st.selectbox("Market League", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

tab1, tab2, tab3 = st.tabs(["🚀 ARBITRAGE HUNTER", "🔴 LIVE CENTER", "🧠 NEURAL SCAN"])

standings = get_standings_safe(curr_league)

# --- TAB 1: ARBITRAGE ENGINE (BÄSTA SPEL) ---
with tab1:
    st.subheader(f"Skannar {league_name} efter högsta väntevärde...")
    if standings:
        fixtures = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": curr_league, "season": SEASON, "next": 15}).json().get('response', [])
        
        results = []
        for f in fixtures:
            h_n, a_n = f['teams']['home']['name'], f['teams']['away']['name']
            h_st = next((t for t in standings if t['team']['name'] == h_n), None)
            a_st = next((t for t in standings if t['team']['name'] == a_n), None)
            
            if h_st and a_st:
                analysis = run_quantum_analysis(h_st, a_st)
                # Räkna ut Edge för båda marknaderna
                edge_o = ((analysis['o25']/100) * odds_o25) - 1
                edge_u = ((analysis['u25']/100) * odds_u25) - 1
                
                # Välj det med högst edge
                best_edge = max(edge_o, edge_u)
                bet_type = "Över 2.5" if edge_o > edge_u else "Under 2.5"
                prob = analysis['o25'] if edge_o > edge_u else analysis['u25']
                current_odds = odds_o25 if edge_o > edge_u else odds_u25
                
                results.append({"Match": f"{h_n}-{a_n}", "Spel": bet_type, "Sannolikhet": f"{round(prob,1)}%", "Edge": round(best_edge*100, 1), "Odds": current_odds})
        
        if results:
            sorted_res = sorted(results, key=lambda x: x['Edge'], reverse=True)
            best = sorted_res[0]
            
            # --- HIGHLIGHT: BÄSTA MATCH ---
            st.markdown(f"<div class='best-bet-box'><h3>🏆 REKOMMENDERAT TOPPVAL: {best['Match']}</h3>"
                        f"<p>Marknad: <b>{best['Spel']}</b> | Beräknad Edge: <b>{best['Edge']}%</b></p></div>", unsafe_allow_html=True)
            
            k_stake = int(bankroll * ((best['Edge']/100)/(best['Odds']-1)) * 0.25)
            st.metric("Rekommenderad Kelly-insats", f"{max(0, k_stake)} kr")
            st.table(pd.DataFrame(sorted_res))

# --- TAB 2: LIVE CENTER ---
with tab1: # (Använder tab1 för live enligt din tidigare layout)
    st.divider()
    st.subheader("⏱️ Live Scoreboard")
    live = get_live_data(curr_league)
    if live:
        for m in live: st.write(f"**{m['teams']['home']['name']} {m['goals']['home']}-{m['goals']['away']} {m['teams']['away']['name']}** ({m['fixture']['status']['elapsed']}')")
    else: st.info("Inga live-matcher just nu.")

# --- TAB 3: NEURAL SCAN (MANUELL) ---
with tab3:
    if standings:
        t_list = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_sel = c1.selectbox("Hemmalag", t_list, index=0)
        a_sel = c2.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)
        
        if st.button("KÖR DJUP SCAN"):
            h_st = next(t for t in standings if t['team']['name'] == h_sel)
            a_st = next(t for t in standings if t['team']['name'] == a_sel)
            res = run_quantum_analysis(h_st, a_st)
            st.divider()
            st.metric("Sannolikhet Över 2.5", f"{round(res['o25'],1)}%")
            st.bar_chart(pd.DataFrame({'%': [res['h_p'], res['d_p'], res['a_p']]}, index=['1','X','2']))
