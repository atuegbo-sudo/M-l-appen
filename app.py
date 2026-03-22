import streamlit as st
import requests
import math
import pandas as pd
import numpy as np

# --- 1. KONFIGURATION ---
FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" # <--- SKRIV IN DIN NYCKEL HÄR

# Enkel mapping för städer (kan utökas eller hämtas via API)
CITY_MAP = {
    "Arsenal": "London", "Manchester City": "Manchester", "Liverpool": "Liverpool",
    "Real Madrid": "Madrid", "Barcelona": "Barcelona", "Bayern Munich": "Munich",
    "Malmö FF": "Malmo", "AIK": "Stockholm", "Hammarby": "Stockholm", "IFK Göteborg": "Gothenburg"
}

# --- 2. VÄDER-FUNKTION ---
def get_live_weather(city):
    if not city: return None
    url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url, timeout=5).json()
        return {
            "temp": res['main']['temp'],
            "wind": res['wind']['speed'],
            "condition": res['weather'][0]['main'],
            "city": city
        }
    except:
        return None

def get_weather_modifier(w_data):
    if not w_data: return 1.0
    mod = 1.0
    if w_data['temp'] < 5: mod *= 0.92
    if w_data['wind'] > 8: mod *= 0.90 # m/s
    if w_data['condition'] in ["Rain", "Drizzle"]: mod *= 1.05
    if w_data['condition'] == "Snow": mod *= 0.85
    return mod

# --- 3. GRÄNSSNITT ---
st.set_page_config(page_title="GoalPredictor v5.5 Live", layout="wide")
st.title("🛡️ GoalPredictor Intelligence v5.5 (LIVE WEATHER)")

# ... (Här behåller du get_teams och get_detailed_stats från tidigare kod) ...

# --- VAL AV LAG ---
col1, col2 = st.columns(2)
with col1:
    h_name = st.selectbox("Hemmalag", t_list)
    # Hämta väder automatiskt baserat på vald stad
    city = CITY_MAP.get(h_name, "London") # Default till London om staden saknas
    weather = get_live_weather(city)
    
    if weather:
        st.write(f"🌡️ **Väder i {city}:** {weather['temp']}°C, {weather['condition']}, {weather['wind']} m/s")
    else:
        st.warning("Kunde inte hämta live-väder.")

# --- BERÄKNING ---
if st.button("KÖR LIVE-ANALYS"):
    w_mod = get_weather_modifier(weather)
    h_adv = 1.20 # Standard hemmafördel
    
    # Här återanvänder vi din beräkningslogik men med w_mod från API:et
    # ... (Samma beräkningar som i förra svaret) ...
    
    st.success(f"Analys slutförd med live-data från {city}!")
    st.metric("Vädrets påverkan", f"{round((w_mod-1)*100, 1)}%")
