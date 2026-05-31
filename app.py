import streamlit as st
import database as db
import dadata_geo as geo
import pandas as pd
import json
import time
import random

st.set_page_config(page_title="WINE & WHISKEY by simple", page_icon="🍷", layout="centered")

ALL_COUNTRIES = ["Россия", "Франция", "Италия", "Испания", "Германия", "Новая Зеландия", "Чили", "Аргентина", "США", "ЮАР", "Австрия", "Португалия"]
ALL_GRAPES = ["Шардоне", "Совиньон Блан", "Рислинг", "Пино Гриджо", "Гевюрцтраминер", "Каберне Совиньон", "Мерло", "Пино Нуар", "Шираз / Сира", "Мальбек", "Темпранильо", "Санджовезе"]

# --- ПРАВКА 1: Авторизация через долгий кэш сессии ---
pers_session = db.get_persistent_session()
if "authenticated" not in st.session_state:
    st.session_state.authenticated = pers_session.get("auth", False)
    st.session_state.user_phone = pers_session.get("phone", None)
    st.session_state.user_fio = pers_session.get("fio", "")

if "page" not in st.session_state: st.session_state.page = "main_menu"
if "logout_confirm" not in st.session_state: st.session_state.logout_confirm = False

# --- ИНТЕРФЕЙС АВТОРИЗАЦИИ ---
if not st.session_state.authenticated:
    st.title("🍷 Винное Казино")
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])
    
    with tab1:
        login_phone = st.text_input("Номер телефона", key="log_phone")
        login_pass = st.text_input("Пароль", type="password", key="log_pass")
        remember = st.checkbox("Запомнить меня", key="remember_chk")
        
        if st.button("Войти", use_container_width=True):
            if login_phone == st.secrets["MASTER_USER"] and login_pass == st.secrets["MASTER_PASSWORD"]:
                st.session_state.authenticated = True
                st.session_state.user_phone = login_phone
                st.session_state.user_fio = "Администратор"
                if remember:
                    pers_session["auth"] = True; pers_session["phone"] = login_phone; pers_session["fio"] = "Администратор"
                st.rerun()
                
            users = db.load_users()
            if not users.empty and str(login_phone) in users["phone"].astype(str).values:
                user_row = users[users["phone"].astype(str) == str(login_phone)].iloc[0]
                if str(user_row["password"]) == str(login_pass):
                    st.session_state.authenticated = True
                    st.session_state.user_phone = str(login_phone)
                    st.session_state.user_fio = user_row["fio"]
                    if remember:
                        pers_session["auth"] = True; pers_session["phone"] = str(login_phone); pers_session["fio"] = user_row["fio"]
                    st.rerun()
                else: st.error("Неверный пароль")
            else: st.error("Пользователь не найден")
                
    with tab2:
        reg_fio = st.text_input("ФИО Ведущего")
        reg_phone = st.text_input("Номер телефона (79xxxxxxxxx)")
        reg_pass = st.text_input("Пароль", type="password")
        if st.button("Зарегистрироваться", use_container_width=True):
            if reg_fio and reg_phone and reg_pass:
                if db.save_user(reg_fio, reg_phone, reg_pass): st.success("Успешно! Войдите во вкладке 'Вход'")
                else: st.error("Телефон уже занят")
            else: st.error("Заполните поля")
    st.stop()

# --- БОКОВАЯ ПАНЕЛЬ (ПРАВКА 3: Отображение ФИО вместо номера) ---
with st.sidebar:
    st.write(f"👤 Ведущий: **{st.session_state.user_fio}**")
    if st.session_state.user_phone == st.secrets["MASTER_USER"]: st.info("👑 Администратор")
    st.markdown("---")
    if not st.session_state.logout_confirm:
        if st.button("Выйти с аккаунта", use_container_width=True):
            st.session_state.logout_confirm = True; st.rerun()
    else:
        st.error("Точно выйти?")
        c1, c2 = st.columns(2)
        if c1.button("Да"):
            st.session_state.authenticated = False; pers_session.clear()
            st.session_state.logout_confirm = False; st.rerun()
        if c2.button("Нет"): st.session_state.logout_confirm = False; st.rerun()

