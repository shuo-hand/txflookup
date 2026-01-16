import streamlit as st
import pandas as pd
import numpy as np
import requests
import urllib3
import ssl  # <--- 修正處：確保導入 ssl 模組
import gspread
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import google.generativeai as genai
import twstock
import os
import json
from functools import partial

# --- 1. 強制繞過 SSL 驗證 (解決 Zeabur 部署 SSL 錯誤) ---
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# 針對 requests 套件進行全域補丁，強制關閉驗證
requests.get = partial(requests.get, verify=False)
requests.post = partial(requests.post, verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 2. 數據庫與環境初始化 ---
GSHEET_NAME = "TX_Database"
WEIGHTED_IDS = ['2330', '2317', '2454', '2382', '2308', '2881', '2882', '3711', '2412', '2303', '2891', '1301', '2886', '2603', '2892']

@st.cache_resource
def init_env():
    """初始化 twstock 股票代碼"""
    try:
        twstock.__update_codes()
        return True
    except:
        return False

init_env()

# --- 3. Google Sheets 核心邏輯 ---
def get_gsheet_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # 確保您在 Zeabur Variables 設定了 GSHEET_JSON
    creds_raw = st.secrets["GSHEET_JSON"] if "GSHEET_JSON" in st.secrets else os.environ.get("GSHEET_JSON")
    if not creds_raw:
        st.error("❌ 找不到 GSHEET_JSON 環境變數")
        st.stop()
    creds_json = json.loads(creds_raw)
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    return gspread.authorize(creds)

def update_gsheet_database():
    """增量同步資料：從最後一筆日期同步到今天"""
    client = get_gsheet_client()
    sh = client.open(GSHEET_NAME).sheet1
    existing_data = sh.get_all_records()
    
    if existing_data:
        df_base = pd.DataFrame(existing_data)
        df_base['日期'] = pd.to_datetime(df_base['日期']).dt.date
        last_date = df_base['日期'].max()
    else:
        df_base = pd.DataFrame(columns=["日期", "開盤", "最高", "最低", "收盤", "漲跌", "振幅", "漲跌幅(%)"])
        sh.append_row(df_base.columns.tolist())
        last_date = date(2023, 1, 1) - timedelta(days=1)

    today = date.today()
    if last_date >= today: return df_base

    new_rows = []
    check_date = last_date + timedelta(days=1)
    
    with st.spinner(f"正在同步雲端歷史數據自 {check_date}..."):
        while check_date <= today:
            d_str = check_date.strftime('%Y/%m/%d')
            url = f"https://www.taifex.com.tw/cht/3/futDailyMarketReport?queryDate={d_str}&commodity_id=TX"
            try:
                res = requests.get(url, timeout=5)
                tables = pd.read_html(res.text)
                if len(tables) >= 3:
                    row = tables[2].iloc[0] # 取台指期近月
                    h, l, c, o = float(row['最高價']), float(row['最低價']), float(row['最後成交價']), float(row['開盤價'])
                    diff = float(row['漲跌價'])
                    new_data = [d_str, o, h, l, c, diff, h-l, (diff/(c-diff))*100]
                    sh.append_row(new_data)
                    new_rows.append(dict(zip(df_base.columns, new_data)))
            except: pass
            check_date += timedelta(days=1)
    
    if new_rows:
        return pd.concat([df_base, pd.DataFrame(new_rows)])
    return df_base

# --- 4. 即時 K 棒抓取與渲染 ---
def get_safe_kbar_data(ids):
    try:
        data = twstock.realtime.get(ids)
        if data and data.get('success'): return data
        return {}
    except: return {}

def render_kbar_component(info):
    if not info or not info.get('success'):
        st.caption("N/A")
        return
    rt = info['realtime']
    try:
        latest = float(rt['latest_trade_price'])
        open_p = float(rt['open'])
        diff = latest - open_p
        color = "#ff4d4d" if diff >= 0 else "#00ff88"
        
        # 建立小型視覺 K 棒
        fig = go.Figure(data=[go.Candlestick(
            open=[open_p], high=[float(rt['high'])], low=[float(rt['low'])], close=[latest],
            increasing_line_color='#ff4d4d', decreasing_line_color='#00ff88', showlegend=False
        )])
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=60, width=50, xaxis_visible=False, yaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, config={'displayModeBar': False}, use_container_width=False)
        st.markdown(f"<div style='text-align:center; font-size:10px;'>{info['info']['name']}<br><span style='color:{color}'>{latest}</span></div>", unsafe_allow_html=True)
    except: st.caption("Err")

# --- 5. 主程式頁面 ---
st.set_page_config(page_title="TX Cloud Strategic Terminal", layout="wide")
st.title("📊 台指期雲端戰略終端 (GSync)")

if st.sidebar.button("🔄 同步全量數據 (Cloud + Realtime)"):
    st.session_state.df_hist = update_gsheet_database()
    st.session_state.w_data = get_safe_kbar_data(WEIGHTED_IDS)
    # 抓取成交值前 15 (簡化版邏輯)
    st.session_state.t_data = get_safe_kbar_data(['2603', '2609', '2317', '2330', '2382', '3231', '2454', '2618', '2409', '2353', '1513', '1519', '2303', '3037', '2371'])
    st.session_state.ready = True

if "ready" in st.session_state:
    # K 棒看板區
    st.subheader("🔥 權值股 TOP 15 / 📊 成交值 TOP 15")
    rows = st.columns(15)
    w_data = st.session_state.w_data
    for i, sid in enumerate(WEIGHTED_IDS):
        with rows[i]: render_kbar_component(w_data.get(sid))
    
    st.divider()

    # 統計看板
    df = st.session_state.df_hist
    st.subheader("📈 2023 至今波動率統計")
    c1, c2, c3 = st.columns(3)
    c1.metric("平均振幅", f"{df['日盤振幅'].mean():.1f}", f"±{df['日盤振幅'].std():.1f}")
    c2.metric("平均漲幅", f"{df[df['日盤漲跌']>0]['日盤漲跌'].mean():.1f}")
    c3.metric("平均跌幅", f"{abs(df[df['日盤漲跌']<0]['日盤漲跌'].mean()):.1f}")

    st.dataframe(df.sort_values("日期", ascending=False), use_container_width=True)
else:
    st.info("請點擊側邊欄「同步全量數據」開始雲端與即時同步。")
