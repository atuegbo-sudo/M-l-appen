import streamlit as st
import requests
import pandas as pd
import numpy as np
import math

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="GoalPredictor v6.0 ULTRA", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #00ff41; }
    .stButton>button { background: linear-gradient(90deg, #00ff41, #008f11); color: black; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"
CURRENT_SEASON = 2025

# --- 2. LOGIK ---
@st.cache_data(ttl=3600)
def get_teams(league_id, season):
    url = f"{BASE_URL}/teams?league={league_id}&season={season}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        return {item['team']['name']: {'id': item['team']['id'], 'city': item['venue']['city']} for item in res['response']}
    except: return {}

def get_stats(team_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season={season}&team={team_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()['response']
        return float(res['goals']['for']['average']['total']), int(res['fixtures']['played']['total'])
    except: return 1.5, 5

# --- 3. UI DASHBOARD ---
with st.sidebar:
    st.title("🎯 System Control")
    category = st.radio("Kategori", ["Herrar", "Damer"])
    league_choice = st.selectbox("Välj Liga", list(LEAGUES_DB[category].keys()))
    curr_league_id = LEAGUES_DB[category][league_choice]
    st.divider()
    bankroll = st.number_input("Kassa (kr)", value=10000)

st.title(f"🚀 {category}: {league_choice.split(': ')[1]} Analyzer")

teams_data = get_teams(curr_league_id, CURRENT_SEASON)
if not teams_data:
    st.error("⚠️ Ingen data hittades. Kontrollera din API-nyckel eller att säsongen har startat.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    h_name = st.selectbox("Hemmalag", sorted(teams_data.keys()), index=0)
    h_form = st.slider("Hemma: Målsnitt (5 senaste)", 0.0, 5.0, 1.8)
with col2:
    a_name = st.selectbox("Bortalag", sorted(teams_data.keys()), index=1)
    a_form = st.slider("Borta: Målsnitt (5 senaste)", 0.0, 5.0, 1.4)

if st.button("STARTA QUANTUM-SIMULERING"):
    with st.spinner('Kör 150 000 Monte Carlo-scenarier...'):
        h_info, a_info = teams_data[h_name], teams_data[a_name]
        h_avg, h_played = get_stats(h_info['id'], curr_league_id, CURRENT_SEASON)
        a_avg, a_played = get_stats(a_info['id'], curr_league_id, CURRENT_SEASON)
        
        # Beräkning med Hemmaplansfördel & Quantum-viktning
        h_exp = ((h_form * 0.6) + (h_avg * 0.4)) * 1.12
        a_exp = ((a_form * 0.6) + (a_avg * 0.4)) * 0.94
        
        # Monte Carlo 150k
        sims = 150000
        h_sim = np.random.poisson(max(0.1, h_exp), sims)
        a_sim = np.random.poisson(max(0.1, a_exp), sims)
        prob_over = np.mean((h_sim + a_sim) > 2.5) * 100
        fair_odds = round(100/prob_over, 2) if prob_over > 0 else 0
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Sannolikhet Över 2.5", f"{round(prob_over, 1)}%")
        c2.metric("Ditt Rättvisa Odds", f"{fair_odds}")
        c3.metric("Datakvalitet", "HÖG" if h_played > 10 else "LÅG")
        
        # Måldiagram
        dist = pd.DataFrame({'Chans (%)': [round(np.mean((h_sim+a_sim)==i)*100, 1) for i in range(6)]}, index=['0','1','2','3','4','5+'])
        st.bar_chart(dist)