# --- ВОССТАНОВЛЕНИЕ БЭКАПА ---
if "game_restored_checked" not in st.session_state:
    if db.check_unfinished_game(st.session_state.user_phone):
        st.warning("⚠️ Обнаружена незавершенная игра!")
        col1, col2 = st.columns(2)
        if col1.button("Восстановить"):
            db.load_local_backup(); st.session_state.game_restored_checked = True; st.rerun()
        if col2.button("Удалить бэкап"):
            db.clear_local_backup(); st.session_state.game_restored_checked = True; st.rerun()
        st.stop()
    st.session_state.game_restored_checked = True

# --- ЭКРАН МАСТЕР-ПАНЕЛИ АДМИНА ---
if st.session_state.user_phone == st.secrets["MASTER_USER"] and st.session_state.page == "main_menu":
    st.title("👑 Мастер-панель Управления")
    tm1, tm2 = st.tabs(["👥 Пользователи", "🎲 Все игры"])
    with tm1:
        u = db.load_users()
        for idx, r in u.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"**{r['fio']}** ({r['phone']})")
            if col2.button("📜 Профиль", key=f"u_{r['phone']}"): st.session_state.view_profile_phone = r['phone']
            if col3.button("🗑️", key=f"del_{r['phone']}"): db.delete_user_from_db(r['phone']); st.rerun()
        if "view_profile_phone" in st.session_state:
            st.markdown(f"#### Игры пользователя {st.session_state.view_profile_phone}")
            g = db.load_all_games()
            if not g.empty:
                st.dataframe(g[g["phone"].astype(str) == str(st.session_state.view_profile_phone)][["date", "venue", "winner", "status"]])
            if st.button("Закрыть профиль"): del st.session_state.view_profile_phone; st.rerun()
    with tm2:
        g = db.load_all_games()
        for idx, r in g.iterrows():
            col_g1, col_g2 = st.columns([5, 1])
            col_g1.write(f"📅 {r['date']} | 📍 {r['venue']} | 🏆 {r['winner']}")
            if col_g2.button("❌", key=f"dg_{r['game_id']}"): db.delete_game_from_db(r['game_id']); st.rerun()
    st.stop()

# --- ГЛАВНОЕ МЕНЮ ВЕДУЩЕГО ---
if st.session_state.page == "main_menu":
    st.title("🎲 Главное меню")
    if st.button("🚀 Создать новую игру", use_container_width=True):
        st.session_state.page = "setup_game"
        st.session_state.game_setup = {"city": "", "venue_name": "", "init_balance": 500}
        st.session_state.coefficients = {"country": 2, "grape": 3, "alc": 2}
        st.session_state.active_params = ["country", "grape", "alc"]
        st.session_state.players = []
        st.rerun()
        
    st.subheader("📜 Ваши прошедшие игры")
    games = db.load_all_games()
    if not games.empty:
        my_g = games[games["phone"].astype(str) == str(st.session_state.user_phone)]
        if not my_g.empty:
            # ПРАВКА 4: Красивая таблица с русскими названиями и подробным просмотром
            display_df = my_g[["date", "venue", "winner", "status"]].copy()
            display_df.columns = ["Дата проведения", "Место / Заведение", "🏆 Победитель", "Статус проведения"]
            st.dataframe(display_df, use_container_width=True)
            
            selected_game_idx = st.selectbox("🎯 Выберите игру для детального просмотра результатов:", options=my_g.index, format_func=lambda x: f"{my_g.loc[x, 'date']} - {my_g.loc[x, 'venue']}")
            if st.button("Посмотреть подробный отчет по игре"):
                st.session_state.view_game_json = my_g.loc[selected_game_idx, "full_json"]
                st.session_state.view_game_meta = my_g.loc[selected_game_idx]
                st.rerun()
        else: st.info("Игр пока нет")

    if "view_game_json" in st.session_state:
        st.markdown(f"### 📊 Детальный отчет: {st.session_state.view_game_meta['venue']}")
        p_list = json.loads(st.session_state.view_game_json)
        res_df = pd.DataFrame(p_list)
        if "name" in res_df.columns and "balance" in res_df.columns:
            res_df.columns = ["Имя Участника", "Финальный баланс фишек"]
            st.table(res_df.sort_values(by="Финальный баланс фишек", ascending=False))
        if st.button("Закрыть отчет"): del st.session_state.view_game_json; st.rerun()

