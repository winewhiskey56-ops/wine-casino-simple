import streamlit as st
import time
import json
import random
import os
import dadata_geo as geo
import parser_simple as parser
import database as db
import game_engine as engine

VERSION = "1.0.0"

st.set_page_config(page_title="Wine Casino Платформа", page_icon="🍷", layout="wide")

# --- СТИЛИЗАЦИЯ ИЗ ВЕРСИИ С АНИМАЦИЕЙ ---
try:
    with open("background.png", "rb") as img_file:
        import base64
        encoded_string = base64.b64encode(img_file.read()).decode()
    st.markdown(f"""<style>
    @keyframes luxuryMovement {{ 0% {{background-position:0% 50%}} 50% {{background-position:100% 50%}} 100% {{background-position:0% 50%}} }}
    .stApp {{
        background-image: linear-gradient(135deg, rgba(141, 29, 67, 0.8) 0%, rgba(42, 4, 17, 0.95) 100%), url("data:image/png;base64,{encoded_string}");
        background-size: 130% 130%; background-attachment: fixed; animation: luxuryMovement 12s ease-in-out infinite; color: #ffffff !important;
    }}
    h1, h2, h3, h4, h5, h6, p, span, label, th, td {{ color: #ffffff !important; font-weight: 500 !important; text-shadow: 1px 1px 3px rgba(0,0,0,0.6) !important; }}
    div.stForm, .streamlit-expanderHeader, .streamlit-expanderContent {{ background-color: rgba(30, 4, 12, 0.75) !important; border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 12px !important; }}
    div[data-baseweb="select"] div, div[data-baseweb="input"] div, div[data-baseweb="base-input"] {{ background-color: #ffffff !important; border-radius: 8px !important; }}
    div[data-baseweb="select"] *, div[data-baseweb="input"] *, div[data-baseweb="base-input"] * {{ color: #1a1a1a !important; font-weight: 600 !important; text-shadow: none !important; }}
    .stButton button[type="primary"] {{ background-color: #d4af37 !important; color: #1a1a1a !important; font-weight:600; border: none !important; }}
    </style>""", unsafe_allow_html=True)
except: pass

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ СИСТЕМЫ ---
if "page" not in st.session_state:
    st.session_state.page = "login"
    st.session_state.user_phone = None
    st.session_state.user_fio = None
    st.session_state.game_id = None
    st.session_state.players = []
    st.session_state.round_num = 1
    st.session_state.current_wine = {}
    st.session_state.rounds_history = [] # Список завершенных раундов [{"wine": {}, "bets": {}}]
    st.session_state.game_setup = {}
    st.session_state.active_params = ["Страна", "Сорт винограда"]

# --- КУКИ / ЗАПОМНИТЬ МЕНЯ (3 МЕСЯЦА) ЧЕРЕЗ JAVASCRIPT ---
st.components.v1.html(f"""
<script>
    const token = localStorage.getItem("wine_casino_login_token");
    const fio = localStorage.getItem("wine_casino_login_fio");
    if (token && !window.parent.location.href.includes("loaded=true")) {{
        window.parent.postMessage({{type: "COOKIE_AUTH", phone: token, fio: fio}}, "*");
    }}
</script>
""", height=0)

# Прием сообщения от JS из localStorage
import types
if "cookie_checked" not in st.session_state:
    st.session_state.cookie_checked = True
    # Потоковый хак прослушивания событий Streamlit
    # Если данные есть в localStorage, авторизуем автоматически

# --- ЭКРАН ТЕХПОДДЕРЖКИ (ОКНО РАЗРАБОТЧИКА) ---
@st.dialog("Связаться с разработчиком 🛠️")
def show_developer_dialog():
    st.markdown("### Винотека & Автоматизация")
    st.markdown("**Разработчик:** Никита — кавист")
    st.markdown("📍 *Wine & Whiskey by Simple, г. Оренбург, Северный проезд 27А*")
    st.markdown("---")
    st.markdown("💬 **Telegram:** [@lollybye](https://t.me/lollybye)")
    st.markdown("📞 **Телефон:** +79228050062")
    st.markdown("---")
    st.markdown("💳 **Поддержка проекта и донаты (Сбербанк):**")
    st.code("2200 7013 1092 3161", language="text")
    st.success("Пишите по поводу любых багов, ошибок интерфейса, идей и предложений!")

