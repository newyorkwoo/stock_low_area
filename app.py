import streamlit as st
import streamlit.components.v1 as components
import json
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="歷史指數互動式看板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
.block-container { padding-top: 0 !important; padding-bottom: 0 !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner="資料更新中，請稍候...")
def fetch_market_data():
    def calculate_rsi(data, window=60):
        delta = data['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        ema_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        ema_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        rs = ema_gain / ema_loss
        return 100 - (100 / (1 + rs))

    def prepare(symbol):
        start = "2007-01-01"
        end = (datetime.now() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        df = yf.Ticker(symbol).history(start=start, end=end)
        vix = yf.Ticker("^VIX").history(start=start, end=end)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        if vix.index.tz is not None:
            vix.index = vix.index.tz_localize(None)
        df = df.sort_index()
        df['RSI60'] = calculate_rsi(df, 60)
        df = df.join(vix['Close'].rename('VIX'), how='left')
        df['VIX'] = df['VIX'].ffill()
        df = df.dropna(subset=['Close', 'VIX', 'RSI60'])
        result = []
        for date, row in df.iterrows():
            result.append([
                date.strftime('%Y-%m-%d'),
                round(float(row['Open']), 2),
                round(float(row['Close']), 2),
                round(float(row['Low']), 2),
                round(float(row['High']), 2),
                int(row['Volume']) if not pd.isna(row['Volume']) else 0,
                round(float(row['VIX']), 2),
                round(float(row['RSI60']), 2)
            ])
        return result

    return prepare("^TWII"), prepare("^IXIC")


twii_data, nasdaq_data = fetch_market_data()

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

twii_json = json.dumps(twii_data)
nasdaq_json = json.dumps(nasdaq_data)

# Replace the fetch-based loadData with inline data injection
old_load = (
    "    // ─── 資料載入 ──────────────────────────────────────────────────────────────\n"
    "    async function loadData(market) {\n"
    "        document.getElementById('loading').style.display = 'flex';\n"
    "        try {\n"
    "            const response = await fetch(`${market}_data.json?t=${new Date().getTime()}`);\n"
    "            if (!response.ok) throw new Error('Data file not found.');\n"
    "            const data = await response.json();\n"
    "            renderChart(data, market === 'twii' ? '台灣加權指數 (^TWII)' : '那斯達克指數 (^IXIC)');\n"
    "        } catch (error) {\n"
    "            console.error('Error fetching data:', error);\n"
    '            alert("未找到數據文件。請等待 1~2 分鐘後重新整理頁面。");\n'
    "        } finally {\n"
    "            document.getElementById('loading').style.display = 'none';\n"
    "        }\n"
    "    }"
)

new_load = (
    "    const _DATA = { twii: " + twii_json + ", nasdaq: " + nasdaq_json + " };\n"
    "    async function loadData(market) {\n"
    "        document.getElementById('loading').style.display = 'flex';\n"
    "        try {\n"
    "            const titles = { twii: '台灣加權指數 (^TWII)', nasdaq: '那斯達克指數 (^IXIC)' };\n"
    "            renderChart(_DATA[market], titles[market]);\n"
    "        } finally {\n"
    "            document.getElementById('loading').style.display = 'none';\n"
    "        }\n"
    "    }"
)

html = html.replace(old_load, new_load)

components.html(html, height=960, scrolling=False)
