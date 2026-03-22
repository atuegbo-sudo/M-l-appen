import streamlit as st
import requests
import math
import pandas as pd

# --- 1. KONFIGURATION ---
# Klistra in din nyckel här under:
API_KEY = "DIN_API_NYCKEL_HÄR"

# Vi använder dubbla headers för att vara säkra på att anslutningen godkänns
HEADERS = {
    'x-apisports-key': API_KEY,
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}
BASE_URL = "https://v3.football.api-sports.io"

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

# --- 3. API-FUNKTIONER MED FELHANTERING ---
@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"{BASE_URL}/teams?league={league_id}&season=2023"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        
        # Om API:et skickar tillbaka ett felmeddelande
        if data.get('errors'):
            st.error(f"API-fel: {data['errors']}")
            return {}
            
        if not data.get('response'):
            return {}
            
        return {item['team']['name']: item['team']['id'] for item in data['response']}
    except Exception as e:
        st.error(f"Anslutningsfel: {e}")
        return {}

def get_team_stats(team_id, league_id):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season=2023&team={team_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('response'):
            stats = res['response']
            avg_for = float(stats['goals']['for']['average']['total'])
            avg_against = float(stats['goals']['against']['average']['total'])
            return avg_for, avg_against
    except:
        pass
    return 1.5, 1.5 # Standardvärde om data saknas

# --- 4. APPENS GRÄNSSNITT ---
st.set_page_config(page_title="ProGoal Analyzer v3", layout="wide")
st.title("⚽ ProGoal Analyzer v3.0")

# Sidebar
st.sidebar.header("Inställningar")
league_name = st.sidebar.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
curr_league = leagues[league_name]

# Hämta lag
teams = get_teams(curr_league)

if not teams:
    st.warning("⚠️ Inga lag hittades. Kontrollera att din API-nyckel är aktiv och att du har 'Free Plan' på dashboard.api-football.com")
    st.info("Tips: Klicka på 'Clear cache' i menyn uppe till höger om du precis aktiverat nyckeln.")
    st.stop()

team_list = sorted(list(teams.keys()))

col1, col2 = st.columns(2)
with col1:
    h_name = st.selectbox("Hemmalag", team_list, index=0)
    h_form = st.slider("Hemma: Målsnitt senaste 5", 0.0, 5.0, 1.5)
with col2:
    a_name = st.selectbox("Bortalag", team_list, index=1)
    a_form = st.slider("Borta: Målsnitt senaste 5", 0.0, 5.0, 1.2)

# --- 5. ANALYS ---
if st.button("KÖR DJUPANALYS"):
    with st.spinner('Hämtar statistik och beräknar...'):
        h_id, a_id = teams[h_name], teams[a_name]
        h_avg_f, h_avg_a = get_team_stats(h_id, curr_league)
        a_avg_f, a_avg_a = get_team_stats(a_id, curr_league)
        
        # Viktning (70% Form, 30% Säsong) - Enkel Pro-modell
        h_exp = ((h_form * 0.7) + (h_avg_f * 0.3)) * 0.95
        a_exp = ((a_form * 0.7) + (a_avg_f * 0.3)) * 0.95
        
        prob = calculate_over_25_prob(h_exp, a_exp)
        fair_odds = round(100 / prob, 2) if prob > 0 else 0
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Sannolikhet Över 2.5", f"{prob}%")
        m2.metric("Ditt Rättvisa Odds", f"{fair_odds}")
        m3.metric("Väntat Målsnitt", f"{round(h_exp + a_exp, 2)}")
        
        # Grafisk visualisering
        st.subheader("Målsannolikhet i matchen")
        dist_data = pd.DataFrame({
            'Antal Mål': ['0', '1', '2', '3', '4', '5+'],
            'Chans (%)': [round(poisson_prob(h_exp+a_exp, i)*100, 1) for i in range(6)]
        }).set_index('Antal Mål')
        st.bar_chart(dist_data)

st.sidebar.markdown("---")
st.sidebar.write("🟢 **Status:** API-nyckel inlagd")