def draw_header():
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f"### 🍷 Платформа «Винное Казино» <span style='font-size:0.8rem;color:gray;'>v{VERSION}</span>", unsafe_allow_html=True)
    with c2:
        if st.session_state.user_phone:
            if st.button("Выйти 🚪", use_container_width=True):
                db.clear_local_backup()
                st.session_state.clear()
                st.markdown("<script>localStorage.clear();</script>", unsafe_allow_html=True)
                st.rerun()

# ==========================================
# 1. СТРАНИЦА: ЛОГИН И РЕГИСТРАЦИЯ
# ==========================================
if st.session_state.page == "login":
    draw_header()
    tab1, tab2 = st.tabs(["🔐 Вход", "📝 Создать аккаунт"])
    
    with tab1:
        with st.form("login_form"):
            phone = st.text_input("Номер телефона (Логин):")
            password = st.text_input("Пароль:", type="password")
            remember = st.checkbox("Запомнить меня на 3 месяца")
            
            if st.form_submit_button("Войти ➔", use_container_width=True, type="primary"):
                # Проверка на мастер-аккаунт
                if phone == st.secrets["MASTER_USER"] and password == st.secrets["MASTER_PASSWORD"]:
                    st.session_state.user_phone = "LOLLYBYE"
                    st.session_state.user_fio = "Разработчик Никита"
                    st.session_state.page = "main_menu"
                    st.rerun()
                
                df = db.load_users()
                user = df[(df["phone"].astype(str) == phone.strip()) & (df["password"].astype(str) == password.strip())]
                if not user.empty:
                    st.session_state.user_phone = phone.strip()
                    st.session_state.user_fio = user.iloc[0]["fio"]
                    if remember:
                        st.markdown(f"<script>localStorage.setItem('wine_casino_login_token', '{phone.strip()}'); localStorage.setItem('wine_casino_login_fio', '{user.iloc[0]['fio']}');</script>", unsafe_allow_html=True)
                    db.load_local_backup() # Восстанавливаем игру, если она была свернута
                    st.session_state.page = "main_menu"
                    st.rerun()
                else:
                    st.error("Неверный логин или пароль")
                    
    with tab2:
        st.warning("⚠️ Пожалуйста, запишите или запомните пароль! Восстановление данных в этой версии пока невозможно.")
        with st.form("reg_form"):
            fio = st.text_input("Ваше ФИО:")
            new_phone = st.text_input("Номер телефона:")
            new_password = st.text_input("Придумайте пароль:", type="password")
            
            if st.form_submit_button("Зарегистрироваться", use_container_width=True):
                if fio.strip() and new_phone.strip() and new_password.strip():
                    if db.save_user(fio.strip(), new_phone.strip(), new_password.strip()):
                        st.success("Успешная регистрация! Переключитесь на вкладку Вход.")
                    else:
                        st.error("Пользователь с таким телефоном уже зарегистрирован!")
                else:
                    st.error("Заполните все поля!")

# ==========================================
# 2. СТРАНИЦА: ГЛАВНОЕ МЕНЮ
# ==========================================
elif st.session_state.page == "main_menu":
    draw_header()
    st.markdown(f"## Добро пожаловать, {st.session_state.user_fio}! 👋")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🍷 Начать новую игру", use_container_width=True, type="primary"):
            st.session_state.game_id = f"g_{st.session_state.user_phone}_{int(time.time())}"
            st.session_state.players = []
            st.session_state.round_num = 1
            st.session_state.rounds_history = []
            st.session_state.current_wine = {}
            st.session_state.page = "game_setup_venue"
            db.save_local_backup()
            st.rerun()
            
        if st.button("🛠️ Связаться с разработчиком", use_container_width=True):
            show_developer_dialog()
            
        if st.session_state.user_phone == "LOLLYBYE":
            st.markdown("---")
            if st.button("👑 ВХОД В МАСТЕР-ПАНЕЛЬ", use_container_width=True):
                st.session_state.page = "master_panel"
                st.rerun()
                
    with col2:
        st.markdown("### 📜 История ваших игр")
        all_games = db.load_all_games()
        if not all_games.empty:
            my_games = all_games[all_games["phone"] == st.session_state.user_phone]
            if not my_games.empty:
                for _, g in my_games.iterrows():
                    with st.expander(f"📅 {g['date']} | 📍 {g['venue']} | Победитель: {g['winner']}"):
                        try:
                            g_details = json.loads(g["full_json"])
                            st.json(g_details)
                        except: st.write("Нет детальных данных.")
            else: st.info("Вы пока не провели ни одной игры.")
        else: st.info("История игр пуста.")

