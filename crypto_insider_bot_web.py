import os
import time
import json
import requests
import pandas as pd
import streamlit as st
import random
from datetime import datetime, timedelta
from openai import OpenAI
from streamlit_autorefresh import st_autorefresh

# 1. Завантаження конфігурації
from dotenv import load_dotenv
load_dotenv()

# 2. Налаштування сторінки Streamlit
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

# Ініціалізація історії сигналів у пам'яті додатка
if "signals_history" not in st.session_state:
    st.session_state.signals_history = []

# --- СИНХРОНІЗОВАНІ ФУНКЦІЇ АНАЛІТИКИ (ПРИВ'ЯЗКА ДО ХВИЛИНИ ЧАСУ) ---

def get_synchronized_seed():
    """ 
    Генерує унікальне число (seed) на основі поточної хвилини.
    Це гарантує, що всі вікна, запущені в одну і ту саму хвилину,
    отримають абсолютно однакові випадкові дані.
    """
    now = datetime.now()
    # Створюємо seed у форматі РРРРММДДГГХХ (наприклад, 202607161120)
    return int(now.strftime("%Y%m%d%H%M"))

def get_smart_money_activity():
    # Фіксуємо seed для цієї хвилини
    seed_value = get_synchronized_seed()
    random.seed(seed_value)
    
    test_coins = [
        "BTC", "ETH", "SOL", "XRP", "ADA", 
        "AVAX", "DOT", "DOGE", "SHIB", "LINK", 
        "LTC", "NEAR", "PEPE", "SUI", "WIF", 
        "FET", "OP", "ARB", "APT", "RENDER"
    ]
    chosen_coin = random.choice(test_coins)
    action = random.choice(["BUY", "SELL"])
    
    # Генерація фіксованих транзакцій на основі тієї ж хвилини
    amount_1 = random.randint(100, 500) * 1000
    amount_2 = random.randint(50, 200) * 1000
    
    if action == "BUY":
        transfers = [
            {"token": chosen_coin, "wallet_tag": "Jump Crypto", "action": "BUY", "amount_usd": amount_1, "timestamp": time.time()},
            {"token": chosen_coin, "wallet_tag": "Smart Money #042", "action": "BUY", "amount_usd": amount_2, "timestamp": time.time() - 300}
        ]
    else:
        transfers = [
            {"token": chosen_coin, "wallet_tag": "Paradigm", "action": "TRANSFER_TO_BINANCE", "amount_usd": amount_1, "timestamp": time.time()},
            {"token": chosen_coin, "wallet_tag": "Smart Money #011", "action": "SELL", "amount_usd": amount_2, "timestamp": time.time() - 150}
        ]
    
    # Обов'язково скидаємо генератор у випадковий стан для інших системних бібліотек
    random.seed()
    return chosen_coin, action, transfers

def get_market_metrics(symbol, action):
    # Прив'язуємо метрики до seed хвилини
    seed_value = get_synchronized_seed()
    random.seed(seed_value + 1)
    
    if action == "BUY":
        funding = round(random.uniform(-0.005, -0.001), 4)
        oi_change = round(random.uniform(5.0, 15.0), 1)
    else:
        funding = round(random.uniform(0.003, 0.01), 4)
        oi_change = round(random.uniform(-8.0, -2.0), 1)
        
    random.seed()
    return {"funding_rate": funding, "open_interest_change_pct": oi_change}

def get_arbitrage_opportunities(symbol, action):
    seed_value = get_synchronized_seed()
    random.seed(seed_value + 2)
    
    spread_bybit_bingx = round(random.uniform(0.1, 0.5), 2)
    
    if action == "BUY":
        data = {
            "best_exchange": "BingX",
            "spread": f"{spread_bybit_bingx}%",
            "interpretation": f"BingX відстає від тренду Bybit на {spread_bybit_bingx}%."
        }
    else:
        data = {
            "best_exchange": "Bybit (Short)",
            "spread": f"{spread_bybit_bingx}%",
            "interpretation": f"На Bybit продажі, BingX тримається."
        }
    random.seed()
    return data

def get_mock_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        res = requests.get(url).json()
        return float(res['price'])
    except:
        prices = {"BTC": 64000.0, "ETH": 3400.0, "SOL": 140.0, "XRP": 1.11, "ADA": 0.38}
        return prices.get(symbol, 1.0)

