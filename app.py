import streamlit as st
import requests
import math
import pandas as pd

# --- 1. KONFIGURATION ---
API_KEY = "210961b3460594ed78d0a659e1ebf79b" # <--- DIN NYCKEL HÄR
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-apisports-key': API_KEY,
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# --- 2. MATEMATISKA FUNKTIONER ---
def poisson_prob(lmbda, k):
    if lmbda <= 0: return 0
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)

def calculate_over_25_prob(home_exp, away_exp):
    prob_under_25 = 0
    for h in range(3):
        for a in range(3):
            if h + a < 3:
                prob_under_25 += (poisson_prob(home_exp, h) * poisson_prob(away_exp, a))
    return round((1 - prob_under_25) * 100, 2)

# --- 3. API-FUNKTIONER ---
@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"{BASE_URL}/teams?league={league_id}&season=2023"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        if not data.get('response'): return {}
        return {item['team']['name']: item['team']['id'] for item in data['response']}
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

def get_h2h_multiplier(home_id, away_id):
    url = f"{BASE_URL}/fixtures/headtohead?h2h={home_id}-{away_id}&last=5"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        fixtures = res.get('response', [])
        if not fixtures: return 1.0
        avg_goals = sum(f['goals']['home'] + f['goals']['away'] for f in fixtures) / len(fixtures)
        return 1.15 if avg_goals > 3.0 else (0.90 if avg_goals < 2.0 else 1.0)
    except:
        return 1.0

# --- 4. APPENS GRÄNSSNITT ---
st.set_page_config(page_title="ProGoal Analyzer v3.5", layout="wide")
st.title("⚽ ProGoal Analyzer v3.5 (Advanced)")

st.sidebar.header("Inställningar")
league_name = st.sidebar.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
curr_league = leagues[league_name]

teams = get_teams(curr_league)
if not teams:
    st.warning("⚠️ Ingen data hittades. Kontrollera din API-nyckel och 'Free Plan' status.")
    st.stop()

t_list = sorted(list(teams.keys()))
col1, col2 = st.columns(2)
with col1:
    h_name = st.selectbox("Hemmalag", t_list, index=0)
    h_form = st.slider("Hemma: Målsnitt senaste 5", 0.0, 5.0, 1.8)
with col2:
    a_name = st.selectbox("Bortalag", t_list, index=1)
    a_form = st.slider("Borta: Målsnitt senaste 5", 0.0, 5.0, 1.4)

# --- 5. ANALYS ---
if st.button("KÖR DJUPANALYS"):
    with st.spinner('Analyserar Form, H2H och Statistik...'):
        h_id, a_id = teams[h_name], teams[a_name]
        h_avg_f, h_avg_a = get_team_stats(h_id, curr_league)
        a_avg_f, a_avg_a = get_team_stats(a_id, curr_league)
        h2h_mod = get_h2h_multiplier(h_id, a_id)
        
        # Beräkning: (70% Form + 30% Säsong) * H2H-faktor * Hemmaplansfördel
        h_exp = ((h_form * 0.7) + (h_avg_f * 0.3)) * h2h_mod * 1.05
        a_exp = ((a_form * 0.7) + (a_avg_f * 0.3)) * h2h_mod * 0.95
        
        prob = calculate_over_25_prob(h_exp, a_exp)
        fair_odds = round(100 / prob, 2) if prob > 0 else 0
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Sannolikhet Över 2.5", f"{prob}%")
        m2.metric("Ditt Rättvisa Odds", f"{fair_odds}")
        m3.metric("H2H-påverkan", f"{round((h2h_mod-1)*100, 1)}%")

        st.subheader("Målsannolikhet")
        dist = pd.DataFrame({
            'Mål': ['0', '1', '2', '3', '4', '5+'],
            'Chans (%)': [round(poisson_prob(h_exp+a_exp, i)*100, 1) for i in range(6)]
        }).set_index('Mål')
        st.bar_chart(dist)

st.sidebar.markdown("---")
if st.sidebar.button("Rensa Cache / Reset"):
    st.cache_data.clear()
    st.rerun()