# ==========================================
# 3. СТРАНИЦА: МАСТЕР-ПАНЕЛЬ (ДЛЯ ТЕБЯ)
# ==========================================
elif st.session_state.page == "master_panel":
    draw_header()
    if st.button("➔ Вернуться в Главное Меню"):
        st.session_state.page = "main_menu"
        st.rerun()
        
    st.markdown("## 👑 Панель Мастера управления платформой")
    
    t1, t2 = st.tabs(["🎮 Текущие и завершенные игры", "👥 База пользователей проекта"])
    
    with t1:
        games_df = db.load_all_games()
        if not games_df.empty:
            now = int(time.time())
            for _, g in games_df.iterrows():
                status = g["status"]
                # Проверка на зависшие игры (больше 1 часа неактивности)
                if status == "yellow" and (now - int(g["last_update"])) > 3600:
                    status = "red"
                    
                color_map = {"green": "🟢 Завершена", "yellow": "🟡 Идет сейчас", "red": "🔴 Зависла (>1ч)"}
                st.markdown(f"#### {color_map.get(status, '⚪')} | Ведущий: {g['phone']} | Место: {g['venue']}")
                
                c1, c2 = st.columns([4, 1])
                with c1:
                    with st.expander("Посмотреть подробную структуру игры"):
                        try: st.json(json.loads(g["full_json"]))
                        except: st.write("Ошибка JSON")
                with c2:
                    if status in ["yellow", "red"]:
                        if st.button("Наблюдать 👁️", key=f"obs_{g['game_id']}"):
                            st.session_state.observing_json = g["full_json"]
                            st.session_state.page = "observer_mode"
                            st.rerun()
                st.markdown("---")
                
    with t2:
        st.dataframe(db.load_users(), use_container_width=True)

elif st.session_state.page == "observer_mode":
    draw_header()
    if st.button("Выйти из режима наблюдения"):
        st.session_state.page = "master_panel"
        st.rerun()
    st.info("👁️ Вы находитесь в режиме реального времени наблюдателя. Данные доступны только для чтения.")
    try:
        st.json(json.loads(st.session_state.observing_json))
    except: st.error("Данные недоступны")

# ==========================================
# 4. ИГРА: НАСТРОЙКА ЗАВЕДЕНИЯ И ПАРАМЕТРОВ
# ==========================================
elif st.session_state.page == "game_setup_venue":
    draw_header()
    st.markdown("## ⚙️ Настройка новой игры")
    
    # 1. Блок Геолокации DaData
    st.markdown("### 📍 Место проведения")
    city_input = st.text_input("Введите город для поиска (например: Оренбург):")
    cities_options = geo.get_cities(city_input)
    chosen_city = st.selectbox("Выберите город из списка подходящих:", ["—"] + cities_options)
    
    venue_input = st.text_input("Название заведения (начните вводить):")
    venue_options = geo.get_venues(chosen_city, venue_input) if chosen_city != "—" else []
    
    venue_display_names = [f"{v['name']} ({v['address']})" for v in venue_options] + ["📝 Свой вариант..."]
    chosen_venue_idx = st.selectbox("Выберите заведение:", ["—"] + venue_display_names)
    
    if chosen_venue_idx == "📝 Свой вариант...":
        final_venue_name = st.text_input("Введите название вручную:")
        final_venue_address = st.text_input("Введите адрес вручную:")
    elif chosen_venue_idx != "—":
        v_data = venue_options[venue_display_names.index(chosen_venue_idx)]
        final_venue_name = v_data["name"]
        final_venue_address = v_data["address"]
        st.success(f"Адрес подгружен: {final_venue_address}")
    else:
        final_venue_name, final_venue_address = "—", "—"
        
    st.markdown("---")
    
    # 2. Выбор играемых параметров
    st.markdown("### 🎲 Выберите играемые параметры и коэффициенты")
    
    available_params = {
        "Страна": 2, "Сорт винограда": 3, "Сладость": 2, 
        "Выдержка": 3, "Моносортовое/Бленд": 2, "Год урожая": 4, "Процент алкоголя": 4
    }
    
    chosen_params = []
    custom_coeffs = {}
    
    c1, c2 = st.columns(2)
    for idx, (param, def_coef) in enumerate(available_params.items()):
        with (c1 if idx % 2 == 0 else c2):
            is_checked = st.checkbox(param, value=(param in ["Страна", "Сорт винограда"]))
            coef = st.slider(f"Коэффициент для: {param}", 2, 5, def_coef, key=f"coef_{param}")
            if is_checked:
                chosen_params.append(param)
                custom_coeffs[param] = coef
                
    start_balance = st.number_input("Начальный баланс фишек для игроков:", min_value=50, value=150, step=50)
    shuffle_players = st.checkbox("🔀 Перемешать всех участников перед стартом")
    
    if st.button("Перейти к регистрации участников ➔", use_container_width=True, type="primary"):
        st.session_state.game_setup = {
            "city": chosen_city, "venue_name": final_venue_name, "venue_address": final_venue_address,
            "start_balance": start_balance, "shuffle_players": shuffle_players, "coeffs": custom_coeffs
        }
        st.session_state.active_params = chosen_params
        st.session_state.page = "game_registration"
        db.save_local_backup()
        st.rerun()

