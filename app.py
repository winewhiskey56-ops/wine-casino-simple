import streamlit as st
import database as db
import dadata_geo as geo
import pandas as pd
import json
import time

# Настройка страницы
st.set_page_config(page_title="Винное Казино", page_icon="🍷", layout="centered")

# --- ГЛОБАЛЬНЫЕ СПРАВОЧНИКИ (ПРАВКА 9) ---
ALL_COUNTRIES = ["Россия", "Франция", "Италия", "Испания", "Германия", "Новая Зеландия", "Чили", "Аргентина", "США", "ЮАР", "Австрия", "Португалия"]
ALL_GRAPES = ["Шардоне", "Совиньон Блан", "Рислинг", "Пино Гриджо", "Гевюрцтраминер", "Каберне Совиньон", "Мерло", "Пино Нуар", "Шираз / Сира", "Мальбек", "Темпранильо", "Санджовезе"]

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ (ПРАВКА 16) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_phone" not in st.session_state:
    st.session_state.user_phone = None
if "logout_confirm" not in st.session_state:
    st.session_state.logout_confirm = False
if "page" not in st.session_state:
    st.session_state.page = "main_menu"

# Проверка авто-входа (Запомнить меня)
if not st.session_state.authenticated and "remember_me_user" in st.session_state:
    st.session_state.authenticated = True
    st.session_state.user_phone = st.session_state.remember_me_user

# --- ОКНО АВТОРИЗАЦИИ ---
if not st.session_state.authenticated:
    st.title("🍷 Винное Казино")
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    
    with tab1:
        login_phone = st.text_input("Номер телефона", key="log_phone")
        login_pass = st.text_input("Пароль", type="password", key="log_pass")
        remember = st.checkbox("Запомнить меня", key="remember_chk") # ПРАВКА 1
        
        if st.button("Войти", use_container_width=True):
            if login_phone == st.secrets["MASTER_USER"] and login_pass == st.secrets["MASTER_PASSWORD"]:
                st.session_state.authenticated = True
                st.session_state.user_phone = login_phone
                if remember: st.session_state.remember_me_user = login_phone
                st.rerun()
                
            users = db.load_users()
            if not users.empty and str(login_phone) in users["phone"].astype(str).values:
                user_row = users[users["phone"].astype(str) == str(login_phone)].iloc[0]
                if str(user_row["password"]) == str(login_pass):
                    st.session_state.authenticated = True
                    st.session_state.user_phone = str(login_phone)
                    if remember: st.session_state.remember_me_user = str(login_phone)
                    st.rerun()
                else:
                    st.error("Неверный пароль")
            else:
                st.error("Пользователь не найден")
                
    with tab2:
        reg_fio = st.text_input("ФИО Ведущего")
        reg_phone = st.text_input("Номер телефона (формат 79xxxxxxxxx)")
        reg_pass = st.text_input("Создайте пароль", type="password")
        if st.button("Зарегистрироваться", use_container_width=True):
            if reg_fio and reg_phone and reg_pass:
                if db.save_user(reg_fio, reg_phone, reg_pass):
                    st.success("Регистрация успешна! Теперь войдите.")
                else:
                    st.error("Пользователь с таким телефоном уже есть.")
            else:
                st.error("Заполните все поля.")
    
    # ПРАВКА 2: Подвал обратной связи
    st.markdown("---")
    with st.expander("💬 Связь с разработчиком"):
        st.write("Вы можете сказать спасибо:")
        st.code("Реквизиты Т-Банк: +79058804440", language="text")
    st.stop()

# --- ПРОВЕРКА АВАРИЙНОЙ СЕССИИ ПРИ ВХОДЕ (ПРАВКА 6) ---
if "game_restored_checked" not in st.session_state:
    if db.check_unfinished_game(st.session_state.user_phone):
        st.warning("⚠️ У вас есть незавершенная игра (сессия активна в течение часа)!")
        col_res1, col_res2 = st.columns(2)
        if col_res1.button("Восстановить игру"):
            db.load_local_backup()
            st.session_state.game_restored_checked = True
            st.rerun()
        if col_res2.button("Начать заново"):
            db.clear_local_backup()
            st.session_state.game_restored_checked = True
            st.rerun()
        st.stop()
    st.session_state.game_restored_checked = True

