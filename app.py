import streamlit as st
import requests
import math
import pandas as pd
import numpy as np

# --- 1. KONFIGURATION ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b" 
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" # <--- Valfri för live-väder

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}

# --- 2. AUTOMATISERINGSMOTOR (ELO & FORM) ---

@st.cache_data(ttl=3600)
def get_league_standings(league_id):
    """Hämtar hela tabellen för att kunna räkna ut Elo för alla lag"""
    url = f"{BASE_URL}/standings?league={league_id}&season=2024"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        return res['response'][0]['league']['standings'][0]
    except: return []

def calculate_auto_stats(team_name, standings):
    """Räknar ut Elo och Form baserat på tabell-data"""
    # Standardvärden om data saknas
    elo = 1500
    form_score = 5.0
    avg_goals = 1.3
    
    for team in standings:
        if team['team']['name'] == team_name:
            # ELO-ALGORITM: Bas (1200) + Poäng-vikt + Målskillnad-bonus - Rank-straff
            points = team['points']
            rank = team['rank']
            gd = team['goalsDiff']
            elo = 1200 + (points * 6) + (gd * 2) - (rank * 3)
            
            # FORM-ALGORITM: Baseras på de 5 senaste (W=2, D=1, L=0)
            form_str = team['form'] if team['form'] else "DDDDD"
            last_5 = form_str[-5:]
            form_score = sum([2 if c == 'W' else 1 if c == 'D' else 0 for c in last_5])
            
            # SNITTMÅL: Faktiska gjorda mål / spelade matcher
            played = team['all']['played']
            if played > 0:
                avg_goals = team['all']['goals']['for'] / played
            break
            
    return int(elo), float(form_score), round(avg_goals, 2)

# --- 3. VÄDER & MATEMATIK ---
def get_live_weather(city):
    # Dummy-väder om nyckel saknas, annars API-anrop
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL_HÄR":
        return {"temp": 12, "wind": 4, "condition": "Cloudy"}
    url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url, timeout=5).json()
        return {"temp": res['main']['temp'], "wind": res['wind']['speed'], "condition": res['weather']['main']}
    except: return {"temp": 15, "wind": 2, "condition": "Clear"}

# --- 4. GRÄNSSNITT ---
st.set_page_config(page_title="GoalPredictor AUTO v6.0", layout="wide")
st.title("🛡️ GoalPredictor v6.0 (100% Automatiserad)")

# Liga-val
league_name = st.sidebar.selectbox("Välj Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
curr_league = leagues[league_name]

# Hämta data automatiskt
with st.spinner('Hämtar senaste tabellen och formen...'):
    standings = get_league_standings(curr_league)
    t_list = [t['team']['name'] for t in standings]

if t_list:
    col1, col2 = st.columns(2)
    
    with col1:
        h_name = st.selectbox("Hemmalag", t_list, index=0)
        h_elo, h_form, h_avg = calculate_auto_stats(h_name, standings)
        # Visa den automatisk hämtade datan
        st.metric("Automatisk Elo (Hemma)", h_elo)
        st.caption(f"Form (5 senaste): **{h_form}/10** | Snittmål: **{h_avg}**")

    with col2:
        a_name = st.selectbox("Bortalag", t_list, index=1 if len(t_list)>1 else 0)
        a_elo, a_form, a_avg = calculate_auto_stats(a_name, standings)
        # Visa den automatisk hämtade datan
        st.metric("Automatisk Elo (Borta)", a_elo)
        st.caption(f"Form (5 senaste): **{a_form}/10** | Snittmål: **{a_avg}**")

    # --- KÖR ANALYS ---
    if st.button("KÖR AUTOMATISK ANALYS"):
        # Beräkningslogik
        elo_diff = (h_elo - a_elo) / 1000
        weather = get_live_weather("London") # Kan bytas mot city-mapping
        
        # Formvikt (60%) + Målsnitt (40%) + Elo-skillnad + Hemmafördel
        h_exp = ((h_avg * 0.4) + (h_form/5 * 0.6) + elo_diff) * 1.20
        a_exp = ((a_avg * 0.4) + (a_form/5 * 0.6) - elo_diff)
        
        # Monte Carlo Simulering
        h_sim = np.random.poisson(max(0.1, h_exp), 10000)
        a_sim = np.random.poisson(max(0.1, a_exp), 10000)
        prob_over_25 = np.mean((h_sim + a_sim) > 2.5) * 100
        
        st.divider()
        res1, res2, res3 = st.columns(3)
        res1.metric("Sannolikhet > 2.5 mål", f"{round(prob_over_25, 1)}%")
        res2.metric("Förväntade mål (H)", round(h_exp, 2))
        res3.metric("Förväntade mål (B)", round(a_exp, 2))
        
        # Visualisering
        st.subheader("Målfördelning (Sannolikhet)")
        chart_data = pd.DataFrame({
            'Hemma (%)': [round((np.sum(h_sim == i)/10000)*100, 1) for i in range(6)],
            'Borta (%)': [round((np.sum(a_sim == i)/10000)*100, 1) for i in range(6)]
        })
        st.bar_chart(chart_data)
else:
    st.error("Kunde inte hämta data från API:et. Kontrollera din nyckel.")

st.sidebar.info("Data uppdateras varje timme via API-Football.")