# --- ЭКРАН 1: НАСТРОЙКИ МЕРОПРИЯТИЯ (ПРАВКА 5, 6, 7) ---
elif st.session_state.page == "setup_game":
    st.title("⚙️ Настройки мероприятия")
    
    # Город с умным выпадающим автозаполнением
    c_input = st.text_input("Введите город для поиска:", value=st.session_state.game_setup.get("city", ""))
    cities = geo.get_city_suggestions(c_input) if c_input else []
    city_final = st.selectbox("Выберите город из списка:", options=[c_input] + cities, index=0)
    st.session_state.game_setup["city"] = city_final

    # Заведение с умным поиском по базе компаний DaData
    v_input = st.text_input("Введите название ресторана/заведения:", value=st.session_state.game_setup.get("venue_name", ""))
    venues = geo.get_venue_suggestions(v_input, city=city_final) if v_input else []
    venue_final = st.selectbox("Выберите заведение из списка:", options=[v_input] + venues, index=0)
    st.session_state.game_setup["venue_name"] = venue_final
    
    st.markdown("---")
    st.subheader("💰 Игровые параметры и экономика")
    st.session_state.game_setup["init_balance"] = st.number_input("Стартовый баланс игроков (фишек)", value=500, step=50)
    
    st.write("Выберите играемые параметры вина в раундах:")
    c_p = st.checkbox("Страна происхождения", value="country" in st.session_state.active_params)
    g_p = st.checkbox("Сорт винограда", value="grape" in st.session_state.active_params)
    a_p = st.checkbox("Крепость / Алкоголь", value="alc" in st.session_state.active_params)
    st.session_state.active_params = [k for k, v in [("country", c_p), ("grape", g_p), ("alc", a_p)] if v]

    st.caption("Настройка множителей выигрыша (Коэффициенты):")
    st.session_state.coefficients["country"] = st.number_input("Коэффициент за Страну", value=2, min_value=1)
    st.session_state.coefficients["grape"] = st.number_input("Коэффициент за Сорт", value=3, min_value=1)
    st.session_state.coefficients["alc"] = st.number_input("Коэффициент за Алкоголь", value=2, min_value=1)

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Отмена"): st.session_state.page = "main_menu"; st.rerun()
    if col2.button("Далее ➡️"): st.session_state.page = "players_reg"; st.rerun()

# --- ЭКРАН 2: РЕГИСТРАЦИЯ ИГРОКОВ (ПРАВКА 6) ---
elif st.session_state.page == "players_reg":
    st.title("👥 Добавление участников")
    
    if "raw_names" not in st.session_state: st.session_state.raw_names = ""
    names_area = st.text_area("Введите имена гостей (каждое с новой строки):", value=st.session_state.raw_names)
    st.session_state.raw_names = names_area
    
    # ПРАВКА 7: Возможность перемешать порядок игроков перед стартом
    shuffle_on = st.checkbox("🎲 Перемешать порядок хода случайным образом")

    col1, col2 = st.columns(2)
    if col1.button("⬅️ Назад"): st.session_state.page = "setup_game"; st.rerun()
    if col2.button("Создать игру 🎰"):
        parsed_names = [n.strip() for n in names_area.split("\n") if n.strip()]
        if not parsed_names:
            st.error("Добавьте хотя бы одного игрока!"); st.stop()
        if shuffle_on: random.shuffle(parsed_names)
        
        st.session_state.players = [{"name": name, "balance": st.session_state.game_setup["init_balance"]} for name in parsed_names]
        st.session_state.game_id = str(int(time.time()))
        st.session_state.round_num = 1
        st.session_state.rounds_history = {}
        st.session_state.current_player_idx = 0
        st.session_state.page = "wine_params"
        db.save_local_backup(); st.rerun()

