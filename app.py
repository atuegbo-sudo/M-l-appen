import streamlit as st
import numpy as np
import requests
import pandas as pd

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="OMNI-QUANT QUANTUM", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stButton>button { background: #00ff41 !important; color: black !important; font-weight: 900; width: 100%; border: none; height: 3em; }
    .neural-box { background: #050505; border: 2px solid #00ff41; padding: 25px; border-radius: 10px; text-align: center; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': API_KEY}

# --- 2. ROBUST DATA FETCHING ---
@st.cache_data(ttl=600)
def get_safe_data(l_id):
    url = f"https://v3.football.api-sports.io{l_id}&season=2025"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        data = res.json()
        if data.get('response'):
            return data['response'][0]['league']['standings'][0]
    except:
        pass
    # FALLBACK DATA: Om API sviker, skapa en lista så appen inte dör
    return [{"team": {"name": "Välj lag (API OFFLINE)"}, "all": {"played": 1, "goals": {"for": 1, "against": 1}}}]

def run_quantum_sim(h_xg, a_xg, shot_factor, corner_factor, sims=500000):
    # AI-motor som väger in skott-effektivitet och hörn-tryck
    h_final = h_xg * shot_factor * corner_factor
    a_final = a_xg * (1/shot_factor) * corner_factor
    
    h_sim = np.random.poisson(max(0.1, h_final), sims)
    a_sim = np.random.poisson(max(0.1, a_final), sims)
    totals = h_sim + a_sim
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    return {line: np.mean(totals > line) * 100 for line in lines}

# --- 3. UI LAYOUT ---
with st.sidebar:
    st.header("📊 Deep Data Analysis")
    bankroll = st.number_input("Din Bankrulle (kr)", value=1000)
    m_odds = st.number_input("Odds (Över 2.5)", value=2.00)
    
    st.divider()
    shots_on_target = st.slider("Skott på mål-faktor", 0.5, 2.0, 1.0, help="Högre = Mer effektiva skott")
    corners = st.slider("Hörn-tryck", 0.5, 2.0, 1.0, help="Högre = Mer tryck i boxen")
    injury_debuff = st.checkbox("Varning: Nyckelspelare saknas (-15% xG)")

# --- 4. EXECUTION ---
st.title("🧠 OMNI-QUANT AI: QUANTUM PRECISION")

LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140}
l_name = st.selectbox("Välj Liga", list(LEAGUES.keys()))
standings = get_safe_data(LEAGUES[l_name])

if standings:
    teams = sorted([t['team']['name'] for t in standings])
    c1, c2 = st.columns(2)
    h_team = c1.selectbox("Hemmalag", teams, index=0)
    a_team = c2.selectbox("Bortalag", teams, index=1)

    if st.button("EXECUTE QUANTUM SCAN"):
        # Hitta lagstatistik
        h_d = next((t for t in standings if t['team']['name'] == h_team), standings[0])
        a_d = next((t for t in standings if t['team']['name'] == a_team), standings[0])
        
        # Beräkna xG (mål per match)
        h_xg = (h_d['all']['goals']['for'] / h_d['all']['played']) * 1.10 # +10% hemmaplan
        a_xg = (a_d['all']['goals']['for'] / a_d['all']['played'])
        
        if injury_debuff:
            h_xg *= 0.85
            a_xg *= 0.85
            
        # Kör AI-Simulering
        probs = run_quantum_sim(h_xg, a_xg, shots_on_target, corners)
        
        st.markdown(f"<div class='neural-box'><h2>{h_team} vs {a_team}</h2></div>", unsafe_allow_html=True)
        
        # Mål-procent 0.5 - 5.5 i ett svep
        cols = st.columns(6)
        for i, line in enumerate(probs):
            with cols[i]:
                st.metric(f"ÖVER {line}", f"{round(probs[line], 1)}%")

        # --- AI BESLUT (KELLY CRITERION) ---
        prob_25 = probs[2.5] / 100
        edge = (prob_25 * m_odds) - 1
        
        st.divider()
        if edge > 0:
            kelly_stake = (edge / (m_odds - 1)) * 0.1 # 10% Kelly för säkerhet
            st.success(f"🔥 AI SIGNAL: Värde hittat! Satsa **{round(bankroll * kelly_stake)} kr** på Över 2.5 mål.")
            st.write(f"Edge: +{round(edge*100, 2)}% | Fair Odds: {round(1/prob_25, 2)}")
        else:
            st.error("❌ INGET VÄRDE: AI avråder från spel på Över 2.5 mål.")

st.sidebar.caption("v2.0 Quantum Engine | Connection Shield Active")
