import streamlit as st
import google.generativeai as genai
import random
import json
import os

    
BACKUP_FILE = "wine_casino_backup.json"

# --- ФУНКЦИИ ЗАЩИТЫ ОТ СБРОСА СЕССИИ ---
def save_game_state():
    """Сохраняет критически важные данные игры на диск"""
    state_to_save = {}
    for k in ["players", "page", "round_num", "current_wine", "bet_rows_count", "hints", "current_player_idx", "last_country", "last_grape", "shuffle_players", "shuffle_order"]:
        if k in st.session_state:
            state_to_save[k] = st.session_state[k]
    
    # Также сохраняем динамические ключи ставок (выборы в селектбоксах и инпутах)
    dynamic_keys = {k: st.session_state[k] for k in st.session_state.keys() if any(x in k for x in ["_v", "_a", "_c"])}
    state_to_save["dynamic_keys"] = dynamic_keys

    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f, ensure_ascii=False, indent=4)

def load_game_state():
    """Восстанавливает данные игры при обновлении страницы"""
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k != "dynamic_keys":
                        st.session_state[k] = v
                if "dynamic_keys" in data:
                    for dk, dv in data["dynamic_keys"].items():
                        st.session_state[dk] = dv
        except:
            pass

def clear_game_backup():
    """Удаляет файл бэкапа при полном перезапуске игры"""
    if os.path.exists(BACKUP_FILE):
        try: os.remove(BACKUP_FILE)
        except: pass

# Инициализируем восстановление до создания дефолтных ключей
load_game_state()

# --- 1. ДАННЫЕ И КОНФИГУРАЦИЯ ---
DATA = {
    "Сладость": ["сухое", "полусухое", "полусладкое", "сладкое"],
    "Страна": ["Россия", "ЮАР", "Австралия", "Аргентина", "США", "Новая Зеландия", "Чили", "Франция", "Италия", "Испания", "Австрия", "Германия", "Португалия", "Грузия", "Армения"],
    "Сорт винограда": ["Шардоне", "Рислинг", "Совиньон Блан", "Пино Гриджио", "Гевюрцтраминер", "Кортезе", "Гарганега", "Альбариньо", "Вердехо", "Грюнер Вельтлинер", "Каберне Совиньон", "Мерло", "Пино Нуар", "Сира/Шираз", "Темпранильо", "Санджовезе", "Мальбек", "Красностоп", "Саперави"],
    "Выдержка": ["выдержано в дубе", "не выдержано в дубе", "выдержано на осадке"]
}
COEFFS = {"Страна": 2, "Сорт винограда": 3, "Сладость": 2, "Выдержка": 3}

# --- 2. ИНИЦИАЛИЗАЦИЯ ИИ (ОСТАВЛЕНА ДЛЯ СОВМЕСТИМОСТИ) ---
def initialize_ai():
    try:
        if "GEMINI_API_KEY" not in st.secrets: return None, "Нет ключа"
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_models = ['models/gemini-1.5-flash', 'gemini-1.5-flash', 'models/gemini-2.5-flash', 'models/gemini-pro']
        sel = next((m for m in target_models if m in available_models), None)
        if not sel and available_models: sel = available_models[0]
        if sel: return genai.GenerativeModel(sel), f"ОК: {sel}"
        return None, "Доступные модели не найдены"
    except Exception as e: return None, f"Ошибка инициализации: {str(e)}"

if "ai_model" not in st.session_state:
    m, s = initialize_ai()
    st.session_state.ai_model, st.session_state.ai_status = m, s

# --- 3. ИНИЦИАЛИЗАЦИЯ БАЗОВЫХ КЛЮЧЕЙ СЕССИИ ---
keys = ["players", "page", "round_num", "current_wine", "bet_rows_count", "hints", "current_player_idx", "last_country", "last_grape", "shuffle_players", "shuffle_order"]
defs = [[], "registration", 1, {}, 1, {"country": "", "grape": ""}, 0, "—", "—", False, []]
for k, d in zip(keys, defs):
    if k not in st.session_state: st.session_state[k] = d