# --- БОКОВАЯ ПАНЕЛЬ И ВЫХОД (ПРАВКА 6) ---
with st.sidebar:
    st.write(f"👤 Ведущий: **{st.session_state.user_phone}**")
    if st.session_state.user_phone == st.secrets["MASTER_USER"]:
        st.info("👑 Права Администратора")
        
    st.markdown("---")
    if not st.session_state.logout_confirm:
        if st.button("Выйти с аккаунта", use_container_width=True):
            st.session_state.logout_confirm = True
            st.rerun()
    else:
        st.error("Вы точно хотите выйти? Активная игра будет сброшена!")
        c_out1, c_out2 = st.columns(2)
        if c_out1.button("Да", key="confirm_yes"):
            st.session_state.authenticated = False
            st.session_state.user_phone = None
            st.session_state.logout_confirm = False
            if "remember_me_user" in st.session_state: del st.session_state.remember_me_user
            st.rerun()
        if c_out2.button("Нет", key="confirm_no"):
            st.session_state.logout_confirm = False
            st.rerun()

# --- РЕНДЕРИНГ ЭКРАНОВ АДМИНА ИЛИ ИГРЫ ---
if st.session_state.user_phone == st.secrets["MASTER_USER"] and st.session_state.page == "main_menu":
    st.title("👑 Мастер-панель Управления")
    t_m1, t_m2 = st.tabs(["👥 Пользователи", "🎲 История всех игр"])
    
    with t_m1: # ПРАВКА 3: Профили и удаление пользователей
        users = db.load_users()
        if users.empty: st.write("База пуста")
        for idx, r in users.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{r['fio']}** ({r['phone']})")
                if col2.button("📜 Профиль / Игры", key=f"p_{r['phone']}_{idx}"):
                    st.session_state.view_profile_phone = r['phone']
                if col3.button("🗑️", key=f"d_u_{r['phone']}_{idx}"):
                    db.delete_user_from_db(r['phone'])
                    st.success("Удален")
                    st.rerun()
                    
        if "view_profile_phone" in st.session_state:
            st.markdown(f"#### История игр ведущего {st.session_state.view_profile_phone}")
            all_g = db.load_all_games()
            if not all_g.empty:
                filtered = all_g[all_g["phone"].astype(str) == str(st.session_state.view_profile_phone)]
                st.dataframe(filtered[["date", "venue", "winner", "status"]] if not filtered.empty else "Игр нет")
            if st.button("Закрыть профиль"):
                del st.session_state.view_profile_phone
                st.rerun()
                
    with t_m2: # ПРАВКА 3: Удаление игр из базы
        games = db.load_all_games()
        if games.empty: st.write("Игр нет")
        for idx, r in games.iterrows():
            col_g1, col_g2 = st.columns([5, 1])
            col_g1.write(f"📅 {r['date']} | 📍 {r['venue']} | 🏆 {r['winner']}")
            if col_g2.button("❌", key=f"d_g_{r['game_id']}"):
                db.delete_game_from_db(r['game_id'])
                st.success("Удалено")
                st.rerun()
    st.stop()

# --- ДВИЖОК ИГРЫ (ОСНОВНЫЕ СЦЕНАРИИ) ---
if st.session_state.page == "main_menu":
    st.title("🎲 Главное меню")
    if st.button("🚀 Создать новую игру", use_container_width=True):
        st.session_state.page = "setup_game"
        st.session_state.game_setup = {"city": "", "venue_name": "", "players_count": 4}
        st.session_state.players = []
        st.rerun()
        
    st.subheader("📜 Ваши прошедшие игры")
    games = db.load_all_games()
    if not games.empty:
        my_games = games[games["phone"].astype(str) == str(st.session_state.user_phone)]
        if not my_games.empty:
            st.dataframe(my_games[["date", "venue", "winner", "status"]])
        else:
            st.info("Вы еще не проводили игры.")

elif st.session_state.page == "setup_game":
    st.title("⚙️ Настройки мероприятия")
    
    # ПРАВКА 4 и 5: Ввод в одно поле DaData + сохранение состояния
    c_val = st.text_input("Город проведения", value=st.session_state.game_setup.get("city", ""))
    st.session_state.game_setup["city"] = c_val
    if c_val:
        sug_cities = geo.get_suggestions(c_val, "address")
        if sug_cities: st.caption(f"💡 Подсказка: {', '.join(sug_cities)}")
            
    v_val = st.text_input("Название заведения", value=st.session_state.game_setup.get("venue_name", ""))
    st.session_state.game_setup["venue_name"] = v_val
    
    p_count = st.number_input("Количество участников", min_value=1, max_value=30, value=st.session_state.game_setup.get("players_count", 4))
    st.session_state.game_setup["players_count"] = p_count
    
    col_nav1, col_nav2 = st.columns(2)
    if col_nav1.button("⬅️ В меню"):
        st.session_state.page = "main_menu"
        st.rerun()
    if col_nav2.button("Далее ➡️"):
        st.session_state.page = "players_reg"
        st.rerun()

