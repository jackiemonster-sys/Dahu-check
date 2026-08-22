import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="台股籌碼與技術分析", layout="wide")
st.title("📈 台股籌碼大戶 + MACD 戰情室")

# 1. 側邊欄設定
st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("輸入台股代號", value="2330").strip()
period = st.sidebar.selectbox("時間範圍", ["3mo", "6mo", "1y"], index=1)

# 2. 萬能適應型 TDCC 抓取函式
@st.cache_data(ttl=3600)
def get_tdcc_big_holders(target_id):
    try:
        # 政府資料開放平臺 API (集保戶股權分散表)
        url = "https://openapi.twse.com.tw/v1/opendata/t187ap14_L"
        res = requests.get(url, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data)
            
            # 欄位自動清洗與轉換
            df.columns = [c.strip() for c in df.columns]
            
            # 找到代表股票代號與持股分級的欄位
            code_col = [c for c in df.columns if '代號' in c or 'Code' in c][0]
            level_col = [c for c in df.columns if '分級' in c or 'Level' in c][0]
            ratio_col = [c for c in df.columns if '%' in c or '比例' in c or 'Percent' in c][0]
            date_col = [c for c in df.columns if '日期' in c or 'Date' in c][0]

            # 篩選千張大戶 (Level 15)
            df_stock = df[(df[code_col].astype(str) == str(target_id)) & (df[level_col].astype(str) == '15')].copy()
            
            if not df_stock.empty:
                df_stock['ratio'] = pd.to_numeric(df_stock[ratio_col], errors='coerce')
                df_stock['date'] = pd.to_datetime(df_stock[date_col].astype(str))
                return df_stock.sort_values('date')
    except Exception as e:
        st.caption(f"除錯訊息: {e}")
    return pd.DataFrame()

ticker_str = f"{stock_id}.TW"

try:
    stock = yf.Ticker(ticker_str)
    df = stock.history(period=period)

    if df.empty:
        st.error("⚠️ 查無股票資料，請確認代號。")
    else:
        # 技術指標計算
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = exp1 - exp2
        df['DEM'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['DEM']

        # 載入大戶資料
        big_holders = get_tdcc_big_holders(stock_id)

        # 頂部儀表板
        col1, col2 = st.columns(2)
        col1.metric("當前股價", f"{df['Close'].iloc[-1]:.1f} 元", f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.1f}")
        
        if not big_holders.empty:
            latest_ratio = big_holders['ratio'].iloc[-1]
            col2.metric("千張大戶持股比率", f"{latest_ratio:.2f}%")
        else:
            col2.metric("千張大戶持股比率", "讀取中/無資料")

        # 繪圖
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            subplot_titles=('K 線圖與 5MA / 20MA', '千張大戶持股比率 (%)', 'MACD 指標'),
            row_heights=[0.5, 0.25, 0.25]
        )

        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA', line=dict(color='green', width=1)), row=1, col=1)

        if not big_holders.empty:
            fig.add_trace(go.Scatter(
                x=big_holders['date'], y=big_holders['ratio'],
                mode='lines+markers', name='大戶 %', line=dict(color='crimson', width=2)
            ), row=2, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], name='DIF', line=dict(color='purple', width=1)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEM'], name='DEM', line=dict(color='gray', width=1)), row=3, col=1)
        colors = ['red' if v >= 0 else 'green' for v in df['MACD_Hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='柱狀圖', marker_color=colors), row=3, col=1)

        fig.update_layout(height=800, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"系統執行錯誤：{e}")
