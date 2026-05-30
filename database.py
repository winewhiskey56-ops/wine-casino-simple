import streamlit as st
from streamlit_searchbox import st_searchbox
# Встроенный в современный Streamlit импорт для работы с Google Таблицами:
from streamlit.connections import GSheetsConnection 
import pandas as pd
import json
import os
import time

DB_CONN = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["SPREADSHEET_URL"]

def load_users():
    try:
        return DB_CONN.read(spreadsheet=SHEET_URL, worksheet="Users", ttl=5)
    except:
        return pd.DataFrame(columns=["fio", "phone", "password"])

def save_user(fio, phone, password):
    df = load_users()
    if phone in df["phone"].astype(str).values:
        return False
    new_user = pd.DataFrame([{"fio": fio, "phone": str(phone), "password": str(password)}])
    updated_df = pd.concat([df, new_user], ignore_index=True)
    DB_CONN.update(spreadsheet=SHEET_URL, worksheet="Users", data=updated_df)
    return True

def save_game_to_db(game_data):
    try:
        df = DB_CONN.read(spreadsheet=SHEET_URL, worksheet="Games", ttl=0)
    except:
        df = pd.DataFrame(columns=["game_id", "phone", "date", "venue", "winner", "status", "full_json", "last_update"])
    
    new_row = pd.DataFrame([game_data])
    # Убираем старую запись этой же игры, если она обновляется
    if not df.empty and game_data["game_id"] in df["game_id"].values:
        df = df[df["game_id"] != game_data["game_id"]]
        
    updated_df = pd.concat([df, new_row], ignore_index=True)
    DB_CONN.update(spreadsheet=SHEET_URL, worksheet="Games", data=updated_df)

def load_all_games():
    try:
        return DB_CONN.read(spreadsheet=SHEET_URL, worksheet="Games", ttl=0)
    except:
        return pd.DataFrame()

# --- ЛОКАЛЬНЫЕ ИЗОЛИРОВАННЫЕ СЕССИИ ДЛЯ КАЖДОГО ВЕДУЩЕГО ---
def get_backup_path():
    return f"backup_{st.session_state.get('user_phone', 'guest')}.json"

def save_local_backup():
    if "user_phone" not in st.session_state: return
    state = {}
    keys_to_save = ["game_id", "players", "page", "round_num", "current_wine", "rounds_history", "game_setup", "active_params"]
    for k in keys_to_save:
        if k in st.session_state: state[k] = st.session_state[k]
    
    # Сохраняем динамические ключи элементов ввода ставок
    dynamic_keys = {k: st.session_state[k] for k in st.session_state.keys() if any(x in k for x in ["_v", "_a", "_c"])}
    state["dynamic_keys"] = dynamic_keys
    
    with open(get_backup_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)
        
    # Дублируем статус "Идет сейчас" в облачную Google Таблицу для Мастер-аккаунта
    if st.session_state.get("page") not in ["registration", "main_menu", "final"]:
        setup = st.session_state.get("game_setup", {})
        save_game_to_db({
            "game_id": st.session_state.game_id,
            "phone": st.session_state.user_phone,
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "venue": f"{setup.get('city', '')}, {setup.get('venue_name', '')}",
            "winner": "В процессе...",
            "status": "yellow",
            "full_json": json.dumps(state, ensure_ascii=False),
            "last_update": int(time.time())
        })

def load_local_backup():
    path = get_backup_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k != "dynamic_keys": st.session_state[k] = v
                if "dynamic_keys" in data:
                    for dk, dv in data["dynamic_keys"].items(): st.session_state[dk] = dv
        except: pass

def clear_local_backup():
    path = get_backup_path()
    if os.path.exists(path):
        try: os.remove(path)
        except: pass
