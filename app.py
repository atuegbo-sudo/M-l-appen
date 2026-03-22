import streamlit as st
import requests
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- 1. KONFIGURATION & STYLING ---
st.set_page_config(page_title="GoalPredictor v12.0 INFINITE", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050a0f; color: #e0e0e0; }
    .stMetric { background-color: #101a24; padding: 15px; border-radius: 10px; border: 1px solid #1f2937; }
    .stButton>button { background: linear-gradient(90deg, #00ff41 0%, #008f11 100%); color: black; font-weight: bold; width: 100%; border: none; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

FOOTBALL_API_KEY = "210961b3460594ed78d0a659e1ebf79b"
WEATHER_API_KEY = "7bd889f1cb9cec6e42e15fc106125abe" 
HEADERS = {'x-apisports-key': FOOTBALL_API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. AVANCERADE DATA-MOTORER ---

@st.cache_data(ttl=60)
def get_live_and_today(league_id):
    today = datetime.now().strftime('%Y-%m-%d')
    live = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "live": "all"}).json().get('response', [])
    todays = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "date": today}).json().get('response', [])
    return live, todays

@st.cache_data(ttl=3600)
def get_standings_safe(league_id):
    res = requests.get(f"{BASE_URL}/standings?league={league_id}&season=2024", headers=HEADERS).json()
    if 'response' in res and len(res['response']) > 0:
        data = res['response']['league']['standings']
        return data if isinstance(data, list) else data
    return []

def get_h2h_factor(h_id, a_id):
    res = requests.get(f"{BASE_URL}/fixtures/headtohead", headers=HEADERS, params={"h2h": f"{h_id}-{a_id}", "last": 5}).json().get('response', [])
    if not res: return 1.0
    avg = sum(f['goals']['home'] + f['goals']['away'] for f in res) / len(res)
    return 1.15 if avg > 3.0 else (0.85 if avg < 2.0 else 1.0)

def get_fatigue(team_id):
    res = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": team_id, "last": 1, "status": "FT"}).json().get('response', [])
    if not res: return 1.0
    last_date = datetime.strptime(res[0]['fixture']['date'][:10], '%Y-%m-%d')
    days_diff = (datetime.now() - last_date).days
    return 0.92 if days_diff < 4 else 1.0

def get_weather_impact(city):
    if WEATHER_API_KEY == "DIN_OPENWEATHER_NYCKEL": return {"temp": 12, "wind": 4, "mod": 1.0}
    try:
        url = f"http://api.openweathermap.org{city}&appid={WEATHER_API_KEY}&units=metric"
        r = requests.get(url, timeout=3).json()
        mod = 0.88 if r['wind']['speed'] > 8 else 1.0
        return {"temp": r['main']['temp'], "wind": r['wind']['speed'], "mod": mod}
    except: return {"temp": 15, "wind": 2, "mod": 1.0}

def poisson_prob(lmbda, k):
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k) if lmbda > 0 else 0

# --- 3. THE NEURAL ARCHIVE ENGINE ---

def run_archive_sim(h_st, a_st, h2h_mod, w_mod, h_fatigue, a_fatigue):
    h_avg = h_st['all']['goals']['for'] / h_st['all']['played']
    a_def = a_st['all']['goals']['against'] / a_st['all']['played']
    a_avg = a_st['all']['goals']['for'] / a_st['all']['played']
    h_def = h_st['all']['goals']['against'] / h_st['all']['played']
    
    # Komplett xG-beräkning (Alla faktorer)
    h_xg = (h_avg * (a_def / 1.2)) * 1.18 * h2h_mod * w_mod * h_fatigue
    a_xg = (a_avg * (h_def / 1.2)) * h2h_mod * w_mod * a_fatigue
    
    sims = 150000
    h_s = np.random.poisson(max(0.1, h_xg), sims)
    a_s = np.random.poisson(max(0.1, a_xg), sims)
    
    return {
        "o25": np.mean((h_s + a_s) > 2.5) * 100,
        "btts": np.mean((h_s > 0) & (a_s > 0)) * 100,
        "h_p": np.mean(h_s > a_s) * 100, "d_p": np.mean(h_s == a_s) * 100, "a_p": np.mean(h_s < a_s) * 100,
        "h_xg": h_xg, "a_xg": a_xg
    }

