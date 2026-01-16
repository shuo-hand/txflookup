import streamlit as st
import pandas as pd
import requests as r
import urllib3
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import google.generativeai as genai
import twstock
import os

# --- 基礎與連線設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
DATA_FILE = "tx_history_database.csv"
WEIGHTED_IDS = ['2330', '2317', '2454', '2382', '2308', '2881', '2882', '3711', '2412', '2303', '2891', '1301', '2886', '2603', '2892']

@st.cache_resource
def init_env():
    twstock.__update_codes() # 更新股票代碼
    return True

init_env()

# --- 數據抓取模組 ---

def get_turnover_top_15():
    """抓取今日成交值前 15 名的股票代號"""
    url = "https://www.twse.com.tw/exchangeReport/TWT4U?response=json"
    try:
        res = r.get(url, timeout=5).json()
        df = pd.DataFrame(res['data'], columns=res['fields'])
        return df['證券代號'].head(15).tolist()
    except:
        # 若抓取失敗，回傳一組預設熱門股代碼
        return ['2330', '2317', '2603', '2382', '2609', '3231', '2353', '2454', '1513', '1519', '2303', '2301', '3037', '2371', '2618']

def get_stocks_kbar_data(stock_ids):
    """利用 twstock 獲取多檔股票的即時 K 棒數據"""
    try:
        data = twstock.realtime.get(stock_ids)
        if not data['success']:
            raise ValueError("twstock 獲取失敗")
        return data
    except Exception as e:
        st.error(f"❌ 股票即時數據獲取失敗: {e}")
        return None

# --- UI 組件：單根 K 棒看板 (模擬 index.tsx 視覺效果) ---

def render_kbar_component(stock_info):
    """渲染單根股票 K 棒組件"""
    if not stock_info['success']:
        return st.caption("N/A")
    
    rt = stock_info['realtime']
    name = stock_info['info']['name']
    code = stock_info['info']['code']
    
    # 數值校驗：確保為真實即時數據，否則報錯
    try:
        latest = float(rt['latest_trade_price'])
        open_p = float(rt['open'])
        high = float(rt['high'])
        low = float(rt['low'])
    except:
        return st.error(f"{name} 數據異常")

    diff = latest - open_p
    color = "#ff4d4d" if diff >= 0 else "#00ff88"
    
    # 建立小型 Plotly K 棒圖
    fig = go.Figure(data=[go.Candlestick(
        open=[open_p], high=[high], low=[low], close=[latest],
        increasing_line_color='#ff4d4d', decreasing_line_color='#00ff88',
        showlegend=False
    )])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=80, width=60,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    
    with st.container():
        st.plotly_chart(fig, config={'displayModeBar': False}, use_container_width=False)
        st.markdown(f"<div style='text-align:center; font-size:12px; font-weight:bold;'>{name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center; font-size:10px; color:{color};'>{latest} ({diff:+.1f})</div>", unsafe_allow_html=True)

# --- 主程式邏輯 ---

st.set_page_config(page_title="TX Strategic Dashboard", layout="wide")
st.title("🛡️ 台指期戰略大數據終端 (含 K 棒看板)")

# 資料庫更新與同步邏輯 (續用前次建議內容)
# ... [此處包含 update_database() 函數] ...

# 側邊欄：刷新按鈕
if st.sidebar.button("🔄 同步真實數據 (含權值股看板)"):
    with st.spinner("同步中..."):
        # 1. 抓取權值股數據
        st.session_state.weighted_data = get_stocks_kbar_data(WEIGHTED_IDS)
        # 2. 抓取成交值熱門股數據
        turnover_ids = get_turnover_top_15()
        st.session_state.turnover_data = get_stocks_kbar_data(turnover_ids)
        st.session_state.sync_ready = True

# --- 顯示 K 棒看板區 ---
if "sync_ready" in st.session_state:
    # 1. 權值股 TOP 15
    st.subheader("🔥 權值股 TOP 15 當日走勢")
    cols_w = st.columns(15)
    w_data = st.session_state.weighted_data
    for idx, sid in enumerate(WEIGHTED_IDS):
        with cols_w[idx]:
            render_kbar_component(w_data[sid])

    st.divider()

    # 2. 成交值 TOP 15
    st.subheader("📊 成交值 TOP 15 觀察")
    cols_t = st.columns(15)
    t_data = st.session_state.turnover_data
    # 取得實際返回的代號列表 (排除 success 鍵)
    t_ids = [k for k in t_data.keys() if k != 'success']
    for idx, sid in enumerate(t_ids[:15]):
        with cols_t[idx]:
            render_kbar_component(t_data[sid])

    st.divider()
    
    # 3. 三大法人趨勢與統計分析
    # ... [此處顯示法人彩色長條圖與歷史統計儀表板] ...
else:
    st.info("👈 請點擊左側「同步真實數據」以載入權值股與熱門股 K 棒看板。")