# --- ЭКРАН 3: ПАРАМЕТРЫ ВИНА ---
elif st.session_state.page == "wine_params":
    st.title(f"🍷 Раунд {st.session_state.round_num}: Выбор образца")
    
    if f"round_{st.session_state.round_num}" not in st.session_state.rounds_history:
        st.session_state.rounds_history[f"round_{st.session_state.round_num}"] = {"name": "", "country": "Россия", "grape": "Шардоне", "alc": 12.0}
    r_data = st.session_state.rounds_history[f"round_{st.session_state.round_num}"]
    
    w_name = st.text_input("Название / Этикетка вина", value=r_data["name"])
    w_country = st.selectbox("Эталонная страна", options=ALL_COUNTRIES, index=ALL_COUNTRIES.index(r_data["country"]) if r_data["country"] in ALL_COUNTRIES else 0)
    w_grape = st.selectbox("Эталонный сорт", options=ALL_GRAPES, index=ALL_GRAPES.index(r_data["grape"]) if r_data["grape"] in ALL_GRAPES else 0)
    w_alc = st.number_input("Эталонный % алкоголя", min_value=0.0, max_value=25.0, value=r_data["alc"], step=0.1)
    
    st.session_state.rounds_history[f"round_{st.session_state.round_num}"] = {"name": w_name, "country": w_country, "grape": w_grape, "alc": w_alc}
    
    if st.button("Принять образец и перейти к ставкам ➡️", use_container_width=True):
        st.session_state.current_player_idx = 0
        st.session_state.page = "bets_page"
        db.save_local_backup(); st.rerun()

# --- ЭКРАН 4: ПООЧЕРЕДНЫЙ ПРИЕМ СТАВОК (ПРАВКА 8: Поочередно как было) ---
elif st.session_state.page == "bets_page":
    p_idx = st.session_state.current_player_idx
    player = st.session_state.players[p_idx]
    
    st.title(f"🎰 Ставка игрока: {player['name']}")
    st.metric("Доступный баланс фишек:", f"{player['balance']}")
    
    b_val_key = f"bet_val_{player['name']}_{st.session_state.round_num}"
    b_country_key = f"bet_country_{player['name']}_{st.session_state.round_num}"
    b_grape_key = f"bet_grape_{player['name']}_{st.session_state.round_num}"
    b_alc_key = f"bet_alc_{player['name']}_{st.session_state.round_num}"
    
    if b_val_key not in st.session_state: st.session_state[b_val_key] = 50
    if b_country_key not in st.session_state: st.session_state[b_country_key] = ALL_COUNTRIES[0]
    if b_grape_key not in st.session_state: st.session_state[b_grape_key] = ALL_GRAPES[0]
    if b_alc_key not in st.session_state: st.session_state[b_alc_key] = 12.0

    col_m, col_i, col_p = st.columns([1, 2, 1])
    if col_m.button("➖ 50"): st.session_state[b_val_key] = max(0, st.session_state[b_val_key] - 50); st.rerun()
    chosen_bet = col_i.number_input("Сумма фишек в банк", min_value=0, max_value=int(player['balance']), value=int(st.session_state[b_val_key]))
    st.session_state[b_val_key] = chosen_bet
    if col_p.button("➕ 50"): st.session_state[b_val_key] = min(int(player['balance']), st.session_state[b_val_key] + 50); st.rerun()

    if "country" in st.session_state.active_params:
        st.session_state[b_country_key] = st.selectbox("Прогноз на страну", options=ALL_COUNTRIES, index=ALL_COUNTRIES.index(st.session_state[b_country_key]))
    if "grape" in st.session_state.active_params:
        st.session_state[b_grape_key] = st.selectbox("Прогноз на сорт винограда", options=ALL_GRAPES, index=ALL_GRAPES.index(st.session_state[b_grape_key]))
    if "alc" in st.session_state.active_params:
        st.session_state[b_alc_key] = st.number_input("Прогноз на процент алкоголя (погрешность ±0.5%)", value=float(st.session_state[b_alc_key]), step=0.1)

    st.markdown("---")
    col_nav1, col_nav2 = st.columns(2)
    
    if col_nav1.button("⬅️ Предыдущий игрок / Назад"):
        if p_idx > 0: st.session_state.current_player_idx -= 1
        else: st.session_state.page = "wine_params"
        st.rerun()
        
    if col_nav2.button("Следующий игрок ➡️" if p_idx < len(st.session_state.players) - 1 else "Рассчитать раунд 📊"):
        if p_idx < len(st.session_state.players) - 1:
            st.session_state.current_player_idx += 1
        else:
            st.session_state.page = "round_results"
        db.save_local_backup(); st.rerun()

