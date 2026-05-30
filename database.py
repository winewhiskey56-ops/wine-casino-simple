import streamlit as st
import pandas as pd
import json
import os
import time
import gspread
from google.oauth2.service_account import Credentials

# --- ИНИЦИАЛИЗАЦИЯ И ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ---
@st.cache_resource
def get_gspread_client():
    # Извлекаем приватный ключ и принудительно чистим его синтаксис
    raw_key = st.secrets["connections"]["gsheets"]["private_key"]
    
    # Исправляем возможные проблемы с переносами строк (\n)
    if "\\n" in raw_key:
        clean_key = raw_key.replace("\\n", "\n")
    else:
        clean_key = raw_key

    # Убираем случайные лишние пробелы по краям, которые могли скопироваться
    clean_key = clean_key.strip()

    creds_dict = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": clean_key,  # Передаем очищенный ключ
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_worksheet_df(sheet_name: str):
    """Вспомогательная функция для быстрого чтения листа в DataFrame"""
    try:
        gc = get_gspread_client()
        # Открываем по ссылке из secrets
        sh = gc.open_by_url(st.secrets["SPREADSHEET_URL"])
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        # Если листа нет или он пустой, возвращаем пустой DataFrame
        return pd.DataFrame()

def update_worksheet_from_df(sheet_name: str, df: pd.DataFrame):
    """Вспомогательная функция для полной перезаписи листа данными из DataFrame"""
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(st.secrets["SPREADSHEET_URL"])
        
        # Пытаемся открыть лист, если его нет — создаем
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
            
        worksheet.clear()
        # gspread требует список списков, включая заголовки
        df_filled = df.fillna("")
        data_to_save = [df_filled.columns.values.tolist()] + df_filled.values.tolist()
        worksheet.update(data_to_save)
    except Exception as e:
        st.error(f"Ошибка сохранения в Google Таблицу: {e}")

# --- БИЗНЕС-ЛОГИКА ПРИЛОЖЕНИЯ ---

def load_users():
    df = get_worksheet_df("Users")
    if df.empty or "phone" not in df.columns:
        return pd.DataFrame(columns=["fio", "phone", "password"])
    return df

def save_user(fio, phone, password):
    df = load_users()
    if phone in df["phone"].astype(str).values:
        return False
    new_user = pd.DataFrame([{"fio": fio, "phone": str(phone), "password": str(password)}])
    updated_df = pd.concat([df, new_user], ignore_index=True)
    update_worksheet_from_df("Users", updated_df)
    return True

def save_game_to_db(game_data):
    df = get_worksheet_df("Games")
    if df.empty or "game_id" not in df.columns:
        df = pd.DataFrame(columns=["game_id", "phone", "date", "venue", "winner", "status", "full_json", "last_update"])
    
    new_row = pd.DataFrame([game_data])
    if not df.empty and game_data["game_id"] in df["game_id"].values:
        df = df[df["game_id"] != game_data["game_id"]]
        
    updated_df = pd.concat([df, new_row], ignore_index=True)
    update_worksheet_from_df("Games", updated_df)

def load_all_games():
    return get_worksheet_df("Games")

# --- ЛОКАЛЬНЫЕ ИЗОЛИРОВАННЫЕ СЕССИИ ДЛЯ КАЖДОГО ВЕДУЩЕГО ---
def get_backup_path():
    return f"backup_{st.session_state.get('user_phone', 'guest')}.json"

def save_local_backup():
    if "user_phone" not in st.session_state: return
    state = {}
    keys_to_save = ["game_id", "players", "page", "round_num", "current_wine", "rounds_history", "game_setup", "active_params"]
    for k in keys_to_save:
        if k in st.session_state: state[k] = st.session_state[k]
    
    dynamic_keys = {k: st.session_state[k] for k in st.session_state.keys() if any(x in k for x in ["_v", "_a", "_c"])}
    state["dynamic_keys"] = dynamic_keys
    
    with open(get_backup_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)
        
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
