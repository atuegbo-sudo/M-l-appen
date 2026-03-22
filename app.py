import streamlit as st
import requests
import math
import pandas as pd

# --- KONFIGURATION ---
API_KEY = "210961b3460594ed78d0a659e1ebf79b" # <--- KLISTRA IN DIN NYCKEL HÄR
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}

# --- MATEMATISKA FUNKTIONER ---
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

# --- API-FUNKTIONER ---
@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"{BASE_URL}teams?league={league_id}&season=2023"
    res = requests.get(url, headers=HEADERS).json()
    return {item['team']['name']: item['team']['id'] for item in res['response']}

def get_team_stats(team_id, league_id):
    url = f"{BASE_URL}teams/statistics?league={league_id}&season=2023&team={team_id}"
    res = requests.get(url, headers=HEADERS).json()['response']
    avg_for = float(res['goals']['for']['average']['total'])
    avg_against = float(res['goals']['against']['average']['total'])
    return avg_for, avg_against

# --- APPENS GRÄNSSNITT ---
st.set_page_config(page_title="ProGoal Analyzer v3", layout="wide")
st.title("⚽ ProGoal Analyzer v3.0")

# Sidebar för inställningar
st.sidebar.header("Inställningar")
league_name = st.sidebar.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78}
curr_league = leagues[league_name]

# Hämta lag
teams = get_teams(curr_league)
team_list = sorted(list(teams.keys()))

col1, col2 = st.columns(2)
with col1:
    h_name = st.selectbox("Hemmalag", team_list, index=0)
    h_form = st.slider("Hemma: Snittmål senaste 5 matcherna", 0.0, 5.0, 1.5)
with col2:
    a_name = st.selectbox("Bortalag", team_list, index=1)
    a_form = st.slider("Borta: Snittmål senaste 5 matcherna", 0.0, 5.0, 1.2)

# --- ANALYS ---
if st.button("KÖR DJUPANALYS"):
    with st.spinner('Beräknar sannolikheter...'):
        h_id, a_id = teams[h_name], teams[a_name]
        
        # 1. Hämta stats
        h_avg_f, h_avg_a = get_team_stats(h_id, curr_league)
        a_avg_f, a_avg_a = get_team_stats(a_id, curr_league)
        
        # 2. Viktad anfallsstyrka (70% Form, 30% Säsong) + Injury Factor (standard 0.92)
        h_exp = ((h_form * 0.7) + (h_avg_f * 0.3)) * 0.92
        a_exp = ((a_form * 0.7) + (a_avg_f * 0.3)) * 0.92
        
        # 3. Beräkna sannolikhet för Över 2.5
        prob = calculate_over_25_prob(h_exp, a_exp)
        fair_odds = round(100 / prob, 2) if prob > 0 else 0
        
        # --- VISA RESULTAT ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Sannolikhet Över 2.5", f"{prob}%")
        m2.metric("Ditt Rättvisa Odds", f"{fair_odds}")
        m3.metric("Väntat Målsnitt", f"{round(h_exp + a_exp, 2)}")
        
        # --- GRAF ---
        st.subheader("Målsannolikhet per match")
        dist_data = pd.DataFrame({
            'Mål': ['0', '1', '2', '3', '4', '5+'],
            'Chans (%)': [poisson_prob(h_exp+a_exp, i)*100 for i in range(6)]
        }).set_index('Mål')
        st.bar_chart(dist_data)
        
        # --- LIVE ODDS (Simulerad kontroll) ---
        st.subheader("Value Check")
        market_odds = st.number_input("Ange aktuellt odds från spelbolaget", value=2.0)
        if market_odds > fair_odds:
            st.success(f"🎯 SPELVÄRDE! Din fördel: +{round(((market_odds/fair_odds)-1)*100, 1)}%")
        else:
            st.error("❌ INGET VÄRDE.")

st.sidebar.info("Data hämtas via API-Football. Modellen använder Poisson-fördelning.")
