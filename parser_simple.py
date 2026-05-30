import requests

def search_simplewine(wine_name: str):
    """Ищет вино по названию через публичное API поиска SimpleWine"""
    if not wine_name or len(wine_name) < 3:
        return None
    
    url = f"https://api.simplewine.ru/v1/search?q={requests.utils.quote(wine_name)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code != 200:
            return None
        
        products = res.json().get("products", [])
        if not products:
            return None
        
        # Берем самый первый подходящий товар
        p = products[0]
        attrs = p.get("attributes", {})
        
        # Парсим сахар (сладость)
        sugar_raw = attrs.get("sugar", "").lower()
        sugar = "сухое"
        if "полусух" in sugar_raw: sugar = "полусухое"
        elif "полуслад" in sugar_raw: sugar = "полусладкое"
        elif "слад" in sugar_raw: sugar = "сладкое"
        
        # Парсим выдержку
        production = p.get("description", "").lower()
        age = "не выдержано в дубе"
        if "дуб" in production or "баррик" in production:
            age = "выдержано в дубе"
        elif "осадк" in production:
            age = "выдержано на осадке"
            
        # Бленд или моносорт
        grapes = attrs.get("grape_varieties", [])
        blend_type = "моносортовое" if len(grapes) <= 1 else "бленд"
        
        # Год урожая
        year = attrs.get("vintage", "2022")
        
        # Алкоголь
        alcohol = str(attrs.get("alcohol", "13")).replace("%", "").strip()
        
        return {
            "Название": p.get("name", wine_name),
            "Страна": attrs.get("country", "—"),
            "Сорт винограда": grapes[0] if grapes else "—",
            "Сладость": sugar,
            "Выдержка": age,
            "Моносортовое/Бленд": blend_type,
            "Год урожая": year,
            "Процент алкоголя": alcohol
        }
    except:
        return None
