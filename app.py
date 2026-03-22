import streamlit as st
import requests
import math
import pandas as pd
import numpy as np

# --- 1. KONFIGURATION ---
# Ersätt med dina faktiska nycklar
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b" 
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-apisports-key': FOOTBALL_API_KEY,
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# Mapping för att väder-API ska hitta rätt stad baserat på hemmalag
CITY_MAP = {
    "Arsenal": "London", "Manchester City": "Manchester", "Liverpool": "Liverpool",
    "Chelsea": "London", "Tottenham": "London", "Manchester United": "Manchester",
    "Real Madrid": "Madrid", "Barcelona": "Barcelona", "Bayern Munich": "Munich",
    "Malmö FF": "Malmo", "AIK": "Stockholm", "Hammarby": "Stockholm", 
    "IFK Göteborg": "Gothenburg", "BK Häcken": "Gothenburg", "Djurgården": "Stockholm"
}

# --- 2. HJÄLPFUNKTIONER (MATEMATIK & VÄDER) ---

def poisson_prob(lmbda, k):
    if lmbda <= 0: return 0
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)

def run_monte_carlo(home_exp, away_exp, simulations=10000):
    home_goals = np.random.poisson(home_exp, simulations)
    away_goals = np.random.poisson(away_exp, simulations)
    prob_over_25 = np.mean((home_goals + away_goals) > 2.5) * 100
    return round(prob_over_25, 2)

def get_live_weather(city):
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL_HÄR":
        return {"temp": 15, "wind": 3, "condition": "Clear", "city": city, "mock": True}
    
    url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url, timeout=5).json()
        return {
            "temp": res['main']['temp'],
            "wind": res['wind']['speed'],
            "condition": res['weather'][0]['main'],
            "city": city,
            "mock": False
        }
    except:
        return None

def get_weather_modifier(w_data):
    if not w_data: return 1.0
    mod = 1.0
    if w_data['temp'] < 5: mod *= 0.92
    if w_data['wind'] > 8: mod *= 0.88 # m/s påverkan
    if w_data['condition'] in ["Rain", "Drizzle"]: mod *= 1.05
    if w_data['condition'] == "Snow": mod *= 0.85
    return mod

# --- 3. API-FUNKTIONER (FOTBOLL) ---

@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"{BASE_URL}/teams?league={league_id}&season=2024"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('response'):
            return {item['team']['name']: item['team']['id'] for item in res['response']}
        return {}
    except:
        return {}

def get_detailed_stats(team_id, league_id):
    url = f"{BASE_URL}/teams/statistics?league={league_id}&season=2024&team={team_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()['response']
        avg_f = float(res['goals']['for']['average']['total'])
        played = int(res['fixtures']['played']['total'])
        return avg_f, played
    except:
        return 1.2, 0 # Defaultvärde om data saknas

# --- 4. GRÄNSSNITT ---

st.set_page_config(page_title="GoalPredictor v5.5 PRO", layout="wide")
st.title("🛡️ GoalPredictor Intelligence v5.5 (Live Weather & Venue)")

# Sidomeny för Liga
st.sidebar.header("Global Analys")
league_name = st.sidebar.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
curr_league = leagues[league_name]

# Hämta lagdata tidigt för att undvika NameError
teams_dict = get_teams(curr_league)
t_list = sorted(list(teams_dict.keys())) if teams_dict else []

if not t_list:
    st.error("Kunde inte ladda lag. Kontrollera din Football API-nyckel.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    h_name = st.selectbox("Hemmalag (Hemmafördel tillämpas)", t_list, index=0)
    h_elo = st.slider("Hemma: Elo Styrka", 1000, 2000, 1500)
    h_form = st.slider("Hemma: Form (0-10)", 0.0, 10.0, 6.0)
    
    # Väder-sektion
    city = CITY_MAP.get(h_name, "London") 
    weather = get_live_weather(city)
    if weather:
        icon = "🌡️" if not weather.get("mock") else "🧪 (Simulerat)"
        st.info(f"{icon} **Väder i {city}:** {weather['temp']}°C, {weather['condition']}, {weather['wind']} m/s")

with col2:
    a_name = st.selectbox("Bortalag", t_list, index=1 if len(t_list) > 1 else 0)
    a_elo = st.slider("Borta: Elo Styrka", 1000, 2000, 1450)
    a_form = st.slider("Borta: Form (0-10)", 0.0, 10.0, 5.0)

# --- 5. ANALYS-KÖRNING ---

if st.button("STARTA LIVE-SIMULERING"):
    with st.spinner('Beräknar xG, väderpåverkan och hemmaplansfördel...'):
        h_id, a_id = teams_dict[h_name], teams_dict[a_name]
        h_avg, h_played = get_detailed_stats(h_id, curr_league)
        a_avg, a_played = get_detailed_stats(a_id, curr_league)
        
        # Logik-faktorer
        weather_mod = get_weather_modifier(weather)
        home_adv = 1.20 # Hemmalag gör statistiskt ca 20% fler mål
        
        elo_diff = (h_elo - a_elo) / 1000
        
        # Beräkning av Expected Goals (xG)
        h_exp = ((h_avg * 0.4) + (h_form/5 * 0.6) + elo_diff) * home_adv * weather_mod
        a_exp = ((a_avg * 0.4) + (a_form/5 * 0.6) - elo_diff) * weather_mod
        
        h_exp, a_exp = max(0.1, h_exp), max(0.1, a_exp)
        
        # Sannolikheter
        prob_over_25 = run_monte_carlo(h_exp, a_exp)
        fair_odds = round(100 / prob_over_25, 2) if prob_over_25 > 0 else "N/A"
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Över 2.5 Mål", f"{prob_over_25}%")
        m2.metric("Rättvist Odds", f"{fair_odds}")
        m3.metric("Väder-faktor", f"x{weather_mod:.2f}")
        
        # Visualisering
        st.subheader("Målsannolikhet per lag")
        dist_data = pd.DataFrame({
            'Mål': [str(i) for i in range(6)],
            'Hemma (%)': [round(poisson_prob(h_exp, i)*100, 1) for i in range(6)],
            'Borta (%)': [round(poisson_prob(a_exp, i)*100, 1) for i in range(6)]
        }).set_index('Mål')
        st.bar_chart(dist_data)

st.sidebar.markdown("---")
if st.sidebar.button("Rensa Cache"):
    st.cache_data.clear()
    st.rerun()
