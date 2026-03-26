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

# --- 2. API CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 3. DEEP SCAN ENGINES ---

@st.cache_data(ttl=20)
def get_deep_live_scan():
    """Hämtar ALLA pågående matcher globalt (inkl. Egypten, Afrika, U21 etc.)"""
    try:
        # Metod 1: Standard Live-API
        url_live = f"{BASE_URL}/fixtures?live=all"
        res_live = requests.get(url_live, headers=HEADERS, timeout=15).json()
        live_matches = res_live.get('response', [])
        
        # Metod 2: Fallback (Om vissa mindre ligor döljs i live-all)
        if not live_matches or len(live_matches) < 5:
            today = datetime.now().strftime('%Y-%m-%d')
            url_today = f"{BASE_URL}/fixtures?date={today}"
            res_today = requests.get(url_today, headers=HEADERS, timeout=15).json()
            # Filtrera fram matcher som faktiskt pågår (1H, 2H, HT, ET)
            live_statuses = ['1H', 'HT', '2H', 'ET', 'P', 'BT']
            live_matches = [m for m in res_today.get('response', []) if m['fixture']['status']['short'] in live_statuses]
            
        return live_matches
    except: return []

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    """Hämtar tabell för historisk analys"""
    for season in [2025, 2024]:
        try:
            res = requests.get(f"{BASE_URL}/standings?league={league_id}&season={season}", headers=HEADERS).json()
            if res.get('response'): return res['response']['league']['standings'], season
        except: continue
    return None, None

def get_weather_multiplier(city):
    """Väder-debuff för målprognos"""
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        if res.get('main'):
            cond = res['weather'][0]['main'].lower()
            mod = 0.85 if any(x in cond for x in ["rain", "snow", "storm"]) else 1.0
            return mod, f"{cond.upper()} ({res['main']['temp']}°C)"
    except: return 1.0, "WEATHER: NEUTRAL"

def run_neural_simulation(h_exp, a_exp, w_mod, sims=1000000):
    """Neural 1M Monte Carlo Simulation för 0.5 - 5.5 mål"""
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
tab1, tab2, tab3 = st.tabs(["🧠 NEURAL SCANNER", "🔴 GLOBAL LIVE DEEP-SCAN", "📊 SEASON STATS"])

# --- TAB 1: PRE-MATCH ANALYSIS ---
with tab1:
    st.sidebar.header("🎯 System Control")
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135, "Bundesliga": 78}
    l_name = st.sidebar.selectbox("Välj Marknad", list(LEAGUES.keys()))
    
    standings, active_season = get_league_standings(LEAGUES[l_name])
    
    if standings:
        teams = sorted([t['team']['name'] for t in standings])
        col1, col2 = st.columns(2)
        h_team = col1.selectbox("Home Team", teams, index=0)
        a_team = col2.selectbox("Away Team", teams, index=1)
        
        m_odds = st.sidebar.number_input("Marknadsodds (Över 2.5)", value=2.00, step=0.01)
        
        if st.button("EXECUTE OMNI-SCAN (1.0M ITERATIONS)"):
            h_stats = next(t for t in standings if t['team']['name'] == h_team)
            a_stats = next(t for t in standings if t['team']['name'] == a_team)
            
            w_mod, w_desc = get_weather_multiplier(h_team)
            
            # Beräkna xG baserat på Hemma (+10%) / Borta (-5%)
            h_exp = (h_stats['all']['goals']['for'] / (h_stats['all']['played'] or 1)) * 1.10
            a_exp = (a_stats['all']['goals']['for'] / (a_stats['all']['played'] or 1)) * 0.95
            
            probs = run_neural_simulation(h_exp, a_exp, w_mod)
            
            st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2><p>{w_desc} | Season: {active_season}</p></div>", unsafe_allow_html=True)
            
            res_cols = st.columns(6)
            for i, line in enumerate(probs):
                res_cols[i].metric(f"Över {line}", f"{probs[line]['prob']}%")
                res_cols[i].caption(f"Fair: {probs[line]['fair']}")
            
            edge = ((probs[2.5]['prob']/100) * m_odds) - 1
            st.divider()
            v1, v2 = st.columns(2)
            v1.metric("Neural Edge (O2.5)", f"{round(edge*100, 2)}%")
            v2.metric("Kelly Stake (5%)", f"{max(0, int(100000 * edge * 0.05))} kr")

# --- TAB 2: GLOBAL LIVE (Inkl. Egypten/Afrika) ---
with tab2:
    st.subheader("🔴 GLOBAL LIVE FEED (Deep Scan Active)")
    live_matches = get_deep_live_scan()
    
    if live_matches:
        st.caption(f"Hittade {len(live_matches)} matcher pågående just nu.")
        col_left, col_right = st.columns(2)
        
        for i, m in enumerate(live_matches):
            h, a = m['teams']['home']['name'], m['teams']['away']['name']
            hg, ag = m['goals']['home'], m['goals']['away']
            elap = m['fixture']['status']['elapsed']
            lg, country = m['league']['name'], m['league']['country']
            
            target_col = col_left if i % 2 == 0 else col_right
            
            with target_col:
                st.markdown(f"""
                <div class="live-card">
                    <div style="display: flex; justify-content: space-between;">
                        <span class="status-live">LIVE {elap}'</span>
                        <span style="color: #666; font-size: 0.8em;">{lg} ({country})</span>
                    </div>
                    <div style="font-size: 1.3em; margin-top: 8px;">
                        <b>{h} {hg} - {ag} {a}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Inga matcher live just nu. Tryck 'Force Refresh' i menyn för att söka igen.")

# --- TAB 3: STANDINGS ---
with tab3:
    if standings:
        st.subheader(f"Ligatabell: {l_name}")
        df = pd.DataFrame([{'Rank': t['rank'], 'Lag': t['team']['name'], 'Spelade': t['all']['played'], 'Mål': f"{t['all']['goals']['for']}:{t['all']['goals']['against']}", 'Poäng': t['points']} for t in standings])
        st.dataframe(df.set_index('Rank'), use_container_width=True)

# --- SIDEBAR TOOLS ---
st.sidebar.markdown("---")
if st.sidebar.button("FORCE REFRESH WORLD DATA"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"v150.0 OMNI | Last Sync: {datetime.now().strftime('%H:%M:%S')}")