# --- 4. HUVUD-APP ---

st.title("🛡️ GoalPredictor v12.0 INFINITE")

with st.sidebar:
    st.header("⚙️ Inställningar")
    bankroll = st.number_input("Din Kassa (kr)", value=10000)
    odds_o25 = st.number_input("Odds Över 2.5", value=1.95)
    league_name = st.selectbox("Liga", ["Premier League", "Allsvenskan", "Serie A", "Bundesliga", "La Liga"])
    leagues = {"Premier League": 39, "Allsvenskan": 113, "Serie A": 135, "Bundesliga": 78, "La Liga": 140}
    curr_league = leagues[league_name]

tab1, tab2 = st.tabs(["🔴 MATCH-CENTER & LIVE", "🧠 MANUELL DJUPANALYS"])

live_data, today_data = get_live_and_today(curr_league)
standings = get_standings_safe(curr_league)

with tab1:
    # Live Dashboard
    if live_data:
        st.subheader("⏱️ Live Just Nu")
        for m in live_data:
            st.success(f"**{m['teams']['home']['name']} {m['goals']['home']} - {m['goals']['away']} {m['teams']['away']['name']}** ({m['fixture']['status']['elapsed']}')")
    
    # Match-väljare med väder
    if standings:
        st.subheader("📅 Välj Match för Komplett Analys")
        fixtures = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": curr_league, "season": 2024, "next": 8}).json().get('response', [])
        
        for f in fixtures:
            h_n, a_n = f['teams']['home']['name'], f['teams']['away']['name']
            city = f['fixture']['venue']['city'] if f['fixture']['venue']['city'] else h_n
            w = get_weather_impact(city)
            
            with st.container():
                c_inf, c_w, c_btn = st.columns([2, 1, 1])
                c_inf.write(f"**{h_n}** vs **{a_n}**")
                c_w.write(f"🌤️ {w['temp']}°C | {w['wind']} m/s")
                
                if c_btn.button("ANALYS", key=f"btn_{f['fixture']['id']}"):
                    h_st = next(t for t in standings if t['team']['name'] == h_n)
                    a_st = next(t for t in standings if t['team']['name'] == a_n)
                    
                    # Kör alla historiska analys-steg
                    h2h = get_h2h_factor(f['teams']['home']['id'], f['teams']['away']['id'])
                    h_fat = get_fatigue(f['teams']['home']['id'])
                    a_fat = get_fatigue(f['teams']['away']['id'])
                    
                    res = run_archive_sim(h_st, a_st, h2h, w['mod'], h_fat, a_fat)
                    
                    st.session_state.full_scan = {
                        "match": f"{h_n}-{a_n}", "data": res, "h2h": h2h, "w": w, "h_fat": h_fat, "a_fat": a_fat
                    }

    if 'full_scan' in st.session_state:
        s = st.session_state.full_scan
        st.divider()
        st.markdown(f"### 📊 Slutgiltig Analys: {s['match']}")
        
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Över 2.5%", f"{round(s['data']['o25'], 1)}%")
        m2.metric("H2H-Faktor", f"x{s['h2h']}")
        
        edge = (s['data']['o25']/100 * odds_o25) - 1
        stake = int(bankroll * (edge/(odds_o25-1)) * 0.2) if edge > 0 else 0
        m3.metric("Rek. Insats", f"{stake} kr")
        m4.metric("BTTS Sannolikhet", f"{round(s['data']['btts'], 1)}%")

        # Grafer (1X2 och Målsannolikhet)
        st.write("#### Målsannolikhet (Poisson Distribution)")
        dist_data = pd.DataFrame({
            'Mål': [str(i) for i in range(6)],
            'Hemma': [round(poisson_prob(s['data']['h_xg'], i)*100, 1) for i in range(6)],
            'Borta': [round(poisson_prob(s['data']['a_xg'], i)*100, 1) for i in range(6)]
        }).set_index('Mål')
        st.area_chart(dist_data)

st.sidebar.caption("v12.0 Infinite Engine: Online")
