import requests
import streamlit as st

def get_suggestions(query: str, target: str = "address"):
    """
    Получает подсказки от DaData (города или заведения).
    target="address" для поиска городов, target="party" или "address" с фильтрами для мест.
    """
    api_key = st.secrets.get("DADATA_API_KEY", "")
    if not api_key:
        return []
    
    url = f"https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/{target}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}"
    }
    
    data = {"query": query, "count": 5}
    if target == "address":
        # Ограничиваем подсказки только городами
        data["from_bound"] = {"value": "city"}
        data["to_bound"] = {"value": "city"}

    try:
        r = requests.post(url, json=data, headers=headers, timeout=3)
        if r.status_code == 200:
            return [suggestion["value"] for suggestion in r.json().get("suggestions", [])]
    except:
        pass
    return []
