import requests
import streamlit as st

API_KEY = st.secrets["DADATA_API_KEY"]

def get_cities(query: str):
    if not query or len(query) < 2:
        return []
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {API_KEY}"
    }
    # Ограничиваем поиск только городами (from_bound/to_bound)
    data = {
        "query": query, 
        "count": 5,
        "from_bound": {"value": "city"},
        "to_bound": {"value": "city"}
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=3)
        if response.status_code == 200:
            suggestions = response.json().get("suggestions", [])
            return [s["value"] for s in suggestions]
    except:
        pass
    return []

def get_venues(city: str, query: str):
    if not query or len(query) < 2:
        return []
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {API_KEY}"
    }
    # Ищем организации в конкретном городе
    data = {"query": f"{city} {query}", "count": 5}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=3)
        if response.status_code == 200:
            suggestions = response.json().get("suggestions", [])
            result = []
            for s in suggestions:
                name = s["value"]
                address = s.get("data", {}).get("address", {}).get("value", "Адрес не найден")
                result.append({"name": name, "address": address})
            return result
    except:
        pass
    return []
