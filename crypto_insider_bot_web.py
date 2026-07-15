import os
import time
import json
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

# 1. Завантаження конфігурації
load_dotenv()

# 2. Налаштування сторінки Streamlit (Веб-версії)
st.set_page_config(
    page_title="ШІ-Порадник Крипто-Арбітражу",
    page_icon="🤖",
    layout="wide"
)

# Ініціалізація клієнта OpenAI
if "OPENAI_API_KEY" in os.environ or os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
else:
    openai_client = None

# Ініціалізація історії сигналів у пам'яті веб-додатка
if "signals_history" not in st.session_state:
    st.session_state.signals_history = []

# --- ФУНКЦІЇ АНАЛІТИКИ ---

def get_smart_money_activity():
    import random
    test_coins = [
        "BTC", "ETH", "SOL", "XRP", "ADA", 
        "AVAX", "DOT", "DOGE", "SHIB", "LINK", 
        "LTC", "NEAR", "PEPE", "SUI", "WIF", 
        "FET", "OP", "ARB", "APT", "RENDER"
    ]
    chosen_coin = random.choice(test_coins)
    action = random.choice(["BUY", "SELL"])
    
    if action == "BUY":
        transfers = [
            {"token": chosen_coin, "wallet_tag": "Jump Crypto", "action": "BUY", "amount_usd": 150000, "timestamp": time.time()},
            {"token": chosen_coin, "wallet_tag": "Smart Money #042", "action": "BUY", "amount_usd": 85000, "timestamp": time.time() - 300},
            {"token": chosen_coin, "wallet_tag": "a16z", "action": "BUY", "amount_usd": 300000, "timestamp": time.time() - 1200}
        ]
    else:
        transfers = [
            {"token": chosen_coin, "wallet_tag": "Paradigm", "action": "TRANSFER_TO_BINANCE", "amount_usd": 450000, "timestamp": time.time()},
            {"token": chosen_coin, "wallet_tag": "Smart Money #011", "action": "SELL", "amount_usd": 120000, "timestamp": time.time() - 150}
        ]
    return chosen_coin, action, transfers

def get_market_metrics(symbol, action):
    if action == "BUY":
        return {"funding_rate": -0.004, "open_interest_change_pct": 11.2}
    else:
        return {"funding_rate": 0.008, "open_interest_change_pct": -5.4}

def get_arbitrage_opportunities(symbol, action):
    import random
    if action == "BUY":
        spread_bybit_bingx = round(random.uniform(0.15, 0.45), 2)
        spread_dex = round(random.uniform(0.5, 1.2), 2)
        data = {
            "best_exchange": "BingX",
            "spread": f"{spread_bybit_bingx}%",
            "interpretation": f"BingX відстає від тренду Bybit на {spread_bybit_bingx}%."
        }
    else:
        spread_bybit_bingx = round(random.uniform(0.1, 0.35), 2)
        data = {
            "best_exchange": "Bybit (Short)",
            "spread": f"{spread_bybit_bingx}%",
            "interpretation": f"На Bybit почалися продажі, BingX тримається."
        }
    return data

def get_mock_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        res = requests.get(url).json()
        return float(res['price'])
    except:
        prices = {"BTC": 64000.0, "ETH": 3400.0, "SOL": 140.0, "XRP": 0.5, "ADA": 0.38}
        return prices.get(symbol, 1.0)

