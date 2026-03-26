import streamlit as st
import requests
import pandas as pd
import numpy as np

# --- 1. AI MATRIX STYLING ---
st.set_page_config(page_title="OMNI-QUANT PRO", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .neural-box { background: #050505; padding: 20px; border: 2px solid #00ff41; border-radius: 10px; margin-bottom: 20px; }
    .signal-gold { color: #ffd700; font-weight: bold; border: 1px solid #ffd700; padding: 15px; text-align: center; background: #221a00; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIG & API ---
API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': API_KEY}

@st.cache_data(ttl=3600)
def get_advanced_stats(l_id):
    # Hämtar tabell och underliggande stats
    url = f"https://v3.football.api-sports.io{l_id}&season=2025"
    res = requests.get(url, headers=HEADERS).json()
    return res['response']['league']['standings'] if res.get('response') else []

def run_pro_quantum_sim(h_att, a_def, a_att, h_def, corner_factor, injury_mod):
    """Avancerad AI-motor som väger in alla faktorer"""
    # Justera anfallsstyrka baserat på skador och hörnor
    h_final_xg = (h_att * a_def) * corner_factor * injury_mod[0]
    a_final_xg = (a_att * h_def) * corner_factor * injury_mod[1]
    
    # 1 miljon iterationer för maximal precision
    h_s = np.random.poisson(h_final_xg, 1000000)
    a_s = np.random.poisson(a_final_xg, 1000000)
    totals = h_s + a_s
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    return {line: np.mean(totals > line) * 100 for line in lines}

# --- 3. UI & INPUTS ---
st.title("🧠 OMNI-QUANT AI: DEEP DATA PRECISION")

with st.sidebar:
    st.header("📊 Deep Data Inputs")
    bankroll = st.number_input("Bankrulle (kr)", value=1000)
    m_odds = st.number_input("Marknadsodds (Över 2.5)", value=2.0, step=0.05)
    
    st.divider()
    st.subheader("🛠️ Manuella AI-Parametrar")
    corners = st.slider("Förväntat hörntryck (Totalt)", 0, 20, 10)
    h_injuries = st.checkbox("Hemmalag: Nyckelspelare borta?")
    a_injuries = st.checkbox("Bortalag: Nyckelspelare borta?")

# --- 4. EXECUTION ---
LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140}
l_name = st.selectbox("Välj Liga", list(LEAGUES.keys()))
standings = get_advanced_stats(LEAGUES[l_name])

if standings:
    teams = sorted([t['team']['name'] for t in standings])
    c1, c2 = st.columns(2)
    h_team = c1.selectbox("Hemmalag", teams, index=0)
    a_team = c2.selectbox("Bortalag", teams, index=1)

    if st.button("RUN DEEP DATA ANALYSIS"):
        h_d = next(t for t in standings if t['team']['name'] == h_team)
        a_d = next(t for t in standings if t['team']['name'] == a_team)
        
        # 1. Grund-styrka (xG per match)
        h_att = (h_d['all']['goals']['for'] / h_d['all']['played']) / 1.3
        h_def = (h_d['all']['goals']['against'] / h_d['all']['played']) / 1.3
        a_att = (a_d['all']['goals']['for'] / a_d['all']['played']) / 1.3
        a_def = (a_d['all']['goals']['against'] / a_d['all']['played']) / 1.3
        
        # 2. Faktorer (Hörnor ökar chansen med ca 2% per hörn över snittet)
        c_factor = 1 + ((corners - 10) * 0.02)
        
        # 3. Skador (Sänker lagets xG med 15% om nyckelspelare saknas)
        h_mod = 0.85 if h_injuries else 1.0
        a_mod = 0.85 if a_injuries else 1.0
        
        # 4. Kör simulering (1.15 = Hemmafördel)
        probs = run_pro_quantum_sim(h_att * 1.15, a_def, a_att, h_def, c_factor, [h_mod, a_mod])
        
        # --- PRESENTATION ---
        st.markdown(f"<div class='neural-box'><h2>🎯 {h_team} vs {a_team}</h2></div>", unsafe_allow_html=True)
        
        cols = st.columns(6)
        for i, line in enumerate(probs):
            with cols[i]:
                st.metric(f"ÖVER {line}", f"{round(probs[line], 1)}%")

        # KELLY CRITERION AI
        prob_25 = probs[2.5] / 100
        edge = (prob_25 * m_odds) - 1
        fair_odds = 1 / prob_25
        
        st.divider()
        res_c1, res_c2 = st.columns(2)
        
        with res_c1:
            if edge > 0:
                st.markdown("<div class='signal-gold'>🔥 SIGNAL: VALUE DETECTED</div>", unsafe_allow_html=True)
                kelly_pct = edge / (m_odds - 1)
                stake = round(bankroll * kelly_pct * 0.1) # 10% Kelly (Säkerhetsmarginal)
                st.write(f"**AI Beslut:** Satsa **{stake} kr** på Över 2.5 mål.")
                st.write(f"**Värde (Edge):** +{round(edge*100, 2)}%")
            else:
                st.warning("⚠️ SKIP: Inget spelvärde hittat. Marknaden är för effektiv.")
        
        with res_c2:
            st.write(f"**AI Fair Odds:** {round(fair_odds, 2)}")
            st.write(f"**Marknadens Odds:** {m_odds}")

else:
    st.error("Kunde inte nå API-data för ligastatistik.")
