import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. PRO STYLING (MATRIX DESIGN) ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-ULTRA", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; box-shadow: 0 0 10px #00ff4122; border-radius: 5px; text-align: center; }
    .stButton>button { background: #00ff41 !important; color: black !important; font-weight: 900; letter-spacing: 3px; border: none; height: 4em; width: 100%; transition: 0.5s; text-transform: uppercase; }
    .stButton>button:hover { background: #ffffff !important; box-shadow: 0 0 50px #00ff41; }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; margin-bottom: 25px; border-radius: 10px; text-align: center; }
    .live-card { background: #080808; padding: 15px; border-left: 5px solid #00ff41; margin-bottom: 10px; border-radius: 5px; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 0.8rem !important; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE NEURAL CORE CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
SEASON = 2025 # Kan ändras till 2026 när säsongerna startar

# --- 3. ENGINES (STATS, WEATHER, SIM) ---

def get_weather_factor(city):
    """Hämtar live-väder för hemmastaden"""
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        condition = res['weather'][0]['main'].lower()
        if any(word in condition for word in ["rain", "snow", "drizzle", "thunderstorm"]):
            return 0.88, f"⚠️ {condition.upper()} (DEBUFF)"
        return 1.0, "☀️ CLEAR"
    except: return 1.0, "WEATHER N/A"

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    """Hämtar ligatabell för historisk statistik"""
    try:
        res = requests.get(f"{BASE_URL}/standings?league={league_id}&season={SEASON}", headers=HEADERS).json()
        return res['response'][0]['league']['standings'][0] if res.get('response') else []
    except: return []

@st.cache_data(ttl=30)
def get_live_data():
    """Hämtar ALLA live-matcher globalt (inkl. landskamper)"""
    try:
        res = requests.get(f"{BASE_URL}/fixtures?live=all", headers=HEADERS, timeout=10).json()
        return res.get('response', [])
    except: return []

def run_deep_simulation(h_exp, a_exp, weather_mod, sims=1000000):
    """Neural motor: 1M iterationer för alla mållinjer"""
    # Hemma (+10%) / Borta (-5%) Bias + Väder
    h_final = h_exp * 1.10 * weather_mod
    a_final = a_exp * 0.95 * weather_mod
    
    h_s = np.random.poisson(max(0.05, h_final), sims)
    a_s = np.random.poisson(max(0.05, a_final), sims)
    totals = h_s + a_s
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    results = {}
    for line in lines:
        prob = np.mean(totals > line) * 100
        fair = round(100/prob, 2) if prob > 0 else 99.0
        results[line] = {"prob": round(prob, 1), "fair": fair}
    return results

def analyze_live_probability(h_g, a_g, elapsed, h_avg, a_avg):
    """Realtidsanalys för pågående matcher"""
    rem_time = max(0, 90 - elapsed)
    time_factor = rem_time / 90
    curr_tot = h_g + a_g
    future_xg = (h_avg + a_avg) * time_factor
    future_goals = np.random.poisson(future_xg, 100000)
    prob_over = np.mean((curr_tot + future_goals) > 2.5) * 100
    return round(prob_over, 1)

# --- 4. DASHBOARD TABS ---
tab1, tab2, tab3 = st.tabs(["🧠 NEURAL SCANNER", "🔴 LIVE MONITOR", "📊 GLOBAL STATS"])

# --- TAB 1: FULL SPECTRUM ANALYSIS ---
with tab1:
    st.sidebar.header("🎯 System Control")
    LEAGUES = {
        "Allsvenskan": 113, "Premier League": 39, "La Liga": 140, 
        "Serie A": 135, "Bundesliga": 78, "VM-kval (EU)": 3
    }
    l_name = st.sidebar.selectbox("Välj Marknad", list(LEAGUES.keys()))
    l_id = LEAGUES[l_name]
    
    standings = get_league_standings(l_id)
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        col_h, col_a = st.columns(2)
        h_team = col_h.selectbox("🏠 Hemma (Stat + 10% Advantage)", teams, index=0)
        a_team = col_a.selectbox("✈️ Borta (Stat - 5% Debuff)", teams, index=1)
        
        m_odds = st.sidebar.number_input("Ditt Odds (Över 2.5)", value=2.00, step=0.01)
        
        if st.button("EXECUTE OMNI-SCAN (ALL LINES)"):
            with st.spinner("⚡ ANALYZING HISTORICAL DATA & WEATHER..."):
                h_data = next(t for t in standings if t['team']['name'] == h_team)
                a_data = next(t for t in standings if t['team']['name'] == a_team)
                
                w_mod, w_desc = get_weather_factor(h_team)
                h_avg = h_data['all']['goals']['for'] / (h_data['all']['played'] or 1)
                a_avg = a_data['all']['goals']['for'] / (a_data['all']['played'] or 1)
                
                probs = run_deep_simulation(h_avg, a_avg, w_mod)
                
                st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2>"
                            f"VÄDER: {w_desc} | LIGA: {l_name}</div>", unsafe_allow_html=True)
                
                # Visa 0.5 till 5.5 i ett svep (6 kolumner)
                res_cols = st.columns(6)
                lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
                for i, line in enumerate(lines):
                    with res_cols[i]:
                        st.metric(f"ÖVER {line}", f"{probs[line]['prob']}%")
                        st.caption(f"Fair: {probs[line]['fair']}")
                
                edge = ((probs[2.5]['prob']/100) * m_odds) - 1
                st.divider()
                v1, v2 = st.columns(2)
                v1.metric("Neural Edge (O2.5)", f"{round(edge*100, 2)}%")
                v2.metric("Kelly Stake (5%)", f"{max(0, int(100000 * edge * 0.05))} kr")
    else:
        st.error("Kunde inte ladda ligadata. Välj en annan liga eller kontrollera säsongsår.")

# --- TAB 2: GLOBAL LIVE MONITOR (INKL LANDSKAMPER) ---
with tab2:
    st.subheader("🔴 GLOBAL LIVE FEED (ALL LEAGUES & INTERNATIONALS)")
    live_matches = get_live_data()
    
    if live_matches:
        for m in live_matches:
            h_n, a_n = m['teams']['home']['name'], m['teams']['away']['name']
            h_g, a_g = m['goals']['home'], m['goals']['away']
            elap = m['fixture']['status']['elapsed']
            l_info = f"{m['league']['country']}: {m['league']['name']}"
            
            # Snabb-analys (1.4 snitt-xG som fallback live)
            l_prob = analyze_live_probability(h_g, a_g, elap, 1.4, 1.2)
            
            st.markdown(f"""
            <div class="live-card">
                <span style="color: #00ff41; font-weight: bold;">{elap}'</span> | {l_info}<br>
                <span style="font-size: 1.3em;">{h_n} {h_g} - {a_g} {a_n}</span><br>
                <span style="color: #888;">Neural Prob O2.5: </span><b>{l_prob}%</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Inga aktiva matcher just nu. Kontrollera igen vid avspark (t.ex. 20:45 ikväll).")

# --- TAB 3: STANDINGS ---
with tab3:
    if standings:
        st.subheader(f"Tabell: {l_name}")
        df = pd.DataFrame([
            {'Rank': t['rank'], 'Lag': t['team']['name'], 'GP': t['all']['played'], 'Mål': f"{t['all']['goals']['for']}:{t['all']['goals']['against']}", 'Poäng': t['points']} 
            for t in standings
        ])
        st.table(df.set_index('Rank'))