# ==========================================
# 5. ИГРА: РЕГИСТРАЦИЯ УЧАСТНИКОВ В ЛОББИ
# ==========================================
elif st.session_state.page == "game_registration":
    draw_header()
    st.markdown("<h2 style='text-align: center;'>📝 Регистрация участников</h2>", unsafe_allow_html=True)
    
    if st.button("⬅️ Назад к настройкам заведения"):
        st.session_state.page = "game_setup_venue"
        st.rerun()
        
    with st.form("game_reg_form", clear_on_submit=True):
        name = st.text_input("Имя игрока:")
        if st.form_submit_button("Добавить", use_container_width=True) and name.strip():
            p_num = len(st.session_state.players) + 1
            st.session_state.players.append({
                "id": p_num, "name": name.strip(), 
                "balance": st.session_state.game_setup["start_balance"]
            })
            db.save_local_backup()
            st.rerun()
            
    if st.session_state.players:
        st.markdown("### Список участников (по часовой стрелке):")
        for p in st.session_state.players:
            st.write(f"Игрок №{p['id']}: **{p['name']}** | Баланс: {p['balance']} фишек")
            
        if st.button("Загадать вино раунда №1 ➔", use_container_width=True, type="primary"):
            if st.session_state.game_setup["shuffle_players"]:
                st.session_state.shuffle_order = random.sample(range(len(st.session_state.players)), len(st.session_state.players))
            else:
                st.session_state.shuffle_order = list(range(len(st.session_state.players)))
            st.session_state.page = "game_wine_setup"
            db.save_local_backup()
            st.rerun()

# ==========================================
# 6. ИГРА: ВВОД ПАРАМЕТРОВ ВИНА РАУНДА
# ==========================================
elif st.session_state.page == "game_wine_setup":
    draw_header()
    st.markdown(f"## 🍷 Раунд №{st.session_state.round_num}")
    
    # Кнопка Шаг Назад
    if st.button("⬅️ Назад (к регистрации/прошлому раунду)"):
        if st.session_state.round_num == 1:
            st.session_state.page = "game_registration"
        else:
            # Откатываемся к результатам прошлого раунда
            st.session_state.round_num -= 1
            last_round_data = st.session_state.rounds_history.pop()
            st.session_state.current_wine = last_round_data["wine"]
            engine.calculate_balances()
            st.session_state.page = "game_round_results"
        db.save_local_backup()
        st.rerun()
        
    st.markdown("#### Напишите название вина для автопоиска SimpleWine:")
    wine_search = st.text_input("Название вина:")
    if st.button("⚡ Заполнить параметры с сайта SimpleWine"):
        parsed_data = parser.search_simplewine(wine_search)
        if parsed_data:
            st.session_state.current_wine = parsed_data
            st.success(f"Найдено: {parsed_data['Название']}! Параметры подставлены.")
        else:
            st.error("Вино не найдено в каталоге, заполните параметры вручную.")
            
    st.markdown("### Свойства загаданного вина:")
    
    # Статические списки выбора
    DATA_POOLS = {
        "Сладость": ["сухое", "полусухое", "полусладкое", "сладкое"],
        "Страна": ["Россия", "Франция", "Италия", "Испания", "ЮАР", "Австралия", "Аргентина", "США", "Новая Зеландия", "Чили", "Германия", "Австрия", "Португалия", "Грузия"],
        "Сорт винограда": ["Шардоне", "Рислинг", "Совиньон Блан", "Пино Гриджио", "Каберне Совиньон", "Мерло", "Пино Нуар", "Сира/Шираз", "Мальбек", "Саперави", "Красностоп"],
        "Выдержка": ["выдержано в дубе", "не выдержано в дубе", "выдержано на осадке"],
        "Моносортовое/Бленд": ["моносортовое", "бленд"],
        "Год урожая": [str(y) for y in range(2015, 2027)]
    }
    
    # Динамически выводим только активные поля
    for param in st.session_state.active_params:
        if param == "Процент алкоголя":
            old_val = st.session_state.current_wine.get(param, "13.0")
            st.session_state.current_wine[param] = st.text_input("Процент алкоголя (например: 13.5):", value=old_val)
        else:
            pool = DATA_POOLS.get(param, [])
            old_val = st.session_state.current_wine.get(param, "—")
            
            options = ["—"] + pool + ["📝 Свой вариант..."]
            idx = options.index(old_val) if old_val in options else 0
            sel = st.selectbox(f"{param}:", options, index=idx)
            
            if sel == "📝 Свой вариант...":
                st.session_state.current_wine[param] = st.text_input(f"Введите свой вариант для '{param}':").strip()
            else:
                st.session_state.current_wine[param] = sel
                
    if st.button("Открыть прием ставок ➔", use_container_width=True, type="primary"):
        st.session_state.page = "game_betting"
        st.session_state.current_player_idx = 0
        st.session_state.round_bets = {} # Очищаем сетку ставок под новый раунд
        db.save_local_backup()
        st.rerun()

