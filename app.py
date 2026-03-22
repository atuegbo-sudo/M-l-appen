@st.cache_data(ttl=3600)
def get_teams(league_id):
    url = f"https://v3.football.api-sports.io{league_id}&season=2023"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        if not data.get('response'):
            st.error(f"API-fel: {data.get('errors')}")
            return {}
        return {item['team']['name']: item['team']['id'] for item in data['response']}
    except Exception as e:
        st.error(f"Kunde inte ansluta till API: {e}")
        return {}
