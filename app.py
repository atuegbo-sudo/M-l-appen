import streamlit as st
import requests
import math
import pandas as pd
import numpy as np

# --- 1. KONFIGURATION ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b" 
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}

CITY_MAP = {
    "Arsenal": "London", "Manchester City": "Manchester", "Liverpool": "Liverpool",
    "Real Madrid": "Madrid", "Barcelona": "Barcelona", "Malmö FF": "Malmo",
    "AIK": "Stockholm", "Hammarby": "Stockholm", "IFK Göteborg": "Gothenburg"
}

# --- 2. AUTOMATISERINGS-FUNKTIONER (REALTID) ---

@st.cache_data(ttl=3600)
def get_auto_data(team_id, league_id):
    """Hämtar form och beräknar en 'Elo-styrka' baserat på tabellen"""
    # 1. Hämta Form (senaste 5)
    url_stats = f"{BASE_URL}/teams/statistics?league={league_id}&season=2024&team={team_id}"
    form_score = 5.0
    avg_goals = 1.2
    try:
        res = requests.get(url_stats, headers=HEADERS).json()['response']
        form_str = res['form'][-5:] if res.get('form') else "WDLWD"
        # Omvandla WDL till poäng (W=2, D=1, L=0) -> Max 10 poäng
        form_score = sum([2 if char == 'W' else 1 if char == 'D' else 0 for char in form_str])
        avg_goals = float(res['goals']['for']['average']['total'])
    except: pass

    # 2. Hämta Tabellplacering för 'Elo'
    url_standings = f"{BASE_URL}/standings?league={league_id}&season=2024"
    elo_estimate = 1500
    try:
        standings = requests.get(url_standings, headers=HEADERS).json()['response'][0]['league']['standings'][0]
        for team in standings:
            if team['team']['id'] == team_id:
                # Enkel Elo-kalkyl: 1000 bas + (poäng * 10) - (placering * 5)
                elo_estimate = 1200 + (team['points'] * 5) - (team['rank'] * 2)
                break
    except: pass

    return round(float(form_score), 1), int(elo_estimate), avg_goals

# --- 3. VÄDER & POISSON ---
def get_live_weather(city):
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL_HÄR":
        return {"temp": 15, "wind": 3, "condition": "Clear", "city": city, "mock": True}
    url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url, timeout=5).json()
        return {"temp": res['main']['temp'], "wind": res['wind']['speed'], "condition": res['weather']['main'], "city": city, "mock": False}
    except: return None

def get_weather_modifier(w_data):
    if not w_data: return 1.0
    m = 1.0
    if w_data['temp'] < 5: m *= 0.92
    if w_data['wind'] > 8: m *= 0.88
    if w_data['condition'] in ["Rain", "Drizzle"]: m *= 1.05
    return m

def poisson_prob(lmbda, k):
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k) if lmbda > 0 else 0

# --- 4. GRÄNSSNITT ---
st.set_page_config(page_title="GoalPredictor AUTO v6.0", layout="wide")
st.title("🛡️ GoalPredictor v6.0 (Full Auto Mode)")

# Ladda liga och lag
league_name = st.sidebar.selectbox("Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
curr_league = leagues[league_name]

@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"{BASE_URL}/teams?league={league_id}&season=2024"
    res = requests.get(url, headers=HEADERS).json()
    return {item['team']['name']: item['team']['id'] for item in res['response']} if res.get('response') else {}

teams_dict = get_teams(curr_league)
t_list = sorted(list(teams_dict.keys()))

if t_list:
    col1, col2 = st.columns(2)
    
    with col1:
        h_name = st.selectbox("Hemmalag", t_list, index=0)
        h_id = teams_dict[h_name]
        # AUTOMATISK HÄMTNING
        h_form, h_elo, h_avg = get_auto_data(h_id, curr_league)
        st.caption(f"🤖 **Auto-analys:** Elo: {h_elo} | Form: {h_form}/10")
        
        city = CITY_MAP.get(h_name, "London")
        weather = get_live_weather(city)
        if weather: st.info(f"🌤️ {city}: {weather['temp']}°C, {weather['condition']}")

    with col2:
        a_name = st.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)
        a_id = teams_dict[a_name]
        # AUTOMATISK HÄMTNING
        a_form, a_elo, a_avg = get_auto_data(a_id, curr_league)
        st.caption(f"🤖 **Auto-analys:** Elo: {a_elo} | Form: {a_form}/10")

    if st.button("KÖR FULLSTÄNDIG AUTOMATISK ANALYS"):
        w_mod = get_weather_modifier(weather)
        elo_diff = (h_elo - a_elo) / 1000
        
        # Beräkning med automatisk data
        h_exp = ((h_avg * 0.4) + (h_form/5 * 0.6) + elo_diff) * 1.20 * w_mod
        a_exp = ((a_avg * 0.4) + (a_form/5 * 0.6) - elo_diff) * w_mod
        
        # Monte Carlo
        h_g = np.random.poisson(max(0.1, h_exp), 10000)
        a_g = np.random.poisson(max(0.1, a_exp), 10000)
        prob = np.mean((h_g + a_g) > 2.5) * 100
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Sannolikhet > 2.5 mål", f"{round(prob, 1)}%")
        c2.metric("Beräknad xG Hemma", round(h_exp, 2))
        c3.metric("Beräknad xG Borta", round(a_exp, 2))
        
        st.bar_chart(pd.DataFrame({
            'Hemma': [round(poisson_prob(h_exp, i)*100, 1) for i in range(6)],
            'Borta': [round(poisson_prob(a_exp, i)*100, 1) for i in range(6)]
        }))
