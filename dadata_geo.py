import requests
import streamlit as st

def get_city_suggestions(query: str):
    """Получает список городов от DaData"""
    api_key = st.secrets.get("DADATA_API_KEY", "")
    if not api_key or not query or len(query) < 2:
        return []
    
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}"
    }
    data = {"query": query, "count": 5, "from_bound": {"value": "city"}, "to_bound": {"value": "city"}}
    try:
        r = requests.post(url, json=data, headers=headers, timeout=3)
        if r.status_code == 200:
            return [s["value"] for s in r.json().get("suggestions", [])]
    except:
        pass
    return []

def get_venue_suggestions(query: str, city: str = ""):
    """Получает список заведений (ресторанов/кафе) от DaData"""
    api_key = st.secrets.get("DADATA_API_KEY", "")
    if not api_key or not query or len(query) < 2:
        return []
    
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}"
    }
    # Ищем по названию, при возможности ограничивая городом
    search_query = f"{city} {query}" if city else query
    data = {"query": search_query, "count": 5}
    try:
        r = requests.post(url, json=data, headers=headers, timeout=3)
        if r.status_code == 200:
            return [s["value"] for s in r.json().get("suggestions", [])]
    except:
        pass
    return []
