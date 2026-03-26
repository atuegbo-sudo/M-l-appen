import streamlit as st
import requests
import pandas as pd
import numpy as np

# --- 1. PRO STYLING (MATRIX DESIGN) ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-LIVE", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; box-shadow: 0 0 10px #00ff4122; border-radius: 5px; text-align: center; }
    .stButton>button { background: #00ff41 !important; color: black !important; font-weight: 900; height: 4em; width: 100%; border: none; text-transform: uppercase; letter-spacing: 2px; }
    .stButton>button:hover { background: #ffffff !important; box-shadow: 0 0 30px #00ff41; }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; margin-bottom: 25px; border-radius: 10px; text-align: center; }
    .live-card-header { color: #00ff41; font-weight: bold; font-size: 1.1em; cursor: pointer; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 1.6rem !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 0.8rem !important; text-transform: uppercase; }
    /* Gör expandern snyggare i mörkt tema */
    .streamlit-expanderHeader { background-color: #080808 !important; border: 1px solid #333 !important; color: #00ff41 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 3. ENGINES ---

@st.cache_data(ttl=30)
def get_live_data():
    try:
        res = requests.get(f"{BASE_URL}/fixtures?live=all", headers=HEADERS, timeout=10).json()
        return res.get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season=2025", headers=HEADERS).json()
        return res['response']['league']['standings'] if res.get('response') else []
    except: return []

def run_deep_simulation(h_exp, a_exp, sims=1000000):
    h_s = np.random.poisson(max(0.1, h_exp * 1.10), sims)
    a_s = np.random.poisson(max(0.1, a_exp * 0.95), sims)
    totals = h_s + a_s
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    return {line: round(np.mean(totals > line) * 100, 1) for line in lines}

def analyze_live_probability(h_g, a_g, elapsed, avg_goals=2.8):
    """Beräknar chansen för fler mål baserat på tid kvar"""
    rem_time = max(0, 90 - elapsed)
    time_factor = rem_time / 90
    future_xg = avg_goals * time_factor
    future_goals = np.random.poisson(future_xg, 100000)
    
    prob_over_current = np.mean(future_goals > 0.5) * 100
    prob_plus_two = np.mean(future_goals > 1.5) * 100
    return round(prob_over_current, 1), round(prob_plus_two, 1)

# --- 4. UI TABS ---
tab1, tab2 = st.tabs(["🧠 NEURAL SCANNER", "🔴 LIVE MONITOR"])

with tab1:
    st.sidebar.header("🎯 System Control")
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135, "Bundesliga": 78}
    l_name = st.sidebar.selectbox("Välj Liga", list(LEAGUES.keys()))
    l_id = LEAGUES[l_name]
    standings = get_league_standings(l_id)
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Hemmalag", teams, index=0)
        a_team = c2.selectbox("Bortalag", teams, index=1)
        
        if st.button("EXECUTE OMNI-SCAN (0.5 - 5.5 GOALS)"):
            h_d = next(t for t in standings if t['team']['name'] == h_team)
            a_d = next(t for t in standings if t['team']['name'] == a_team)
            h_avg = h_d['all']['goals']['for'] / (h_d['all']['played'] or 1)
            a_avg = a_d['all']['goals']['for'] / (a_d['all']['played'] or 1)
            probs = run_deep_simulation(h_avg, a_avg)
            
            st.markdown(f"<div class='neural-box'><h2>🎯 {h_team} vs {a_team}</h2></div>", unsafe_allow_html=True)
            res_cols = st.columns(6)
            for i, line in enumerate(probs):
                with res_cols[i]:
                    st.metric(f"ÖVER {line}", f"{probs[line]}%")
    else:
        st.error("Kunde inte hämta data för vald liga.")

with tab2:
    st.subheader("🔴 Global Live Monitor (Klicka på en match för analys)")
    live_matches = get_live_data()
    
    if live_matches:
        for m in live_matches:
            h_n, a_n = m['teams']['home']['name'], m['teams']['away']['name']
            h_g, a_g = m['goals']['home'], m['goals']['away']
            elap = m['fixture']['status']['elapsed']
            league = m['league']['name']
            
            # Skapa en klickbar expander för varje match
            with st.expander(f"⏱️ {elap}' | {h_n} {h_g} - {a_g} {a_n} ({league})"):
                st.write("### 🧠 Live Neural Prediction")
                p1, p2 = analyze_live_probability(h_g, a_g, elap)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Chans för +1 mål till", f"{p1}%")
                c2.metric("Chans för +2 mål till", f"{p2}%")
                c3.write(f"**Aktuell ställning:** {h_g}-{a_g}")
                
                st.info(f"Baserat på att {elap} minuter har spelats är den neurala förväntningen att matchen slutar med fler mål {p1}% sannolik.")
    else:
        st.info("Inga matcher live just nu. Matcherna ikväll startar kl. 20:45!")
