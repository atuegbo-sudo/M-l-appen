import streamlit as st
import requests
import numpy as np
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="GoalPredictor OMNI-ULTRA", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .live-card { background: #080808; padding: 15px; border-left: 5px solid #00ff41; margin-bottom: 10px; border-radius: 5px; }
    .neural-box { background: #050505; padding: 20px; border: 2px solid #00ff41; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# API KEYS
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}

# --- 2. ENGINES ---

@st.cache_data(ttl=60)
def get_live_matches():
    try:
        res = requests.get("https://v3.football.api-sports.io", headers=HEADERS, timeout=10).json()
        return res.get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def get_standings(l_id):
    for s in [2025, 2024]:
        try:
            res = requests.get(f"https://v3.football.api-sports.io{l_id}&season={s}", headers=HEADERS).json()
            if res.get('response'): return res['response'][0]['league']['standings'][0], s
        except: continue
    return None, None

def run_sim(h_exp, a_exp, sims=1000000):
    h_s = np.random.poisson(max(0.1, h_exp), sims)
    a_s = np.random.poisson(max(0.1, a_exp), sims)
    t = h_s + a_s
    return {line: round(np.mean(t > line) * 100, 1) for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]}

# --- 3. UI ---
st.title("🧠 GOALPREDICTOR v150.0 OMNI")

t1, t2 = st.tabs(["🔍 PRE-MATCH SCANNER", "🔴 LIVE ANALYZER"])

with t1:
    LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135}
    l_name = st.selectbox("Välj Liga", list(LEAGUES.keys()))
    data, yr = get_standings(LEAGUES[l_name])
    
    if data:
        st.caption(f"Statistik baserad på säsong: {yr}")
        teams = sorted([t['team']['name'] for t in data])
        c1, c2 = st.columns(2)
        h_t = c1.selectbox("Hemmalag", teams, index=0)
        a_t = c2.selectbox("Bortalag", teams, index=1)
        
        if st.button("KÖR FULL SPECTRUM ANALYS"):
            h_s = next(t for t in data if t['team']['name'] == h_t)
            a_s = next(t for t in data if t['team']['name'] == a_t)
            
            h_exp = (h_s['all']['goals']['for'] / (h_s['all']['played'] or 1)) * 1.10
            a_exp = (a_s['all']['goals']['for'] / (a_s['all']['played'] or 1)) * 0.95
            
            probs = run_sim(h_exp, a_exp)
            st.markdown(f"<div class='neural-box'><h2>{h_t} vs {a_t}</h2></div>", unsafe_allow_html=True)
            cols = st.columns(6)
            for i, (line, p) in enumerate(probs.items()):
                cols[i].metric(f"Över {line}", f"{p}%")
    else:
        st.error("Kunde inte hämta tabell. Kontrollera API-nyckel.")

with t2:
    st.subheader("Live-matcher just nu")
    live_list = get_live_matches()
    
    if not live_list:
        st.info("Inga live-matcher hittades just nu. Visar demo-layout:")
        live_list = [{
            'teams': {'home': {'name': 'Demo Hemmalag'}, 'away': {'name': 'Demo Bortalag'}},
            'goals': {'home': 1, 'away': 1},
            'fixture': {'status': {'elapsed': 65}},
            'league': {'name': 'Träningsmatch'}
        }]
    
    for m in live_list:
        h, a = m['teams']['home']['name'], m['teams']['away']['name']
        hg, ag = m['goals']['home'], m['goals']['away']
        time = m['fixture']['status']['elapsed']
        
        # Enkel live-analys (xG baserat på tid kvar)
        rem_factor = (90 - time) / 90
        prob_o25 = min(100, round((hg+ag + 1.2 * rem_factor) * 35, 1)) if hg+ag < 3 else 100
        
        st.markdown(f"""
            <div class="live-card">
                <b>{h} {hg} - {ag} {a}</b> ({time}')<br>
                <small>{m['league']['name']}</small><br>
                <span style="color: #00ff41;">Sannolikhet Över 2.5 mål: {prob_o25}%</span>
            </div>
        """, unsafe_allow_html=True)
