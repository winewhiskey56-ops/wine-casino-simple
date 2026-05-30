import streamlit as st

def calculate_balances():
    """Полный математический пересчет всей игры с 0-го раунда на основе истории"""
    setup = st.session_state.get("game_setup", {})
    start_balance = setup.get("start_balance", 150)
    coeffs = setup.get("coeffs", {})
    
    # Сбрасываем балансы всех игроков на стартовые
    for p in st.session_state.players:
        p["balance"] = start_balance
        
    # Пошагово проходим по завершенным раундам и вычисляем результаты
    for r_idx, r_data in enumerate(st.session_state.rounds_history):
        correct_wine = r_data["wine"]
        
        for p in st.session_state.players:
            # Ищем ставки этого игрока в данном раунде
            p_bets = r_data["bets"].get(str(p["id"]), [])
            spent = sum(b["amt"] for b in p_bets)
            
            # Списываем поставленное
            p["balance"] -= spent
            
            # Считаем выигрыш
            win = 0
            for b in p_bets:
                cat = b["cat"]
                val = str(b["val"]).lower().strip()
                ans = str(correct_wine.get(cat, "")).lower().strip()
                
                if cat == "Процент алкоголя":
                    try:
                        hit = abs(float(val) - float(ans)) <= 0.5
                    except: hit = False
                else:
                    hit = (val == ans and val != "—")
                    
                if hit:
                    win += b["amt"] * coeffs.get(cat, 2)
            
            p["balance"] += win
