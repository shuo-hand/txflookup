{\rtf1\ansi\ansicpg950\cocoartf2820
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import requests as r\
import urllib3\
from bs4 import BeautifulSoup\
import plotly.graph_objects as go\
from datetime import datetime, date, timedelta\
import google.generativeai as genai\
import twstock\
import os\
\
# --- \uc0\u22522 \u30990 \u33287 \u36899 \u32218 \u35373 \u23450  ---\
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)\
DATA_FILE = "tx_history_database.csv"\
WEIGHTED_IDS = ['2330', '2317', '2454', '2382', '2308', '2881', '2882', '3711', '2412', '2303', '2891', '1301', '2886', '2603', '2892']\
\
@st.cache_resource\
def init_env():\
    twstock.__update_codes() # \uc0\u26356 \u26032 \u32929 \u31080 \u20195 \u30908 \
    return True\
\
init_env()\
\
# --- \uc0\u25976 \u25818 \u25235 \u21462 \u27169 \u32068  ---\
\
def get_turnover_top_15():\
    """\uc0\u25235 \u21462 \u20170 \u26085 \u25104 \u20132 \u20540 \u21069  15 \u21517 \u30340 \u32929 \u31080 \u20195 \u34399 """\
    url = "https://www.twse.com.tw/exchangeReport/TWT4U?response=json"\
    try:\
        res = r.get(url, timeout=5).json()\
        df = pd.DataFrame(res['data'], columns=res['fields'])\
        return df['\uc0\u35657 \u21048 \u20195 \u34399 '].head(15).tolist()\
    except:\
        # \uc0\u33509 \u25235 \u21462 \u22833 \u25943 \u65292 \u22238 \u20659 \u19968 \u32068 \u38928 \u35373 \u29105 \u38272 \u32929 \u20195 \u30908 \
        return ['2330', '2317', '2603', '2382', '2609', '3231', '2353', '2454', '1513', '1519', '2303', '2301', '3037', '2371', '2618']\
\
def get_stocks_kbar_data(stock_ids):\
    """\uc0\u21033 \u29992  twstock \u29554 \u21462 \u22810 \u27284 \u32929 \u31080 \u30340 \u21363 \u26178  K \u26834 \u25976 \u25818 """\
    try:\
        data = twstock.realtime.get(stock_ids)\
        if not data['success']:\
            raise ValueError("twstock \uc0\u29554 \u21462 \u22833 \u25943 ")\
        return data\
    except Exception as e:\
        st.error(f"\uc0\u10060  \u32929 \u31080 \u21363 \u26178 \u25976 \u25818 \u29554 \u21462 \u22833 \u25943 : \{e\}")\
        return None\
\
# --- UI \uc0\u32068 \u20214 \u65306 \u21934 \u26681  K \u26834 \u30475 \u26495  (\u27169 \u25836  index.tsx \u35222 \u35258 \u25928 \u26524 ) ---\
\
def render_kbar_component(stock_info):\
    """\uc0\u28210 \u26579 \u21934 \u26681 \u32929 \u31080  K \u26834 \u32068 \u20214 """\
    if not stock_info['success']:\
        return st.caption("N/A")\
    \
    rt = stock_info['realtime']\
    name = stock_info['info']['name']\
    code = stock_info['info']['code']\
    \
    # \uc0\u25976 \u20540 \u26657 \u39511 \u65306 \u30906 \u20445 \u28858 \u30495 \u23526 \u21363 \u26178 \u25976 \u25818 \u65292 \u21542 \u21063 \u22577 \u37679 \
    try:\
        latest = float(rt['latest_trade_price'])\
        open_p = float(rt['open'])\
        high = float(rt['high'])\
        low = float(rt['low'])\
    except:\
        return st.error(f"\{name\} \uc0\u25976 \u25818 \u30064 \u24120 ")\