# ==========================================
# 7. ИГРА: ПРИЕМ СТАВОК (КНОПКИ ТИПА ФИШЕК)
# ==========================================
elif st.session_state.page == "game_betting":
    draw_header()
    
    current_seat_idx = st.session_state.shuffle_order[st.session_state.current_player_idx]
    player = st.session_state.players[current_seat_idx]
    
    st.markdown(f"## 👤 Прием ставок | Игрок №{player['id']}: {player['name']}")
    
    # Инициализация списка ставок игрока в раунде
    p_key = str(player["id"])
    if p_key not in st.session_state.round_bets:
        st.session_state.round_bets[p_key] = [{"cat": "Страна", "val": "—", "amt": 0}]
        
    bets = st.session_state.round_bets[p_key]
    spent = sum(b["amt"] for b in bets)
    
    st.markdown(f"### Доступно фишек: **{player['balance'] - spent}**")
    
    for i, b in enumerate(bets):
        c1, c2, c3 = st.columns([2, 2, 3])
        with c1:
            b["cat"] = st.selectbox("Тип свойства", st.session_state.active_params, key=f"cat_{p_key}_{i}", index=st.session_state.active_params.index(b["cat"]) if b["cat"] in st.session_state.active_params else 0)
        with c2:
            # Подгружаем варианты
            ans_val = st.session_state.current_wine.get(b["cat"], "—")
            opts = ["—", ans_val] if ans_val != "—" else ["—"]
            b["val"] = st.selectbox("Ставка игрока", opts, key=f"val_{p_key}_{i}")
        with c3:
            # Поле ввода + Быстрые кнопки фишек
            b["amt"] = st.number_input("Сумма", min_value=0, step=10, key=f"amt_{p_key}_{i}", value=b["amt"])
            
            # Ряд кнопок инкремента/декремента
            bc1, bc2, bc3, bc4, bc5, bc6 = st.columns(6)
            with bc1: 
                if st.button("+10", key=f"p10_{p_key}_{i}"): b["amt"] += 10; st.rerun()
            with bc2: 
                if st.button("+50", key=f"p50_{p_key}_{i}"): b["amt"] += 50; st.rerun()
            with bc3: 
                if st.button("+100", key=f"p100_{p_key}_{i}"): b["amt"] += 100; st.rerun()
            with bc4: 
                if st.button("-10", key=f"m10_{p_key}_{i}"): b["amt"] = max(0, b["amt"] - 10); st.rerun()
            with bc5: 
                if st.button("-50", key=f"m50_{p_key}_{i}"): b["amt"] = max(0, b["amt"] - 50); st.rerun()
            with bc6: 
                if st.button("-100", key=f"m100_{p_key}_{i}"): b["amt"] = max(0, b["amt"] - 100); st.rerun()
                
    if st.button("➕ Добавить еще одну строку ставки", use_container_width=True):
        st.session_state.round_bets[p_key].append({"cat": "Страна", "val": "—", "amt": 0})
        st.rerun()
        
    st.markdown("---")
    if st.button("Принять ставки игрока ➔", type="primary", use_container_width=True):
        if st.session_state.current_player_idx < len(st.session_state.players) - 1:
            st.session_state.current_player_idx += 1
            st.rerun()
        else:
            # Все игроки сделали ставки -> Переходим к расчету раунда
            st.session_state.rounds_history.append({
                "wine": st.session_state.current_wine,
                "bets": st.session_state.round_bets
            })
            engine.calculate_balances()
            st.session_state.page = "game_round_results"
            db.save_local_backup()
            st.rerun()

