import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="台股籌碼與技術分析", layout="wide")
st.title("📈 台股籌碼與 MACD 戰情室")

# 1. 側邊欄設定
st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("輸入台股代號", value="2330").strip()
period = st.sidebar.selectbox("時間範圍", ["3mo", "6mo", "1y", "2y"], index=2)

ticker_str = f"{stock_id}.TW"

try:
    stock = yf.Ticker(ticker_str)
    df = stock.history(period=period)

    if df.empty:
        # 上市抓不到試抓上櫃 (.TWO)
        ticker_str = f"{stock_id}.TWO"
        stock = yf.Ticker(ticker_str)
        df = stock.history(period=period)

    if df.empty:
        st.error("⚠️ 查無股票資料，請確認代號（如：2330、8069）。")
    else:
        # 計算技術指標
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = exp1 - exp2
        df['DEM'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['DEM']

        # 籌碼指標估算（利用法人持股與量價集中度）
        info = stock.info
        inst_held = info.get('institutionalPercentHeld', 0)
        
        # 頂部指標面板
        col1, col2, col3 = st.columns(3)
        col1.metric("當前股價", f"{df['Close'].iloc[-1]:.1f} 元", f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.1f}")
        col2.metric("法人/機構大戶持股比率", f"{inst_held * 100:.2f}%" if inst_held else "無數據")
        
        # 籌碼評語
        if inst_held and inst_held > 0.4:
            col3.success("🔥 籌碼結構：法人大戶高度集中 (>40%)")
        elif inst_held and inst_held < 0.2:
            col3.warning("⚠️ 籌碼結構：散戶偏多，大戶持股偏低 (<20%)")
        else:
            col3.info("⚖️ 籌碼結構：籌碼中性/觀望中")

        # 圖表繪製
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            subplot_titles=('K 線圖與 5MA / 20MA', 'MACD 指標'),
            row_heights=[0.65, 0.35]
        )

        # K線 + 均線
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA', line=dict(color='green', width=1)), row=1, col=1)

        # MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], name='DIF', line=dict(color='purple', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEM'], name='DEM', line=dict(color='gray', width=1)), row=2, col=1)
        colors = ['red' if v >= 0 else 'green' for v in df['MACD_Hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='柱狀圖', marker_color=colors), row=2, col=1)

        fig.update_layout(height=750, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"系統執行錯誤：{e}")