\
    diff = latest - open_p\
    color = "#ff4d4d" if diff >= 0 else "#00ff88"\
    \
    # \uc0\u24314 \u31435 \u23567 \u22411  Plotly K \u26834 \u22294 \
    fig = go.Figure(data=[go.Candlestick(\
        open=[open_p], high=[high], low=[low], close=[latest],\
        increasing_line_color='#ff4d4d', decreasing_line_color='#00ff88',\
        showlegend=False\
    )])\
    fig.update_layout(\
        margin=dict(l=0, r=0, t=0, b=0),\
        height=80, width=60,\
        xaxis=dict(visible=False), yaxis=dict(visible=False),\
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'\
    )\
    \
    with st.container():\
        st.plotly_chart(fig, config=\{'displayModeBar': False\}, use_container_width=False)\
        st.markdown(f"<div style='text-align:center; font-size:12px; font-weight:bold;'>\{name\}</div>", unsafe_allow_html=True)\
        st.markdown(f"<div style='text-align:center; font-size:10px; color:\{color\};'>\{latest\} (\{diff:+.1f\})</div>", unsafe_allow_html=True)\
\
# --- \uc0\u20027 \u31243 \u24335 \u37007 \u36655  ---\
\
st.set_page_config(page_title="TX Strategic Dashboard", layout="wide")\
st.title("\uc0\u55357 \u57057 \u65039  \u21488 \u25351 \u26399 \u25136 \u30053 \u22823 \u25976 \u25818 \u32066 \u31471  (\u21547  K \u26834 \u30475 \u26495 )")\
\
# \uc0\u36039 \u26009 \u24235 \u26356 \u26032 \u33287 \u21516 \u27493 \u37007 \u36655  (\u32396 \u29992 \u21069 \u27425 \u24314 \u35696 \u20839 \u23481 )\
# ... [\uc0\u27492 \u34389 \u21253 \u21547  update_database() \u20989 \u25976 ] ...\
\
# \uc0\u20596 \u37002 \u27396 \u65306 \u21047 \u26032 \u25353 \u37397 \
if st.sidebar.button("\uc0\u55357 \u56580  \u21516 \u27493 \u30495 \u23526 \u25976 \u25818  (\u21547 \u27402 \u20540 \u32929 \u30475 \u26495 )"):\
    with st.spinner("\uc0\u21516 \u27493 \u20013 ..."):\
        # 1. \uc0\u25235 \u21462 \u27402 \u20540 \u32929 \u25976 \u25818 \
        st.session_state.weighted_data = get_stocks_kbar_data(WEIGHTED_IDS)\
        # 2. \uc0\u25235 \u21462 \u25104 \u20132 \u20540 \u29105 \u38272 \u32929 \u25976 \u25818 \
        turnover_ids = get_turnover_top_15()\
        st.session_state.turnover_data = get_stocks_kbar_data(turnover_ids)\
        st.session_state.sync_ready = True\
\
# --- \uc0\u39023 \u31034  K \u26834 \u30475 \u26495 \u21312  ---\
if "sync_ready" in st.session_state:\
    # 1. \uc0\u27402 \u20540 \u32929  TOP 15\
    st.subheader("\uc0\u55357 \u56613  \u27402 \u20540 \u32929  TOP 15 \u30070 \u26085 \u36208 \u21218 ")\
    cols_w = st.columns(15)\
    w_data = st.session_state.weighted_data\
    for idx, sid in enumerate(WEIGHTED_IDS):\
        with cols_w[idx]:\
            render_kbar_component(w_data[sid])\
\
    st.divider()\
\
    # 2. \uc0\u25104 \u20132 \u20540  TOP 15\
    st.subheader("\uc0\u55357 \u56522  \u25104 \u20132 \u20540  TOP 15 \u35264 \u23519 ")\
    cols_t = st.columns(15)\
    t_data = st.session_state.turnover_data\
    # \uc0\u21462 \u24471 \u23526 \u38555 \u36820 \u22238 \u30340 \u20195 \u34399 \u21015 \u34920  (\u25490 \u38500  success \u37749 )\
    t_ids = [k for k in t_data.keys() if k != 'success']\
    for idx, sid in enumerate(t_ids[:15]):\
        with cols_t[idx]:\
            render_kbar_component(t_data[sid])\
\
    st.divider()\
    \
    # 3. \uc0\u19977 \u22823 \u27861 \u20154 \u36264 \u21218 \u33287 \u32113 \u35336 \u20998 \u26512 \
    # ... [\uc0\u27492 \u34389 \u39023 \u31034 \u27861 \u20154 \u24425 \u33394 \u38263 \u26781 \u22294 \u33287 \u27511 \u21490 \u32113 \u35336 \u20736 \u34920 \u26495 ] ...\
else:\
    st.info("\uc0\u55357 \u56392  \u35531 \u40670 \u25802 \u24038 \u20596 \u12300 \u21516 \u27493 \u30495 \u23526 \u25976 \u25818 \u12301 \u20197 \u36617 \u20837 \u27402 \u20540 \u32929 \u33287 \u29105 \u38272 \u32929  K \u26834 \u30475 \u26495 \u12290 ")}