import streamlit as st
import pandas as pd
import json
import os
import time
import gspread
from google.oauth2.service_account import Credentials

@st.cache_resource
def get_gspread_client():
    raw_key = st.secrets["connections"]["gsheets"]["private_key"]
    clean_key = raw_key.replace("\\n", "\n") if "\\n" in raw_key else raw_key
    clean_key = clean_key.strip()

    creds_dict = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": clean_key,
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
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(st.secrets["SPREADSHEET_URL"])
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def update_worksheet_from_df(sheet_name: str, df: pd.DataFrame):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(st.secrets["SPREADSHEET_URL"])
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")
        worksheet.clear()
        df_filled = df.fillna("")
        data_to_save = [df_filled.columns.values.tolist()] + df_filled.values.tolist()
        worksheet.update(data_to_save)
    except Exception as e:
        st.error(f"Ошибка Google Таблиц: {e}")

def load_users():
    df = get_worksheet_df("Users")
    if df.empty or "phone" not in df.columns:
        return pd.DataFrame(columns=["fio", "phone", "password"])
    return df

def save_user(fio, phone, password):
    df = load_users()
    if str(phone) in df["phone"].astype(str).values:
        return False
    new_user = pd.DataFrame([{"fio": fio, "phone": str(phone), "password": str(password)}])
    update_worksheet_from_df("Users", pd.concat([df, new_user], ignore_index=True))
    return True

def delete_user_from_db(phone):
    df = load_users()
    if not df.empty:
        update_worksheet_from_df("Users", df[df["phone"].astype(str) != str(phone)])

def save_game_to_db(game_data):
    df = get_worksheet_df("Games")
    if df.empty or "game_id" not in df.columns:
        df = pd.DataFrame(columns=["game_id", "phone", "date", "venue", "winner", "status", "full_json", "last_update"])
    if not df.empty and str(game_data["game_id"]) in df["game_id"].astype(str).values:
        df = df[df["game_id"].astype(str) != str(game_data["game_id"])]
    update_worksheet_from_df("Games", pd.concat([df, pd.DataFrame([game_data])], ignore_index=True))

def load_all_games():
    return get_worksheet_df("Games")

def delete_game_from_db(game_id):
    df = load_all_games()
    if not df.empty:
        update_worksheet_from_df("Games", df[df["game_id"].astype(str) != str(game_id)])

# Кэш для сохранения сессии при обновлении страницы (ПРАВКА 1)
@st.cache_data(ttl=86400)
def get_persistent_session():
    return {}

def check_unfinished_game(phone):
    path = f"backup_{phone}.json"
    return os.path.exists(path) and (time.time() - os.path.getmtime(path) < 3600)

def save_local_backup():
    if "user_phone" not in st.session_state or not st.session_state.user_phone: return
    state = {k: st.session_state[k] for k in ["game_id", "players", "page", "round_num", "current_wine", "rounds_history", "game_setup", "active_params", "wines_stack", "coefficients", "current_player_idx"] if k in st.session_state}
    dynamic_keys = {k: st.session_state[k] for k in st.session_state.keys() if any(x in k for x in ["_v", "_a", "_c", "bet_val_"])}
    state["dynamic_keys"] = dynamic_keys
    with open(f"backup_{st.session_state.user_phone}.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

def load_local_backup():
    if "user_phone" not in st.session_state: return
    path = f"backup_{st.session_state.user_phone}.json"
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
    if "user_phone" not in st.session_state: return
    path = f"backup_{st.session_state.user_phone}.json"
    if os.path.exists(path):
        try: os.remove(path)
        except: pass