def header(show_logo=False):
    if show_logo:
        try: st.image("logo.png", width=250)
        except: st.write("### WINE & WHISKEY")
    st.markdown("---")

# --- 4. СТРАНИЦЫ ИГРЫ ---
def show_registration():
    header(True)
    st.markdown("<h2 style='text-align: center;'>📝 Регистрация</h2>", unsafe_allow_html=True)
    
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("Имя игрока:")
        if st.form_submit_button("Добавить", use_container_width=True) and name.strip():
            # Записываем ID (номер по часовой стрелке) прямо в структуру игрока
            player_num = len(st.session_state.players) + 1
            st.session_state.players.append({
                "id": player_num,
                "name": name.strip(), 
                "balance": 150, 
                "round_bets": [], 
                "balance_at_start": 150
            })
            save_game_state()
            st.rerun()
            
    # Вынесли галочку перемешивания из формы, чтобы ведущий настраивал её в любой момент
    st.session_state.shuffle_players = st.checkbox(
        "🔀 Перемешивать участников каждый раунд", 
        value=st.session_state.shuffle_players,
        help="Очередность ходов будет случайной в каждом раунде, чтобы гости не списывали ставки друг у друга."
    )
    
    if st.session_state.players:
        st.markdown("### Список игроков (по часовой стрелке):")
        for p in st.session_state.players: 
            st.write(f"Игрок №{p['id']}: **{p['name']}**")
            
        if st.button("Начать игру ➔", use_container_width=True, type="primary"):
            st.session_state.page = "setup"
            # Генерируем порядок для 1 раунда
            if st.session_state.shuffle_players:
                st.session_state.shuffle_order = random.sample(range(len(st.session_state.players)), len(st.session_state.players))
            else:
                st.session_state.shuffle_order = list(range(len(st.session_state.players)))
            save_game_state()
            st.rerun()

def show_setup():
    header()
    st.markdown(f"### 🍷 Раунд №{st.session_state.round_num}")
    st.markdown("#### Выберите или введите параметры загаданного вина:")
    
    c1, c2 = st.columns(2)
    with c1:
        # --- ПОЛЕ СТРАНА ---
        old_country = st.session_state.current_wine.get("Страna_raw", "—")
        country_select = st.selectbox("Страна:", ["—"] + DATA["Страна"] + ["📝 Свой вариант..."], index=0 if old_country == "—" else (["—"] + DATA["Страна"] + ["📝 Свой вариант..."]).index(old_country) if old_country in (["—"] + DATA["Страна"] + ["📝 Свой вариант..."]) else len(["—"] + DATA["Страна"]))
        
        if country_select == "📝 Свой вариант...":
            country_val = st.text_input("Введите страну вручную:", value=st.session_state.current_wine.get("Страна", "")).strip()
        else:
            country_val = country_select
            
        st.session_state.current_wine["Страна"] = country_val
        st.session_state.current_wine["Страna_raw"] = country_select

        # --- ПОЛЕ СОРТ ВИНОГРАДА ---
        old_grape = st.session_state.current_wine.get("Сорт_raw", "—")
        grape_select = st.selectbox("Сорт винограда:", ["—"] + DATA["Сорт винограда"] + ["📝 Свой вариант..."], index=0 if old_grape == "—" else (["—"] + DATA["Сорт винограда"] + ["📝 Свой вариант..."]).index(old_grape) if old_grape in (["—"] + DATA["Сорт винограда"] + ["📝 Свой вариант..."]) else len(["—"] + DATA["Сорт винограда"]))
        
        if grape_select == "📝 Свой вариант...":
            grape_val = st.text_input("Введите сорт вручную:", value=st.session_state.current_wine.get("Сорт винограда", "")).strip()
        else:
            grape_val = grape_select
            
        st.session_state.current_wine["Сорт винограда"] = grape_val
        st.session_state.current_wine["Сорт_raw"] = grape_select

    with c2:
        # --- ПОЛЕ СЛАДОСТЬ ---
        old_sweet = st.session_state.current_wine.get("Сладость", "—")
        sweet_val = st.selectbox("Сладость:", ["—"] + DATA["Сладость"])
        st.session_state.current_wine["Сладость"] = sweet_val

        # --- ПОЛЕ ВЫДЕРЖКА ---
        old_age = st.session_state.current_wine.get("Выдержка", "—")
        age_val = st.selectbox("Выдержка:", ["—"] + DATA["Выдержка"])
        st.session_state.current_wine["Выдержка"] = age_val
        
    save_game_state()
                
    st.markdown("---")
    if st.button("К ставкам ➔", use_container_width=True, type="primary"):
        # Если ведущий забыл заполнить ручные поля, берем прочерк
        if not st.session_state.current_wine.get("Страна"): st.session_state.current_wine["Страна"] = "—"
        if not st.session_state.current_wine.get("Сорт винограда"): st.session_state.current_wine["Сорт винограда"] = "—"
        
        for p in st.session_state.players: 
            p['balance_at_start'] = p['balance']
        st.session_state.page = "betting"
        st.session_state.current_player_idx = 0
        st.session_state.bet_rows_count = 1
        save_game_state()
        st.rerun()

