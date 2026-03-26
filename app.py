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
    .neural-box { background: #050505; border: 2px solid #00ff41; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 0.8rem !important; }
    </style>
    """, unsafe_allow_html=True)

API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': API_KEY}

# --- 2. DATA FETCHING MED SÄKER FALLBACK ---
@st.cache_data(ttl=600)
def get_safe_data(l_id):
    url = f"https://v3.football.api-sports.io{l_id}&season=2025"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        data = res.json()
        if data.get('response') and len(data['response']) > 0:
            return data['response'][0]['league']['standings'][0]
    except:
        pass
    # ROBUST FALLBACK: Skapar minst två lag så selectbox (index=1) inte kraschar
    return [
        {"team": {"name": "Laddar... (API OFFLINE)"}, "all": {"played": 1, "goals": {"for": 1, "against": 1}}},
        {"team": {"name": "Testa igen (API OFFLINE)"}, "all": {"played": 1, "goals": {"for": 1, "against": 1}}}
    ]

def run_quantum_sim(h_xg, a_xg, shot_f, corner_f, sims=1000000):
    # AI-simulering med skott och hörn-parametrar
    h_final = h_xg * shot_f * corner_f
    a_final = a_xg * (1/shot_f) * corner_f
    
    h_sim = np.random.poisson(max(0.05, h_final), sims)
    a_sim = np.random.poisson(max(0.05, a_final), sims)
    totals = h_sim + a_sim
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    return {line: np.mean(totals > line) * 100 for line in lines}

# --- 3. UI LAYOUT ---
st.title("🧠 OMNI-QUANT AI: QUANTUM PRECISION")

with st.sidebar:
    st.header("📊 Deep Data Analysis")
    bankroll = st.number_input("Din Bankrulle (kr)", value=1000)
    m_odds = st.number_input("Odds (Över 2.5)", value=2.00)
    
    st.divider()
    shots_on_target = st.slider("Skott på mål-faktor", 0.5, 2.0, 1.0)
    corners = st.slider("Hörn-tryck", 0.5, 2.0, 1.0)
    injury_debuff = st.checkbox("Varning: Nyckelspelare saknas")

# --- 4. EXECUTION ---
LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140}
l_name = st.selectbox("Välj Liga", list(LEAGUES.keys()))
standings = get_safe_data(LEAGUES[l_name])

if standings:
    # Hämtar lagnamn säkert
    teams = sorted([t['team']['name'] for t in standings])
    c1, c2 = st.columns(2)
    h_team = c1.selectbox("Hemmalag", teams, index=0)
    # Säkerställer att index=1 bara används om det finns fler än 1 lag
    a_idx = 1 if len(teams) > 1 else 0
    a_team = c2.selectbox("Bortalag", teams, index=a_idx)

    if st.button("EXECUTE QUANTUM SCAN (ALL LINES 0.5 - 5.5)"):
        h_d = next((t for t in standings if t['team']['name'] == h_team), standings[0])
        a_d = next((t for t in standings if t['team']['name'] == a_team), standings[0])
        
        # Beräkna xG (mål per match)
        h_xg = (h_d['all']['goals']['for'] / (h_d['all']['played'] or 1)) * 1.15
        a_xg = (a_d['all']['goals']['for'] / (a_d['all']['played'] or 1))
        
        if injury_debuff:
            h_xg *= 0.85
            a_xg *= 0.85
            
        probs = run_quantum_sim(h_xg, a_xg, shots_on_target, corners)
        
        st.markdown(f"<div class='neural-box'><h2>🎯 {h_team} vs {a_team}</h2></div>", unsafe_allow_html=True)
        
        # --- ALLA MÅLLINJER I ETT SVEP (6 KOLUMNER) ---
        cols = st.columns(6)
        for i, line in enumerate(probs):
            with cols[i]:
                st.metric(f"ÖVER {line}", f"{round(probs[line], 1)}%")
                st.caption(f"Fair: {round(100/probs[line], 2) if probs[line] > 0 else 'N/A'}")

        # --- AI BESLUT (KELLY) ---
        prob_25 = probs[2.5] / 100
        edge = (prob_25 * m_odds) - 1
        
        st.divider()
        if edge > 0:
            kelly_stake = (edge / (m_odds - 1)) * 0.1
            st.success(f"🔥 AI SIGNAL: Satsa **{round(bankroll * kelly_stake)} kr** på Över 2.5 mål. Edge: +{round(edge*100, 2)}%")
        else:
            st.warning("❌ AI AVSTYR: Inget spelvärde (Edge < 0).")
