import streamlit as st
import requests
import pandas as pd
import numpy as np

# --- 1. AI MATRIX STYLING ---
st.set_page_config(page_title="OMNI-QUANT PRO", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; border-radius: 10px; margin-bottom: 25px; text-align: center; }
    .signal-gold { color: #000; background: #00ff41; font-weight: 900; padding: 15px; text-align: center; border-radius: 5px; text-transform: uppercase; letter-spacing: 2px; }
    .stButton>button { background: #00ff41 !important; color: black !important; font-weight: 900; height: 3.5em; width: 100%; border: none; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 2.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIG & API (FELSÄKER) ---
API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': API_KEY}

@st.cache_data(ttl=600)
def get_advanced_stats(l_id):
    url = f"https://v3.football.api-sports.io{l_id}&season=2025"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get('response'):
            return data['response'][0]['league']['standings'][0]
        return None
    except Exception:
        return None

def run_pro_quantum_sim(h_att, a_def, a_att, h_def, corner_factor, h_mod, a_mod):
    # AI-Beräkning: Anfall möter Försvar + Väder/Skador/Hörnor
    h_final_xg = (h_att * a_def) * corner_factor * h_mod
    a_final_xg = (a_att * h_def) * corner_factor * a_mod
    
    # 1.0M Simulationer för extrem precision
    h_s = np.random.poisson(max(0.05, h_final_xg), 1000000)
    a_s = np.random.poisson(max(0.05, a_final_xg), 1000000)
    totals = h_s + a_s
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    return {line: np.mean(totals > line) * 100 for line in lines}

# --- 3. UI LAYOUT ---
st.title("🧠 OMNI-QUANT AI: DEEP DATA PRECISION")

with st.sidebar:
    st.header("📊 Deep Data Inputs")
    bankroll = st.number_input("Bankrulle (kr)", value=1000, step=100)
    m_odds = st.number_input("Marknadsodds (Över 2.5)", value=2.0, step=0.05)
    
    st.divider()
    st.subheader("🛠️ Manuella AI-Parametrar")
    corners = st.slider("Förväntat hörntryck (Totalt)", 0, 20, 10, help="Fler hörnor = Högre målchans")
    h_injuries = st.checkbox("Hemmalag: Nyckelspelare saknas")
    a_injuries = st.checkbox("Bortalag: Nyckelspelare saknas")

# --- 4. EXECUTION ---
LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135}
l_name = st.selectbox("Välj Liga", list(LEAGUES.keys()))
standings = get_advanced_stats(LEAGUES[l_name])

if standings:
    teams = sorted([t['team']['name'] for t in standings])
    c1, c2 = st.columns(2)
    h_team = c1.selectbox("Hemmalag", teams, index=0)
    a_team = c2.selectbox("Bortalag", teams, index=1)

    if st.button("RUN DEEP DATA ANALYSIS"):
        with st.spinner("AI is calculating probabilities..."):
            h_d = next(t for t in standings if t['team']['name'] == h_team)
            a_d = next(t for t in standings if t['team']['name'] == a_team)
            
            # Grund-styrka (xG per match) normaliserat
            h_att = (h_d['all']['goals']['for'] / h_d['all']['played']) / 1.3
            h_def = (h_d['all']['goals']['against'] / h_d['all']['played']) / 1.3
            a_att = (a_d['all']['goals']['for'] / a_d['all']['played']) / 1.3
            a_def = (a_d['all']['goals']['against'] / a_d['all']['played']) / 1.3
            
            # Parametrar: Hörnor (2% påverkan) & Skador (15% debuff)
            c_factor = 1 + ((corners - 10) * 0.02)
            h_mod = 0.85 if h_injuries else 1.15  # 1.15 inkluderar hemmaplansfördel
            a_mod = 0.85 if a_injuries else 1.0
            
            probs = run_pro_quantum_sim(h_att, a_def, a_att, h_def, c_factor, h_mod, a_mod)
            
            st.markdown(f"<div class='neural-box'><h2>🎯 {h_team} vs {a_team}</h2></div>", unsafe_allow_html=True)
            
            # Mål-svepet (Sannolikhet för 0.5 - 5.5)
            cols = st.columns(6)
            for i, line in enumerate(probs):
                with cols[i]:
                    st.metric(f"ÖVER {line}", f"{round(probs[line], 1)}%")

            # KELLY CRITERION AI DECISION
            prob_25 = probs[2.5] / 100
            edge = (prob_25 * m_odds) - 1
            fair_odds = 1 / (prob_25 if prob_25 > 0 else 0.001)
            
            st.divider()
            res_c1, res_c2 = st.columns(2)
            
            with res_c1:
                if edge > 0.02: # Kräver minst 2% edge för signal
                    st.markdown("<div class='signal-gold'>🔥 SIGNAL: VALUE DETECTED</div>", unsafe_allow_html=True)
                    # Fractional Kelly (10% av full Kelly för säkerhet)
                    kelly_pct = edge / (m_odds - 1)
                    stake = round(bankroll * kelly_pct * 0.10)
                    st.write(f"**AI Beslut:** Satsa **{max(0, stake)} kr** på Över 2.5 mål.")
                    st.write(f"**Värde (Edge):** +{round(edge*100, 2)}%")
                else:
                    st.warning("⚠️ SKIP: Inget statistiskt spelvärde. Marknaden är för effektiv.")
            
            with res_c2:
                st.write(f"**AI Fair Odds:** {round(fair_odds, 2)}")
                st.write(f"**Marknadens Odds:** {m_odds}")
                st.write(f"**Rek. Risk:** {round(kelly_pct*100 if edge > 0 else 0, 1)}% av kassan")
else:
    st.error("⚠️ API-ANSLUTNING MISSLYCKADES. Vänta 60 sekunder och ladda om sidan (F5).")
    st.info("Detta beror ofta på att API-gränsen för dygnet är nådd.")