def show_betting():
    header()
    
    # Определяем, какой игрок ходит согласно сохраненному порядку (обычному или перемешанному)
    current_seat_idx = st.session_state.shuffle_order[st.session_state.current_player_idx]
    player = st.session_state.players[current_seat_idx]
    p_idx = current_seat_idx # внутренний индекс для сохранения уникальных ключей ввода
    
    spent, valid = 0, []
    
    for i in range(st.session_state.bet_rows_count):
        cat = st.session_state.get(f"p{p_idx}_c{i}", "Сладость")
        val = st.session_state.get(f"p{p_idx}_v{i}", "—")
        amt = st.session_state.get(f"p{p_idx}_a{i}", 0)
        if val != "—" and amt > 0: 
            spent += amt
            valid.append({"cat": cat, "val": val, "amt": amt})

    # Вывод Имени в формате: Игрок №X: Имя
    st.markdown(f"## 👤 Игрок №{player['id']}: {player['name']}")
    st.markdown(f"### Фишки: {player['balance'] - spent}")
    
    for i in range(st.session_state.bet_rows_count):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: 
            chosen_cat = st.selectbox("Тип", list(COEFFS.keys()), key=f"p{p_idx}_c{i}", on_change=save_game_state)
        with col2: 
            # Динамически подтягиваем варианты ставок. 
            # Если ведущий ввел страну/сорт руками, временно добавляем этот кастомный вариант в выпадающий список игрока
            current_options = ["—"] + DATA[chosen_cat]
            correct_custom_val = st.session_state.current_wine.get(chosen_cat, "—")
            if correct_custom_val != "—" and correct_custom_val not in current_options:
                current_options.append(correct_custom_val)
                
            st.selectbox("Ставка", current_options, key=f"p{p_idx}_v{i}", on_change=save_game_state)
        with col3: 
            st.number_input("Сумма", min_value=0, step=10, key=f"p{p_idx}_a{i}", on_change=save_game_state)
            
        if i == st.session_state.bet_rows_count - 1 and st.session_state.get(f"p{p_idx}_v{i}", "—") != "—" and st.session_state.get(f"p{p_idx}_a{i}", 0) > 0:
            st.session_state.bet_rows_count += 1
            save_game_state()
            st.rerun()
            
    if st.button("Принять", use_container_width=True, type="primary"):
        player['round_bets'], player['balance'] = valid, player['balance'] - spent
        if st.session_state.current_player_idx < len(st.session_state.players) - 1:
            st.session_state.current_player_idx += 1
            st.session_state.bet_rows_count = 1
        else: 
            st.session_state.page = "results"
        save_game_state()
        st.rerun()

