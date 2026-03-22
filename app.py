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

# --- 2. AVANCERAD ANALYSMOTOR ---
def poisson_prob(lmbda, k):
    if lmbda <= 0: return 0
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)

def run_monte_carlo(home_exp, away_exp, simulations=10000):
    """Simulerar matchen 10 000 gånger för att hitta sannolikheten"""
    home_goals = np.random.poisson(home_exp, simulations)
    away_goals = np.random.poisson(away_exp, simulations)
    total_goals = home_goals + away_goals
    prob_over_25 = np.mean(total_goals > 2.5) * 100
    return round(prob_over_25, 2)

# --- 3. API-FUNKTIONER ---
@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"{BASE_URL}/teams?league={league_id}&season=2023"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if not res.get('response'): return {}
        return {item['team']['name']: item['team']['id'] for item in res['response']}
    except:
        return {}

def get_team_stats(team_id, league_id):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season=2023&team={team_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('response'):
            s = res['response']
            return float(s['goals']['for']['average']['total']), float(s['goals']['against']['average']['total'])
    except:
        pass
    return 1.5, 1.5

def get_h2h_factor(home_id, away_id):
    url = f"{BASE_URL}/fixtures/headtohead?h2h={home_id}-{away_id}&last=5"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        fixtures = res.get('response', [])
        if not fixtures: return 1.0
        avg_g = sum(f['goals']['home'] + f['goals']['away'] for f in fixtures) / len(fixtures)
        return 1.12 if avg_g > 3.0 else (0.88 if avg_g < 2.0 else 1.0)
    except:
        return 1.0

# --- 4. APPENS GRÄNSSNITT ---
st.set_page_config(page_title="GoalPredictor v4 PRO", layout="wide")
st.title("🛡️ GoalPredictor Intelligence v4.0 PRO")

st.sidebar.header("Global Analys")
league_name = st.sidebar.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
curr_league = leagues[league_name]

teams = get_teams(curr_league)
if not teams:
    st.error("⚠️ API-anslutning misslyckades. Kontrollera nyckel/subscription.")
    st.stop()

t_list = sorted(list(teams.keys()))
col1, col2 = st.columns(2)

with col1:
    h_name = st.selectbox("Hemmalag", t_list, index=0)
    h_elo = st.slider("Hemma: Elo Styrka (Relativ)", 1000, 2000, 1500)
    h_form = st.slider("Hemma: Målsnitt (5 senaste)", 0.0, 5.0, 1.8)

with col2:
    a_name = st.selectbox("Bortalag", t_list, index=1)
    a_elo = st.slider("Borta: Elo Styrka (Relativ)", 1000, 2000, 1450)
    a_form = st.slider("Borta: Målsnitt (5 senaste)", 0.0, 5.0, 1.4)

# --- 5. ANALYS-KÖRNING ---
if st.button("KÖR MONTE CARLO SIMULERING"):
    with st.spinner('Simulerar 10 000 matchscenarier...'):
        h_id, a_id = teams[h_name], teams[a_name]
        h_avg_f, h_avg_a = get_team_stats(h_id, curr_league)
        a_avg_f, a_avg_a = get_team_stats(a_id, curr_league)
        h2h_mod = get_h2h_factor(h_id, a_id)
        
        # Beräkning: Elo-differens påverkar baslinjen
        elo_diff = (h_elo - a_elo) / 1000
        
        # Slutgiltig målförväntan (Vägd Form + Elo-justering + H2H)
        h_exp = ((h_form * 0.6) + (h_avg_f * 0.4) + elo_diff) * h2h_mod * 1.05
        a_exp = ((a_form * 0.6) + (a_avg_f * 0.4) - elo_diff) * h2h_mod * 0.95
        
        # Säkra att målförväntan inte blir negativ
        h_exp, a_exp = max(0.1, h_exp), max(0.1, a_exp)
        
        # Simulering
        prob_over = run_monte_carlo(h_exp, a_exp)
        fair_odds = round(100 / prob_over, 2) if prob_over > 0 else 0
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Simulerad Sannolikhet", f"{prob_over}%")
        c2.metric("Rättvist Odds", f"{fair_odds}")
        c3.metric("Förväntat Resultat", f"{round(h_exp)} - {round(a_exp)}")

        # Grafisk fördelning
        st.subheader("Sannolikhet per antal mål (Simulerad)")
        dist = pd.DataFrame({
            'Mål': ['0', '1', '2', '3', '4', '5+'],
            'Chans (%)': [round(poisson_prob(h_exp+a_exp, i)*100, 1) for i in range(6)]
        }).set_index('Mål')
        st.bar_chart(dist)

st.sidebar.markdown("---")
if st.sidebar.button("Rensa Cache"):
    st.cache_data.clear()
    st.rerun()
