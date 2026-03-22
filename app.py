import streamlit as st
import requests
import math

# --- KONFIGURATION ---
API_KEY = "DIN_API_NYCKEL_HÄR"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}

# --- MATEMATISKA FUNKTIONER ---
def poisson_prob(lmbda, k):
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)

def calculate_over_25(home_exp, away_exp):
    prob_under_25 = 0
    for h in range(3):
        for a in range(3):
            if h + a < 3:
                prob_under_25 += (poisson_prob(home_exp, h) * poisson_prob(away_exp, a))
    return round((1 - prob_under_25) * 100, 2)

# --- DATA-FUNKTIONER ---
def get_stats(team_id, league_id=39, season=2023):
    url = f"{BASE_URL}teams/statistics?league={league_id}&season={season}&team={team_id}"
    res = requests.get(url, headers=HEADERS).json()['response']
    # Snittmål (Säsong)
    avg_for = float(res['goals']['for']['average']['total'])
    avg_against = float(res['goals']['against']['average']['total'])
    return avg_for, avg_against

def get_injury_factor(team_id, fixture_id):
    # Simulerad logik för skade-debuff (API-anrop för skador)
    url = f"{BASE_URL}injuries?fixture={fixture_id}&team={team_id}"
    # Om inga skador hittas eller API-gräns nås, returnera 1.0 (ingen sänkning)
    return 0.92 # Exempel: Sänker anfall med 8% pga skador i demon

# --- APPENS GRÄNSSNITT ---
st.set_page_config(page_title="GoalPredictor Pro v2", page_icon="⚽")
st.title("⚽ GoalPredictor Pro v2")
st.markdown("Analys baserad på **Poisson-fördelning**, **Form** och **Skador**.")

col1, col2 = st.columns(2)

with col1:
    st.header("Hemmalag")
    h_id = st.number_input("Team ID (Hemma)", value=42) # Arsenal
    h_season_avg, h_season_def = 2.1, 0.9 # Demo-värden
    h_form_avg = st.slider("Hemma: Snittmål senaste 5 matcherna", 0.0, 5.0, 2.5)

with col2:
    st.header("Bortalag")
    a_id = st.number_input("Team ID (Borta)", value=40) # Liverpool
    a_season_avg, a_season_def = 1.9, 1.1 # Demo-värden
    a_form_avg = st.slider("Borta: Snittmål senaste 5 matcherna", 0.0, 5.0, 1.8)

# --- ANALYS-LOGIK ---
if st.button("BERÄKNA SPELVÄRDE"):
    # Viktning: 70% Form, 30% Säsong
    h_attack = (h_form_avg * 0.7) + (h_season_avg * 0.3)
    a_attack = (a_form_avg * 0.7) + (a_season_avg * 0.3)
    
    # Applicera Skade-faktor
    h_final_exp = h_attack * get_injury_factor(h_id, 123)
    a_final_exp = a_attack * get_injury_factor(a_id, 123)
    
    # Beräkna sannolikhet
    prob = calculate_over_25(h_final_exp, a_final_exp)
    fair_odds = round(100 / prob, 2)
    
    # Visa resultat
    st.divider()
    st.subheader(f"Sannolikhet för Över 2.5 mål: {prob}%")
    st.write(f"Ditt framtagna 'Rättvisa Odds': **{fair_odds}**")
    
    market_odds = st.number_input("Vad är spelbolagets odds?", value=1.85)
    
    if market_odds > fair_odds:
        st.success(f"✅ SPELVÄRDE HITTAT! (Värde: +{round((market_odds/fair_odds - 1)*100, 1)}%)")
    else:
        st.error("❌ INGET VÄRDE - Avstå spel.")