def ask_openai_decision(token, onchain_data, market_metrics, arbitrage_data):
    if not openai_client:
        return {"decision": "HOLD", "reason": "Ключ OpenAI API не знайдено."}
        
    prompt = f"""
    Ти професійний крипто-трейдер та арбітражник. 
    Проаналізуй наступні дані для токена {token} та ухвали рішення про доцільність угоди.
    
    1. Дані On-chain: {json.dumps(onchain_data)}
    2. Метрики ринку: {json.dumps(market_metrics)}
    3. Дані арбітражу: {json.dumps(arbitrage_data)}
    
    Поверни відповідь у форматі JSON:
    {{
        "decision": "BUY" або "SELL" або "HOLD",
        "reason": "коротке, чітке обґрунтування українською мовою"
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

def perform_scan(sl_pct, tp_pct):
    token, action, onchain = get_smart_money_activity()
    metrics = get_market_metrics(token, action)
    arb = get_arbitrage_opportunities(token, action)
    
    ai_res = ask_openai_decision(token, onchain, metrics, arb)
    decision = ai_res.get("decision", "HOLD")
    reason = ai_res.get("reason", "Сигнал слабкий.")
    
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

    # Заокруглюємо час сигналу до початку поточної хвилини, 
    # щоб час відображення в усіх таблицях також повністю збігався
    sync_time = datetime.now().replace(second=0, microsecond=0).strftime("%H:%M:%S")

    new_signal = {
        "Час": sync_time,
        "Монета": f"{token}/USDT",
        "Напрямок": side,
        "Ціна входу": f"{price:.4f}",
        "Stop-Loss": f"{sl:.4f}" if sl > 0 else "-",
        "Take-Profit": f"{tp:.4f}" if tp > 0 else "-",
        "Рекомендована біржа": arb.get("best_exchange", "Bybit"),
        "Спред": arb.get("spread", "-"),
        "Аналітика від ШІ": reason
    }
    
    # Захист від дублікатів: додаємо сигнал лише якщо такого самого за цей час ще немає в історії
    if not any(s["Час"] == sync_time and s["Монета"] == f"{token}/USDT" for s in st.session_state.signals_history):
        st.session_state.signals_history.insert(0, new_signal)

# --- ВЕБ-ІНТЕРФЕЙС STREAMLIT ---

st.title("🤖 ШІ-Порадник Крипто-Інсайдів та Арбітражу")
st.write("Веб-платформа для моніторингу аномалій Smart Money та міжбіржових спредів (Bybit/BingX) в реальному часі.")

# Бокова панель
st.sidebar.header("⚙️ Налаштування системи")
trade_volume = st.sidebar.number_input("Обсяг угоди, USDT", value=10.0)
sl_pct = st.sidebar.slider("Stop-Loss, %", min_value=1.0, max_value=5.0, value=2.0) / 100
tp_pct = st.sidebar.slider("Take-Profit, %", min_value=2.0, max_value=15.0, value=6.0) / 100

# Вибір режиму оновлення
st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 Увімкнути автоматичне оновлення", value=True)
scan_interval = st.sidebar.slider("Інтервал сканування (сек)", min_value=10, max_value=300, value=60)

if not openai_client:
    st.error("⚠️ Помилка: Ключ OPENAI_API_KEY не знайдено!")
    st.stop()

# НАДІЙНА ЛОГІКА АВТООНОВЛЕННЯ
if auto_refresh:
    # Запускаємо таймер оновлення сторінки
    st_autorefresh(interval=scan_interval * 1000, key="crypto_bot_refresh")
    
    if "last_scan_time" not in st.session_state:
        st.session_state.last_scan_time = time.time()
        perform_scan(sl_pct, tp_pct)
        
    current_time = time.time()
    if current_time - st.session_state.last_scan_time >= scan_interval:
        st.session_state.last_scan_time = current_time
        perform_scan(sl_pct, tp_pct)

# Кнопка примусового сканування
if st.button("⚡ Примусове сканування прямо зараз"):
    with st.spinner("Аналіз даних..."):
        perform_scan(sl_pct, tp_pct)
        st.session_state.last_scan_time = time.time()
        st.rerun()

# --- ВІДОБРАЖЕННЯ ТАБЛИЦІ СИГНАЛІВ ---
st.subheader("📊 Онлайн Таблиця Торгових Сигналів")

if st.session_state.signals_history:
    df = pd.DataFrame(st.session_state.signals_history)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Напрямок": st.column_config.TextColumn("Напрямок"),
            "Аналітика від ШІ": st.column_config.TextColumn("Аналітика від ШІ", width="large")
        }
    )
    
    if st.button("🗑️ Очистити історію таблиці"):
        st.session_state.signals_history = []
        st.rerun()
else:
    st.info("Таблиця порожня. Натисніть кнопку 'Примусове сканування' або зачекайте запуску таймера.")