elif st.session_state.page == "players_reg":
    st.title("👥 Регистрация игроков")
    count = st.session_state.game_setup["players_count"]
    
    # Восстановление имен, если вернулись назад (ПРАВКА 5)
    if not st.session_state.players:
        st.session_state.players = [{"name": f"Игрок {i+1}", "balance": 500} for i in range(count)]
        
    for i in range(count):
        p_name = st.text_input(f"Имя игрока №{i+1}", value=st.session_state.players[i]["name"], key=f"p_init_name_{i}")
        st.session_state.players[i]["name"] = p_name
        
    col_p1, col_p2 = st.columns(2)
    if col_p1.button("⬅️ Назад"):
        st.session_state.page = "setup_game"
        st.rerun()
    if col_p2.button("Начать игру 🎰"):
        st.session_state.game_id = str(int(time.time()))
        st.session_state.round_num = 1
        st.session_state.rounds_history = {}
        st.session_state.page = "wine_params"
        db.save_local_backup()
        st.rerun()

elif st.session_state.page == "wine_params":
    st.title(f"🍷 Раунд {st.session_state.round_num}: Параметры Вина")
    
    # ПРАВКА 13: Восстановление имени вина при шаге назад
    if f"round_{st.session_state.round_num}" not in st.session_state.rounds_history:
        st.session_state.rounds_history[f"round_{st.session_state.round_num}"] = {
            "name": "", "country": "Россия", "grape": "Шардоне", "alc": 12.0
        }
    
    r_data = st.session_state.rounds_history[f"round_{st.session_state.round_num}"]
    
    w_name = st.text_input("Название / этикетка вина", value=r_data["name"])
    w_country = st.selectbox("Правильная страна", options=ALL_COUNTRIES, index=ALL_COUNTRIES.index(r_data["country"]) if r_data["country"] in ALL_COUNTRIES else 0)
    w_grape = st.selectbox("Правильный сорт", options=ALL_GRAPES, index=ALL_GRAPES.index(r_data["grape"]) if r_data["grape"] in ALL_GRAPES else 0)
    
    # ПРАВКА 12: Числовой ввод алкоголя эталона
    w_alc = st.number_input("Правильный процент алкоголя (%)", min_value=0.0, max_value=25.0, value=r_data["alc"], step=0.1)
    
    # Сохраняем в историю раунда
    st.session_state.rounds_history[f"round_{st.session_state.round_num}"] = {
        "name": w_name, "country": w_country, "grape": w_grape, "alc": w_alc
    }
    
    if st.button("Перейти к ставкам ➡️", use_container_width=True):
        st.session_state.page = "bets_page"
        db.save_local_backup()
        st.rerun()

elif st.session_state.page == "bets_page":
    st.title(f"🎰 Прием ставок — Раунд {st.session_state.round_num}")
    
    # ПРАВКА 8: Навигация назад к вводу вина
    if st.button("⬅️ Исправить параметры вина"):
        st.session_state.page = "wine_params"
        st.rerun()
        
    st.markdown("---")
    
    # ПРАВКА 10: Убрана кнопка "Добавить строку" — строки идут автоматически по игрокам
    for idx, p in enumerate(st.session_state.players):
        st.write(f"👤 **{p['name']}** (Доступный баланс: {p['balance']} фишек)")
        
        # Восстановление старой ставки игрока, если прыгаем назад-вперед (ПРАВКА 13)
        b_val_key = f"bet_val_{p['name']}_{st.session_state.round_num}"
        b_country_key = f"bet_country_{p['name']}_{st.session_state.round_num}"
        b_grape_key = f"bet_grape_{p['name']}_{st.session_state.round_num}"
        b_alc_key = f"bet_alc_{p['name']}_{st.session_state.round_num}"
        
        if b_val_key not in st.session_state: st.session_state[b_val_key] = 50
        if b_country_key not in st.session_state: st.session_state[b_country_key] = ALL_COUNTRIES[0]
        if b_grape_key not in st.session_state: st.session_state[b_grape_key] = ALL_GRAPES[0]
        if b_alc_key not in st.session_state: st.session_state[b_alc_key] = 12.0
            
        # ПРАВКА 11: Кнопки фишек слева(-) и справа(+) от ввода ставки
        col_m, col_i, col_p = st.columns([1, 2, 1])
        
        if col_m.button("➖ 50", key=f"m_{idx}"):
            st.session_state[b_val_key] = max(0, st.session_state[b_val_key] - 50)
            st.rerun()
            
        chosen_bet = col_i.number_input("Сумма фишек", min_value=0, max_value=int(p['balance']), value=int(st.session_state[b_val_key]), key=f"num_{idx}")
        st.session_state[b_val_key] = chosen_bet
        
        if col_p.button("➕ 50", key=f"p_{idx}"):
            st.session_state[b_val_key] = min(int(p['balance']), st.session_state[b_val_key] + 50)
            st.rerun()
            
        # Поля выбора ставок игроков по глобальным справочникам (ПРАВКА 9)
        st.session_state[b_country_key] = st.selectbox("Ставка на Страну", options=ALL_COUNTRIES, key=f"c_{idx}", index=ALL_COUNTRIES.index(st.session_state[b_country_key]))
        st.session_state[b_grape_key] = st.selectbox("Ставка на Сорт", options=ALL_GRAPES, key=f"g_{idx}", index=ALL_GRAPES.index(st.session_state[b_grape_key]))
        
        # ПРАВКА 12: Свободный ввод алкоголя игроком
        st.session_state[b_alc_key] = st.number_input("Ставка на % алкоголя", min_value=0.0, max_value=20.0, step=0.1, value=float(st.session_state[b_alc_key]), key=f"a_{idx}")
        st.markdown("---")
        
    if st.button("📊 Рассчитать итоги раунда", use_container_width=True):
        st.session_state.page = "round_results"
        db.save_local_backup()
        st.rerun()

