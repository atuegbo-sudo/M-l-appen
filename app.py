import streamlit as st
import requests
import numpy as np
import pandas as pd

# --- 1. SETUP & MATRIX STYLE ---
st.set_page_config(page_title="GoalPredictor OMNI", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stButton>button { 
        background: #00ff41 !important; color: black !important; 
        font-weight: 900; width: 100%; height: 4em; border: 2px solid #ffffff;
        font-size: 18px !important; text-transform: uppercase; margin: 20px 0;
    }
    .metric-box { background: #050505; border: 1px solid #00ff41; padding: 15px; border-radius: 10px; text-align: center; }
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG (FELSÄKER) ---
API_KEY = "210961b3460594ed78d0a659e1ebf79b"
HEADERS = {'x-apisports-key': API_KEY}

@st.cache_data(ttl=600) # Kortare cache för att snabbare upptäcka om anslutningen är tillbaka
def get_data(l_id):
    url = f"https://v3.football.api-sports.io{l_id}&season=2025"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status() # Kastar fel om statuskoden är dålig
        data = res.json()
        if not data.get('response'):
            return None
        return data['response'][0]['league']['standings'][0]
    except Exception as e:
        return f"Error: {e}"

def run_sim(h_xg, a_xg):
    # Simulera 1 miljon matcher för 0.5 - 5.5 mål
    h_s = np.random.poisson(h_xg * 1.10, 1000000)
    a_s = np.random.poisson(a_xg * 0.95, 1000000)
    t = h_s + a_s
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    return {line: round(np.mean(t > line) * 100, 1) for line in lines}

# --- 3. UI LAYOUT ---
tab1, tab2 = st.tabs(["🧠 NEURAL SCANNER", "🔴 LIVE MONITOR"])

with tab1:
    st.sidebar.header("LIGA-VAL")
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135}
    l_name = st.sidebar.selectbox("Välj Liga", list(LEAGUES.keys()))
    
    standings = get_data(LEAGUES[l_name])
    
    if isinstance(standings, str): # Om get_data returnerar ett felmeddelande
        st.error(f"⚠️ Anslutningsproblem: API:et svarar inte. Kontrollera din internetanslutning eller API-nyckel.")
        st.info("Tips: Vänta 1 minut och ladda om sidan.")
    elif standings:
        teams = sorted([t['team']['name'] for t in standings])
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Välj Hemmalag", teams, index=0)
        a_team = c2.selectbox("Välj Bortalag", teams, index=1)
        
        # --- DEN STORA KNAPPEN ---
        if st.button("KÖR NEURAL ANALYS (VISA % 0.5 - 5.5)"):
            h_d = next(t for t in standings if t['team']['name'] == h_team)
            a_d = next(t for t in standings if t['team']['name'] == a_team)
            
            # Beräkna målsnitt från säsongsdata
            h_avg = h_d['all']['goals']['for'] / (h_d['all']['played'] or 1)
            a_avg = a_d['all']['goals']['for'] / (a_d['all']['played'] or 1)
            
            probs = run_sim(h_avg, a_avg)
            
            st.markdown(f"### 🎯 Analys: {h_team} vs {a_team}")
            
            # --- VISA PROCENTEN I ETT SVEP (6 KOLUMNER) ---
            cols = st.columns(6)
            for i, line in enumerate(probs):
                with cols[i]:
                    st.metric(f"ÖVER {line}", f"{probs[line]}%")
                    st.caption(f"Fair: {round(100/probs[line], 2) if probs[line] > 0 else 'N/A'}")
            
            st.success("✅ Neural simulering av 1 000 000 matcher klar.")
    else:
        st.warning("Ingen data hittades. Prova en annan liga eller kontrollera säsongsår.")

with tab2:
    st.info("Live-monitor: Matcher dyker upp här vid avspark (t.ex. kl. 20:45 ikväll).")