# --- ЭКРАН 5: ИТОГИ РАУНДА И РАСЧЕТЫ ---
elif st.session_state.page == "round_results":
    st.title(f"📊 Результаты раунда {st.session_state.round_num}")
    target = st.session_state.rounds_history[f"round_{st.session_state.round_num}"]
    st.write(f"🟢 **Правильный ответ:** {target['name']} ({target['country']}, {target['grape']}, {target['alc']}% )")
    
    results = []
    for p in st.session_state.players:
        b_val = st.session_state.get(f"bet_val_{p['name']}_{st.session_state.round_num}", 0)
        b_country = st.session_state.get(f"bet_country_{p['name']}_{st.session_state.round_num}", "")
        b_grape = st.session_state.get(f"bet_grape_{p['name']}_{st.session_state.round_num}", "")
        b_alc = st.session_state.get(f"bet_alc_{p['name']}_{st.session_state.round_num}", 0.0)
        
        coef = 0
        hits = []
        if "country" in st.session_state.active_params and b_country == target["country"]:
            coef += st.session_state.coefficients["country"]; hits.append("Страна")
        if "grape" in st.session_state.active_params and b_grape == target["grape"]:
            coef += st.session_state.coefficients["grape"]; hits.append("Сорт")
        if "alc" in st.session_state.active_params and abs(float(b_alc) - float(target["alc"])) <= 0.5:
            coef += st.session_state.coefficients["alc"]; hits.append("Алкоголь")
            
        if coef > 0:
            p["balance"] += (b_val * coef)
            status = f"🎉 Сыграла: {', '.join(hits)}"
        else:
            p["balance"] -= b_val
            status = "❌ Не сыграла"
            
        results.append({"Игрок": p["name"], "Поставил фишек": b_val, "Статус": status, "Текущий баланс": p["balance"]})
        
    st.table(pd.DataFrame(results))
    
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Вернуться к ставкам"): st.session_state.page = "bets_page"; st.rerun()
    if col2.button("Следующий раунд 🍷"):
        st.session_state.round_num += 1
        st.session_state.page = "wine_params"
        db.save_local_backup(); st.rerun()
        
    if st.button("🏁 Завершить всю игру и сохранить", use_container_width=True):
        winner = max(st.session_state.players, key=lambda x: x["balance"])["name"]
        game_data = {
            "game_id": str(st.session_state.game_id),
            "phone": str(st.session_state.user_phone),
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "venue": f"{st.session_state.game_setup['city']}, {st.session_state.game_setup['venue_name']}",
            "winner": str(winner),
            "status": "Завершена",
            "full_json": json.dumps(st.session_state.players, ensure_ascii=False),
            "last_update": int(time.time())
        }
        db.save_game_to_db(game_data)
        db.clear_local_backup()
        st.session_state.page = "main_menu"
        st.success("Игра сохранена успешно!")
        time.sleep(1.5); st.rerun()

# --- ПРАВКА 2: ИНФОРМАЦИОННЫЙ ПОДВАЛ И СВЯЗЬ С РАЗРАБОТЧИКОМ ---
st.markdown("---")
with st.expander("💬 Связь с разработчиком"):
    st.write("**Заказчик системы:** ООО «Доктор Вайн»")
    st.write("**Бренд:** WINE & WHISKEY by simple (г. Оренбург, Северный проезд, д. 27А)")
    st.write("**Руководитель проекта / Ведущий сомелье:** winewhiskey56-ops")
    st.write("Вы можете выразить благодарность разработчику переводом на карту Т-Банка:")
    st.code("Реквизиты для перевода на карту: [Перевод по номеру карты в приложении]", language="text")
