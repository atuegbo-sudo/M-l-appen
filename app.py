import streamlit as st
import requests
import math
import pandas as pd
import numpy as np

# --- 1. KONFIGURATION ---
API_KEY = "210961b3460594ed78d0a659e1ebf79b" # <--- DIN NYCKEL HÄR
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-apisports-key': API_KEY,
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# --- 2. MATEMATIK & SIMULERING ---
def poisson_prob(lmbda, k):
    if lmbda <= 0: return 0
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)

def run_monte_carlo(home_exp, away_exp, simulations=10000):
    home_goals = np.random.poisson(home_exp, simulations)
    away_goals = np.random.poisson(away_exp, simulations)
    prob_over_25 = np.mean((home_goals + away_goals) > 2.5) * 100
    return round(prob_over_25, 2)

# --- 3. API-FUNKTIONER ---
@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"{BASE_URL}/teams?league={league_id}&season=2023"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        return {item['team']['name']: item['team']['id'] for item in res['response']} if res.get('response') else {}
    except: return {}

def get_detailed_stats(team_id, league_id):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season=2023&team={team_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()['response']
        avg_f = float(res['goals']['for']['average']['total'])
        played = int(res['fixtures']['played']['total'])
        return avg_f, played
    except: return 1.5, 0

def get_h2h_factor(home_id, away_id):
    url = f"{BASE_URL}/fixtures/headtohead?h2h={home_id}-{away_id}&last=5"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json().get('response', [])
        if not res: return 1.0, 0
        avg_g = sum(f['goals']['home'] + f['goals']['away'] for f in res) / len(res)
        factor = 1.15 if avg_g > 3.0 else (0.85 if avg_g < 2.0 else 1.0)
        return factor, len(res)
    except: return 1.0, 0

# --- 4. GRÄNSSNITT ---
st.set_page_config(page_title="GoalPredictor Intelligence v4.5", layout="wide")
st.title("🛡️ GoalPredictor Intelligence v4.5 PRO")

st.sidebar.header("Global Analys")
league_name = st.sidebar.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
curr_league = leagues[league_name]

teams = get_teams(curr_league)
if not teams:
    st.error("⚠️ API-anslutning misslyckades. Kontrollera din nyckel.")
    st.stop()

t_list = sorted(list(teams.keys()))
col1, col2 = st.columns(2)

with col1:
    h_name = st.selectbox("Hemmalag", t_list, index=0)
    h_elo = st.slider("Hemma: Elo Styrka", 1000, 2000, 1500)
    h_form = st.slider("Hemma: Snittmål (5 senaste)", 0.0, 5.0, 1.8)

with col2:
    a_name = st.selectbox("Bortalag", t_list, index=1)
    a_elo = st.slider("Borta: Elo Styrka", 1000, 2000, 1450)
    a_form = st.slider("Borta: Snittmål (5 senaste)", 0.0, 5.0, 1.4)

# --- 5. ANALYS-KÖRNING ---
if st.button("STARTA PRO-SIMULERING"):
    with st.spinner('Kör Monte Carlo & Risk-analys...'):
        h_id, a_id = teams[h_name], teams[a_name]
        h_avg, h_played = get_detailed_stats(h_id, curr_league)
        a_avg, a_played = get_detailed_stats(a_id, curr_league)
        h2h_mod, h2h_count = get_h2h_factor(h_id, a_id)
        
        # Beräkning: Elo + Form + H2H
        elo_diff = (h_elo - a_elo) / 1000
        h_exp = ((h_form * 0.6) + (h_avg * 0.4) + elo_diff) * h2h_mod * 1.05
        a_exp = ((a_form * 0.6) + (a_avg * 0.4) - elo_diff) * h2h_mod * 0.95
        h_exp, a_exp = max(0.1, h_exp), max(0.1, a_exp)
        
        # Sannolikhet & Risk
        prob = run_monte_carlo(h_exp, a_exp)
        fair_odds = round(100 / prob, 2) if prob > 0 else 0
        
        # Risk-o-meter logik
        risk_score = 0
        if h_played < 8 or a_played < 8: risk_score += 50
        if h2h_count < 3: risk_score += 20
        
        st.divider()
        if risk_score >= 60: st.warning(f"🔴 HÖG RISK ({risk_score}%): Svag datakvalitet (få matcher).")
        elif risk_score >= 30: st.info(f"🟡 MEDELRISK ({risk_score}%): Analysen är stabil men formen varierar.")
        else: st.success(f"🟢 LÅG RISK ({risk_score}%): Mycket god datakvalitet.")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Simulerad Sannolikhet", f"{prob}%")
        c2.metric("Rättvist Odds", f"{fair_odds}")
        c3.metric("H2H-faktor", f"x{h2h_mod}")

        st.subheader("Målsannolikhet (Simulerad)")
        dist = pd.DataFrame({
            'Mål': ['0', '1', '2', '3', '4', '5+'],
            'Chans (%)': [round(poisson_prob(h_exp+a_exp, i)*100, 1) for i in range(6)]
        }).set_index('Mål')
        st.bar_chart(dist)

st.sidebar.markdown("---")
if st.sidebar.button("Nollställ & Rensa Cache"):
    st.cache_data.clear()
    st.rerun()