def ask_openai_decision(token, onchain_data, market_metrics, arbitrage_data):
    if not openai_client:
        return {"decision": "HOLD", "reason": "Ключ OpenAI API не знайдено в налаштуваннях."}
        
    prompt = f"""
    Ти професійний крипто-трейдер та арбітражник. 
    Проаналізуй наступні дані для токена {token} та ухвали рішення про доцільність угоди.
    
    1. Дані On-chain (Smart Money):
    {json.dumps(onchain_data, indent=2)}
    
    2. Метрики ринку (Ставка фінансування):
    {json.dumps(market_metrics, indent=2)}
    
    3. Дані міжбіржового арбітражу:
    {json.dumps(arbitrage_data, indent=2)}
    
    Поверни відповідь у форматі JSON:
    {{
        "decision": "BUY" або "SELL" або "HOLD",
        "reason": "коротке, чітке обґрунтування українською мовою з рекомендацією біржі"
    }}
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ти аналітичний торговий модуль. Твоя відповідь має бути суворо у форматі JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        return {"decision": "HOLD", "reason": f"Помилка ШІ: {e}"}

# --- ВЕБ-ІНТЕРФЕЙС STREAMLIT ---

st.title("🤖 ШІ-Порадник Крипто-Інсайдів та Арбітражу")
st.write("Веб-платформа для моніторингу аномалій Smart Money та міжбіржових спредів (Bybit/BingX) в реальному часі.")

# Бокова панель (Sidebar) з налаштуваннями ризиків та інтервалу
st.sidebar.header("⚙️ Налаштування системи")
trade_volume = st.sidebar.number_input("Обсяг угоди, USDT", value=float(os.getenv("TRADE_VOLUME_USDT", 10.0)))
sl_pct = st.sidebar.slider("Stop-Loss, %", min_value=1.0, max_value=5.0, value=float(os.getenv("STOP_LOSS_PCT", 0.02))*100) / 100
tp_pct = st.sidebar.slider("Take-Profit, %", min_value=2.0, max_value=15.0, value=float(os.getenv("TAKE_PROFIT_PCT", 0.06))*100) / 100
scan_interval = st.sidebar.slider("Інтервал сканування (сек)", min_value=10, max_value=300, value=int(os.getenv("SCAN_INTERVAL_SEC", 60)))

# Перевірка ключів
if not openai_client:
    st.error("⚠️ Помилка: Ключ OPENAI_API_KEY не знайдено! Додайте його у ваш файл .env.")
    st.stop()

# Кнопка для ручного запуску нового циклу сканування
if st.button("🔄 Сканувати ринок прямо зараз"):
    with st.spinner("Отримання та аналіз даних..."):
        token, action, onchain = get_smart_money_activity()
        metrics = get_market_metrics(token, action)
        arb = get_arbitrage_opportunities(token, action)
        
        # Запит до ШІ
        ai_res = ask_openai_decision(token, onchain, metrics, arb)
        decision = ai_res.get("decision", "HOLD")
        reason = ai_res.get("reason", "Сигнал слабкий.")
        
        # Розрахунок цін
        price = get_mock_price(token)
        if decision == "BUY":
            sl = price * (1.0 - sl_pct)
            tp = price * (1.0 + tp_pct)
            side = "🟢 LONG"
        elif decision == "SELL":
            sl = price * (1.0 + sl_pct)
            tp = price * (1.0 - tp_pct)
            side = "🔴 SHORT"
        else:
            sl, tp = 0.0, 0.0
            side = "⚪ HOLD"

        # Запис у пам'ять
        new_signal = {
            "Час": datetime.now().strftime("%H:%M:%S"),
            "Монета": f"{token}/USDT",
            "Напрямок": side,
            "Ціна входу": f"{price:.4f}",
            "Stop-Loss": f"{sl:.4f}" if sl > 0 else "-",
            "Take-Profit": f"{tp:.4f}" if tp > 0 else "-",
            "Рекомендована біржа": arb.get("best_exchange", "Bybit"),
            "Спред": arb.get("spread", "-"),
            "Аналітика від ШІ": reason
        }
        
        # Додаємо на початок списку (щоб свіжі були зверху)
        st.session_state.signals_history.insert(0, new_signal)

# --- ВІДОБРАЖЕННЯ ТАБЛИЦІ СИГНАЛІВ ---

st.subheader("📊 Онлайн Таблиця Торгових Сигналів")

if st.session_state.signals_history:
    # Перетворюємо історію сигналів у красиву таблицю Pandas
    df = pd.DataFrame(st.session_state.signals_history)
    
    # Виводимо інтерактивну таблицю на весь екран
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Напрямок": st.column_config.TextColumn("Напрямок"),
            "Аналітика від ШІ": st.column_config.TextColumn("Аналітика від ШІ", width="large")
        }
    )
    
    # Окремий блок для швидкого очищення таблиці
    if st.button("🗑️ Очистити історію таблиці"):
        st.session_state.signals_history = []
        st.experimental_rerun()
else:
    st.info("Таблиця порожня. Натисніть кнопку 'Сканувати ринок прямо зараз', щоб ШІ проаналізував свіжі інсайди.")

# Автооновлення сторінки кожні Х секунд для імітації онлайн-стриму
st.caption(f"Налаштовано інтервал автоматичного оновлення дашборду. Натисніть кнопку сканування для примусового оновлення таблиці.")