elif st.session_state.page == "round_results":
    st.title(f"📊 Итоги раунда {st.session_state.round_num}")
    
    target = st.session_state.rounds_history[f"round_{st.session_state.round_num}"]
    
    st.write(f"🟢 **Правильный ответ:** {target['name']} ({target['country']}, {target['grape']}, {target['alc']}% )")
    
    results_table = []
    
    # Подсчет результатов (выполняется один раз при переходе на экран)
    for p in st.session_state.players:
        b_val = st.session_state.get(f"bet_val_{p['name']}_{st.session_state.round_num}", 0)
        b_country = st.session_state.get(f"bet_country_{p['name']}_{st.session_state.round_num}", "")
        b_grape = st.session_state.get(f"bet_grape_{p['name']}_{st.session_state.round_num}", "")
        b_alc = st.session_state.get(f"bet_alc_{p['name']}_{st.session_state.round_num}", 0.0)
        
        # Вычисление попадания
        win_coef = 0
        hit_details = []
        if b_country == target["country"]: 
            win_coef += 2
            hit_details.append("Страна (x2)")
        if b_grape == target["grape"]: 
            win_coef += 3
            hit_details.append("Сорт (x3)")
        if abs(float(b_alc) - float(target["alc"])) <= 0.5: # ПРАВКА 12: погрешность ±0.5
            win_coef += 2
            hit_details.append("Алкоголь (x2)")
            
        if win_coef > 0:
            win_amount = b_val * win_coef
            p["balance"] += win_amount
            status_text = f"🎉 Сыграла: {', '.join(hit_details)}"
            p_payout = win_amount
        else:
            p["balance"] -= b_val
            status_text = "❌ Не сыграла" # ПРАВКА 14: Отображение проигравших
            p_payout = -b_val
            
        results_table.append({
            "Игрок": p["name"],
            "Ставка": b_val,
            "Прогноз": f"{b_country} / {b_grape} / {b_alc}%",
            "Статус": status_text,
            "Баланс": p["balance"]
        })
        
    st.table(pd.DataFrame(results_table))
    
    col_r1, col_r2 = st.columns(2)
    if col_r1.button("⬅️ Назад к ставкам"): # ПРАВКА 8
        st.session_state.page = "bets_page"
        st.rerun()
        
    if col_r2.button("Следующий раунд ➡️"):
        st.session_state.round_num += 1
        st.session_state.page = "wine_params"
        db.save_local_backup()
        st.rerun()
        
    if st.button("🏁 Завершить всю игру и сохранить", use_container_width=True):
        # Определение победителя
        best_player = max(st.session_state.players, key=lambda x: x["balance"])
        
        # ПРАВКА 15: Отправка и сохранение игры в историю базы Гугл Таблиц
        game_result_data = {
            "game_id": str(st.session_state.game_id),
            "phone": str(st.session_state.user_phone),
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "venue": f"{st.session_state.game_setup['city']}, {st.session_state.game_setup['venue_name']}",
            "winner": str(best_player["name"]),
            "status": "Завершена",
            "full_json": json.dumps(st.session_state.players, ensure_ascii=False),
            "last_update": int(time.time())
        }
        db.save_game_to_db(game_result_data)
        db.clear_local_backup() # Удаляем бэкап, так как игра успешно закрыта
        
        st.session_state.page = "main_menu"
        st.success("Игра сохранена в облако!")
        time.sleep(1.5)
        st.rerun()
