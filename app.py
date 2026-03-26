import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# --- 1. PRO-LEVEL STYLING ---
st.set_page_config(page_title="GoalPredictor v150.0 OMNI-ULTRA", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #000000; color: #00ff41; font-family: 'Courier New', monospace; }
    .stMetric { background: #050505; padding: 15px; border: 1px solid #00ff41; border-radius: 5px; }
    .stButton>button { background: #00ff41; color: black; font-weight: 900; width: 100%; height: 3em; border-radius: 0; transition: 0.3s; }
    .stButton>button:hover { background: #ffffff; box-shadow: 0 0 20px #00ff41; }
    .weather-box { background: #080808; padding: 15px; border-left: 5px solid #00ff41; margin-bottom: 20px; font-size: 0.9em; }
    .neural-box { background: #050505; padding: 25px; border: 2px solid #00ff41; text-align: center; margin-bottom: 20px; }
    .stat-card { background: #111; padding: 10px; border: 1px solid #333; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API CONFIG ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 3. CORE ENGINES ---

def get_weather_impact(city):
    """Hämtar väder och beräknar påverkan på mål (xG)"""
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        condition = res['weather'][0]['main'].lower()
        temp = res['main']['temp']
        
        # Logik: Regn/Snö gör bollen svårkontrollerad = färre mål
        multiplier = 1.0
        if any(word in condition for word in ["rain", "drizzle", "snow", "thunderstorm"]):
            multiplier = 0.85 
            desc = f"⚠️ {condition.upper()} DETECTED - xG DEBUFF APPLIED"
        elif temp < 0:
            multiplier = 0.92
            desc = f"❄️ FREEZING TEMP ({temp}°C) - SLIGHT DEBUFF"
        else:
            desc = f"☀️ CLEAR CONDITIONS ({temp}°C) - NO DEBUFF"
        return multiplier, desc
    except:
        return 1.0, "WEATHER DATA OFFLINE - USING NEUTRAL"

@st.cache_data(ttl=3600)
def get_league_data(l_id):
    """Hämtar historisk tabellstatistik"""
    try:
        url = f"{BASE_URL}/standings?league={l_id}&season=2025"
        res = requests.get(url, headers=HEADERS).json()
        return res['response'][0]['league']['standings'][0]
    except: return []

def run_neural_sim(h_exp, a_exp, weather_mod, sims=1000000):
    """
    Huvudmotor: Väger in Hemma/Borta (redan i exp), 
    Väder-mod och kör 1 miljon Monte Carlo-iterationer.
    """
    # Applicera väder på den slutgiltiga förväntningen
    h_final = h_exp * weather_mod
    a_final = a_exp * weather_mod
    
    h_sim = np.random.poisson(max(0.1, h_final), sims)
    a_sim = np.random.poisson(max(0.1, a_final), sims)
    totals = h_sim + a_sim
    
    lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
    results = {}
    for line in lines:
        prob = np.mean(totals > line) * 100
        fair = round(100/prob, 2) if prob > 0 else 99.0
        results[line] = {"prob": round(prob, 1), "fair": fair}
    return results

# --- 4. DASHBOARD UI ---
st.title("🧠 GOALPREDICTOR v150.0 OMNI-ULTRA")
st.caption("Neural Intelligence • Weather Integration • Home/Away Bias • 1M Sims")

# Sidomeny
st.sidebar.header("🕹️ SYSTEM CONTROLS")
LEAGUES = {"Allsvenskan": 113, "Premier League": 39, "La Liga": 140, "Serie A": 135, "Bundesliga": 78}
selected_league = st.sidebar.selectbox("Välj Liga", list(LEAGUES.keys()))
l_id = LEAGUES[selected_league]

standings = get_league_data(l_id)

if standings:
    teams = sorted([t['team']['name'] for t in standings])
    
    col1, col2 = st.columns(2)
    with col1:
        h_team_name = st.selectbox("🏠 Hemmalag (Stats + Fördel)", teams, index=0)
    with col2:
        a_team_name = st.selectbox("✈️ Bortalag (Stats)", teams, index=1)
    
    target_odds = st.sidebar.number_input("Marknadsodds (Över 2.5)", value=2.00, step=0.01)

    if st.button("EXECUTE OMNI-SCAN"):
        with st.spinner("Analyzing weather, H2H, and running 1M simulations..."):
            # 1. Hämta lagens objekt från API-datan
            h_stats = next(t for t in standings if t['team']['name'] == h_team_name)
            a_stats = next(t for t in standings if t['team']['name'] == a_team_name)
            
            # 2. Väder-analys (baserat på hemmastad)
            w_mod, w_desc = get_weather_impact(h_team_name)
            
            # 3. Beräkna xG baserat på HISTORIK (Mål/Matcher)
            # Vi lägger till 10% bonus för hemmalag och drar av 5% för bortalag (Hemmafördel)
            h_played = h_stats['all']['played'] or 1
            a_played = a_stats['all']['played'] or 1
            
            h_avg = (h_stats['all']['goals']['for'] / h_played) * 1.10
            a_avg = (a_stats['all']['goals']['for'] / a_played) * 0.95
            
            # 4. Kör den neurala simuleringen
            probs = run_neural_sim(h_avg, a_avg, w_mod)
            
            # --- PRESENTATION ---
            st.markdown(f"<div class='weather-box'>{w_desc}</div>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='neural-box'><h2>{h_team_name} vs {a_team_name}</h2>"
                        f"Simulerat målsnitt: {round((h_avg + a_avg) * w_mod, 2)} mål/match</div>", unsafe_allow_html=True)
            
            # Visning av alla mållinjer
            st.subheader("📊 Neural Probability Spectrum")
            res_cols = st.columns(6)
            lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
            for i, line in enumerate(lines):
                with res_cols[i]:
                    st.metric(f"Över {line}", f"{probs[line]['prob']}%")
                    st.caption(f"Fair: {probs[line]['fair']}")
            
            st.divider()
            
            # 5. VALUE ANALYSIS (Kelly Criterion)
            prob_25 = probs[2.5]['prob'] / 100
            edge = (prob_25 * target_odds) - 1
            
            val_c1, val_c2, val_c3 = st.columns(3)
            with val_c1:
                st.metric("Neural Edge", f"{round(edge*100, 2)}%", delta=f"{round(edge*100, 1)}%")
            with val_c2:
                kelly = max(0, (edge / (target_odds - 1)) * 0.05) # 5% Kelly-fraktion för säkerhet
                st.metric("Rek. Insats (Kelly)", f"{round(kelly*100, 2)}%")
            with val_c3:
                status = "✅ VALUE DETECTED" if edge > 0 else "❌ NO VALUE"
                st.subheader(status)

            # 6. HISTORISK TABELL-JÄMFÖRELSE
            with st.expander("Se Historisk Statistik (Säsong 2025)"):
                st.write(f"**{h_team_name}**: {h_stats['all']['goals']['for']} gjorda / {h_stats['all']['goals']['against']} insläppta")
                st.write(f"**{a_team_name}**: {a_stats['all']['goals']['for']} gjorda / {a_stats['all']['goals']['against']} insläppta")

else:
    st.error("Kunde inte hämta data. Kontrollera API-nycklar eller välj en annan liga.")

# --- FOOTER ---
st.sidebar.markdown("---")
st.sidebar.info("Systemet väger in hemmaplansfördel (+10% xG) och bortaplans-debuff (-5% xG) automatiskt baserat på lagens placering i valet.")