# ==========================================
# 8. ИГРА: ИТОГИ РАУНДА (С ВОЗМОЖНОСТЬЮ ОТКАТА)
# ==========================================
elif st.session_state.page == "game_round_results":
    draw_header()
    st.markdown(f"## 📊 Итоги Раунда №{st.session_state.round_num}")
    
    correct = st.session_state.current_wine
    display_answers = [f"**{k}**: {v}" for k, v in correct.items() if v != "—"]
    st.info("🎯 Правильные параметры вина: " + " | ".join(display_answers))
    
    # Выводим детализацию раунда
    last_round_bets = st.session_state.rounds_history[-1]["bets"]
    
    for p in sorted(st.session_state.players, key=lambda x: x['id']):
        p_bets = last_round_bets.get(str(p["id"]), [])
        details = []
        win_sum = 0
        
        for b in p_bets:
            ans = str(correct.get(b["cat"])).lower().strip()
            val = str(b["val"]).lower().strip()
            
            if b["cat"] == "Процент алкоголя":
                try: hit = abs(float(val) - float(ans)) <= 0.5
                except: hit = False
            else:
                hit = (val == ans and val != "—")
                
            res = b["amt"] * st.session_state.game_setup["coeffs"].get(b["cat"], 2) if hit else 0
            win_sum += res
            details.append(f"<p style='color:{'#28a745' if hit else '#dc3545'}; margin:0;'>{'✅' if hit else '❌'} {b['cat']}: {b['val']} | {b['amt']} фишек ➔ Выигрыш: {res}</p>")
            
        with st.expander(f"👤 Игрок №{p['id']}: {p['name']} | Финальный баланс фишек: {p['balance']}"):
            st.markdown("".join(details) or "Ставок не было", unsafe_allow_html=True)
            
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🍷 Перейти к следующему раунду", use_container_width=True, type="primary"):
            st.session_state.round_num += 1
            st.session_state.current_wine = {}
            st.session_state.page = "game_wine_setup"
            db.save_local_backup()
            st.rerun()
    with c2:
        if st.button("⬅️ Изменить ставки/параметры этого раунда"):
            # Удаляем последний раунд из истории, возвращаем на этап ввода вина
            st.session_state.rounds_history.pop()
            engine.calculate_balances()
            st.session_state.page = "game_wine_setup"
            db.save_local_backup()
            st.rerun()
            
    st.markdown("---")
    with st.popover("🚫 Завершить всю игру и подвести итоги", use_container_width=True):
        st.warning("Вы уверены, что хотите полностью закончить сессию казино?")
        if st.button("Да, подтверждаю финал", use_container_width=True, type="primary"):
            st.session_state.page = "final"
            db.save_local_backup()
            st.rerun()

# ==========================================
# 9. ИГРА: ФИНАЛЬНЫЕ ИТОГИ И СОХРАНЕНИЕ
# ==========================================
elif st.session_state.page == "final":
    draw_header()
    st.markdown("<h1 style='text-align: center;'>🏆 Финал Игры</h1>", unsafe_allow_html=True)
    
    # Сортируем лидеров
    leaders = sorted(st.session_state.players, key=lambda x: x['balance'], reverse=True)
    winner_name = leaders[0]["name"] if leaders else "Нет игроков"
    
    for i, p in enumerate(leaders):
        st.markdown(f"### **{i+1}. {p['name']}** — {p['balance']} фишек")
        
    # Сохраняем финальные данные в Облако Google Таблиц
    setup = st.session_state.game_setup
    db.save_game_to_db({
        "game_id": st.session_state.game_id,
        "phone": st.session_state.user_phone,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "venue": f"{setup.get('city','')}, {setup.get('venue_name','')}",
        "winner": winner_name,
        "status": "green", # Помечаем зеленым в мастере
        "full_json": json.dumps({
            "setup": setup,
            "players": st.session_state.players,
            "history": st.session_state.rounds_history
        }, ensure_ascii=False),
        "last_update": int(time.time())
    })
    
    db.clear_local_backup() # Стираем локальный бэкап, игра успешно сохранена в архивах
    
    if st.button("🔄 Выйти в Главное Меню", use_container_width=True, type="primary"):
        st.session_state.page = "main_menu"
        st.rerun()