def show_results():
    header()
    correct = st.session_state.current_wine
    st.markdown("## 📊 Итоги Раунда")
    
    # Красивое отображение загаданного вина
    display_answers = [f"{k}: {v}" for k, v in correct.items() if v != "—" and "raw" not in k]
    st.info("🎯 Ответ: " + " | ".join(display_answers))
    
    # Расчет результатов происходит один раз в нижнем регистре для поддержки ручного ввода
    if f"calculated_r_{st.session_state.round_num}" not in st.session_state:
        for p in st.session_state.players:
            win = 0
            for b in p['round_bets']:
                hit = str(b['val']).lower().strip() == str(correct.get(b['cat'])).lower().strip()
                win += b['amt'] * COEFFS[b['cat']] if hit else 0
            p['balance'] += win
        st.session_state[f"calculated_r_{st.session_state.round_num}"] = True
        save_game_state()

    # Показываем результаты в порядке Игроков №1, №2, №3...
    for p in sorted(st.session_state.players, key=lambda x: x['id']):
        win_sum = 0
        details = []
        for b in p['round_bets']:
            hit = str(b['val']).lower().strip() == str(correct.get(b['cat'])).lower().strip()
            res = b['amt'] * COEFFS[b['cat']] if hit else 0
            win_sum += res
            details.append(f"<p style='color:{'#28a745' if hit else '#dc3545'}; margin:0;'>{'✅' if hit else '❌'} {b['cat']}: {b['val']} | {b['amt']} ➔ {res}</p>")
        
        with st.expander(f"👤 Игрок №{p['id']}: {p['name']} | Выигрыш: +{win_sum}"):
            st.markdown("".join(details) or "Ставок нет", unsafe_allow_html=True)
            st.write(f"Баланс: {p['balance']}")
            
    st.markdown("---")
    
    # Кнопка СЛЕДУЮЩИЙ РАУНД на самом видном месте
    if st.button("След. раунд 🍷", use_container_width=True, type="primary"):
        st.session_state.round_num += 1
        st.session_state.page = "setup"
        st.session_state.current_wine = {}
        st.session_state.hints = {"country": "", "grape": ""}
        st.session_state.last_country, st.session_state.last_grape = "—", "—"
        
        # Если включено перемешивание, генерируем новую уникальную последовательность для следующего раунда
        if st.session_state.shuffle_players:
            st.session_state.shuffle_order = random.sample(range(len(st.session_state.players)), len(st.session_state.players))
        else:
            st.session_state.shuffle_order = list(range(len(st.session_state.players)))
            
        for k in list(st.session_state.keys()):
            if any(x in k for x in ["_v", "_a", "_c"]): del st.session_state[k]
        save_game_state()
        st.rerun()
        
   # Кнопка ЗАВЕРШИТЬ ИГРУ опущена вниз, уменьшена и защищена окном подтверждения
    st.write("")
    c1, c2 = st.columns([2, 1])
    with c2:
        with st.popover("🚫 Завершить игру", use_container_width=True):
            st.warning("Вы уверены, что хотите закончить игру и перейти к финальным результатам?")
            if st.button("Да, подтверждаю", use_container_width=True, type="primary"):
                st.session_state.page = "final"
                save_game_state()
                st.rerun()

def show_final():
    header()
    st.markdown("<h1 style='text-align: center;'>🏆 Финал</h1>", unsafe_allow_html=True)
    
    # Сортируем игроков по финальному балансу фишек
    for i, p in enumerate(sorted(st.session_state.players, key=lambda x: x['balance'], reverse=True)):
        st.write(f"**{i+1}. Игрок №{p['id']}: {p['name']}** — {p['balance']} фишек")
        
    st.markdown("---")
    if st.button("Заново 🔄", use_container_width=True, type="primary"):
        clear_game_backup()
        st.session_state.clear()
        st.rerun()

# --- 5. РОУТИНГ ---
if st.session_state.page == "registration": show_registration()
elif st.session_state.page == "setup": show_setup()
elif st.session_state.page == "betting": show_betting()
elif st.session_state.page == "results": show_results()
elif st.session_state.page == "final": show_final()
