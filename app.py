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
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" # <--- DIN NYCKEL HÄR
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
SEASON = 2025 

# --- 2. THE ARBITRAGE & NEURAL ENGINE ---

@st.cache_data(ttl=60)
def get_live_data(league_id):
    try:
        res = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "live": "all"}).json()
        return res.get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_standings_safe(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season=2024", headers=HEADERS).json()
        if 'response' in res and len(res['response']) > 0:
            # API-Football returnerar ibland listor i listor för standings
            data = res['response'][0]['league']['standings'][0]
            return data
        return []
    except Exception as e:
        return []

def get_weather_mod(city):
    """Hämtar väderjustering baserat på vind och temp"""
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        w = requests.get(url, timeout=3).json()
        temp, wind = w['main']['temp'], w['wind']['speed']
        mod = 1.0
        if wind > 8: mod *= 0.93 # Sänker mål vid hård vind
        if temp > 28: mod *= 1.07 # Höjer mål vid extrem värme (trötta försvar)
        return mod, f"{temp}°C, {wind}m/s"
    except: return 1.0, "Väderdata ej tillgänglig"

def run_quantum_analysis(h_st, a_st, h2h_mod=1.0, w_mod=1.0):
    """Bivariat DxG Simulation - 150 000 iterationer"""
    # Beräknar xG baserat på anfall vs försvarstyrka
    h_xg = (h_st['all']['goals']['for']/h_st['all']['played']) * (a_st['all']['goals']['against']/a_st['all']['played']/1.2) * 1.15 * w_mod * h2h_mod
    a_xg = (a_st['all']['goals']['for']/a_st['all']['played']) * (h_st['all']['goals']['against']/h_st['all']['played']/1.2) * w_mod * h2h_mod
    
    sims = 150000
    h_s = np.random.poisson(max(0.1, h_xg), sims)
    a_s = np.random.poisson(max(0.1, a_xg), sims)
    
    prob_o25 = np.mean((h_s + a_s) > 2.5) * 100
    return {
        "o25": prob_o25, 
        "u25": 100 - prob_o25, 
        "h_p": np.mean(h_s > a_s)*100, 
        "d_p": np.mean(h_s == a_s)*100, 
        "a_p": np.mean(h_s < a_s)*100,
        "exp_goals": h_xg + a_xg
    }

# --- 3. DASHBOARD UI ---

with st.sidebar:
    st.header("🎯 System Control")
    bankroll = st.number_input("Din Kassa (kr)", value=10000)
    odds_o25 = st.number_input("Odds Över 2.5", value=1.95, step=0.01)
    odds_u25 = st.number_input("Odds Under 2.5", value=1.95, step=0.01)
    st.divider()
    league_name = st.selectbox("Market League", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]
    if st.button("🔄 Force Refresh Cache"):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3 = st.tabs(["🚀 ARBITRAGE HUNTER", "🔴 LIVE CENTER", "🧠 NEURAL SCAN"])

standings = get_standings_safe(curr_league)

# --- TAB 1: ARBITRAGE ENGINE ---
with tab1:
    if not standings:
        st.warning("⚠️ Kunde inte hämta tabellen. Kontrollera API-nyckel eller att säsongen har börjat.")
    else:
        st.subheader(f"Skannar {league_name} efter högsta väntevärde...")
        # Hämtar nästa 15 matcher
        fixtures = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": curr_league, "season": 2024, "next": 15}).json().get('response', [])
        
        results = []
        for f in fixtures:
            h_n, a_n = f['teams']['home']['name'], f['teams']['away']['name']
            h_st = next((t for t in standings if t['team']['name'] == h_n), None)
            a_st = next((t for t in standings if t['team']['name'] == a_n), None)
            
            if h_st and a_st:
                analysis = run_quantum_analysis(h_st, a_st)
                edge_o = ((analysis['o25']/100) * odds_o25) - 1
                edge_u = ((analysis['u25']/100) * odds_u25) - 1
                
                best_edge = max(edge_o, edge_u)
                bet_type = "Över 2.5" if edge_o > edge_u else "Under 2.5"
                prob = analysis['o25'] if edge_o > edge_u else analysis['u25']
                current_odds = odds_o25 if edge_o > edge_u else odds_u25
                
                results.append({"Match": f"{h_n} - {a_n}", "Spel": bet_type, "Sannolikhet": f"{round(prob,1)}%", "Edge": round(best_edge*100, 1), "Odds": current_odds})
        
        if results:
            sorted_res = sorted(results, key=lambda x: x['Edge'], reverse=True)
            best = sorted_res[0]
            
            st.markdown(f"<div class='best-bet-box'><h3>🏆 TOPPVAL: {best['Match']}</h3>"
                        f"<p>Marknad: <b>{best['Spel']}</b> | Beräknad Edge: <b>{best['Edge']}%</b> | Sannolikhet: <b>{best['Sannolikhet']}</b></p></div>", unsafe_allow_html=True)
            
            # Kelly Criterion (25% fractional Kelly för säkerhet)
            k_stake = int(bankroll * ((best['Edge']/100)/(best['Odds']-1)) * 0.25)
            st.metric("Rekommenderad Kelly-insats (25% fr.)", f"{max(0, k_stake)} kr")
            st.dataframe(pd.DataFrame(sorted_res), use_container_width=True)

# --- TAB 2: LIVE CENTER ---
with tab2:
    st.subheader("⏱️ Live Scoreboard")
    live = get_live_data(curr_league)
    if live:
        for m in live: 
            st.markdown(f"**{m['teams']['home']['name']} {m['goals']['home']}-{m['goals']['away']} {m['teams']['away']['name']}** ({m['fixture']['status']['elapsed']}')")
    else: 
        st.info("Inga live-matcher just nu i denna liga.")

# --- TAB 3: NEURAL SCAN (MANUELL) ---
with tab3:
    if standings:
        t_list = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_sel = c1.selectbox("Hemmalag (Väder hämtas härifrån)", t_list, index=0)
        a_sel = c2.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)
        
        if st.button("KÖR FULL NEURAL SCAN"):
            h_st = next(t for t in standings if t['team']['name'] == h_sel)
            a_st = next(t for t in standings if t['team']['name'] == a_sel)
            
            # Väder-integration
            w_mod, w_desc = get_weather_mod(h_st['team']['name']) # Förenklat: kollar stad via lagnamn
            
            res = run_quantum_analysis(h_st, a_st, w_mod=w_mod)
            
            st.divider()
            st.subheader(f"Väderförhållanden: {w_desc}")
            
            met1, met2, met3 = st.columns(3)
            met1.metric("Över 2.5", f"{round(res['o25'],1)}%")
            met2.metric("Under 2.5", f"{round(res['u25'],1)}%")
            met3.metric("Väntat Antal Mål", f"{round(res['exp_goals'],2)}")
            
            st.subheader("Matchutgång (1X2)")
            chart_data = pd.DataFrame({'Sannolikhet %': [res['h_p'], res['d_p'], res['a_p']]}, index=['1 (Hemman)','X (Oavgjort)','2 (Borta)'])
            st.bar_chart(chart_data)
