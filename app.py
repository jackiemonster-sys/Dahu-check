import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader

st.set_page_config(page_title="台股籌碼與技術分析", layout="wide")
st.title("📈 台股籌碼大戶 + MACD 戰情室")

# 1. 側邊欄設定
st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("輸入台股代號", value="2330").strip()
period = st.sidebar.selectbox("時間範圍", ["3mo", "6mo", "1y", "2y"], index=2)

ticker_str = f"{stock_id}.TW"

try:
    # 2. 抓取 yfinance 價格
    stock = yf.Ticker(ticker_str)
    df = stock.history(period=period)

    if df.empty:
        st.error("⚠️ 查無股票資料，請確認代號是否正確（例如：2330）。")
    else:
        # 計算均線
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        # 計算 MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = exp1 - exp2
        df['DEM'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['DEM']

        # 3. 抓取 FinMind 千張大戶資料 (含防呆)
        big_holders = pd.DataFrame()
        try:
            dl = DataLoader()
            start_date = df.index[0].strftime('%Y-%m-%d')
            df_share = dl.taiwan_stock_holding_shares_per(
                stock_id=stock_id, start_date=start_date
            )
            
            if not df_share.empty:
                # 轉數字型態防呆
                df_share['HoldingSharesLevel'] = pd.to_numeric(df_share['HoldingSharesLevel'], errors='coerce')
                df_share['percent'] = pd.to_numeric(df_share['percent'], errors='coerce')
                
                # 15 代表 1000 張以上大戶
                big_holders = df_share[df_share['HoldingSharesLevel'] == 15].copy()
                if not big_holders.empty:
                    big_holders['date'] = pd.to_datetime(big_holders['date'])
                    big_holders = big_holders.set_index('date').sort_index()
        except Exception:
            st.warning("⚠️ 大戶資料暫時無法載入，將先顯示技術指標。")

        # 4. 頂部籌碼卡片
        if not big_holders.empty and len(big_holders) >= 2:
            latest_ratio = big_holders['percent'].iloc[-1]
            prev_ratio = big_holders['percent'].iloc[-2]
            diff = latest_ratio - prev_ratio

            col1, col2, col3 = st.columns(3)
            col1.metric("當前股價", f"{df['Close'].iloc[-1]:.1f} 元", f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.1f}")
            col2.metric("千張大戶持股比率", f"{latest_ratio:.2f}%", f"{diff:+.2f}% (較上週)")
            
            if diff > 0.3:
                col3.success("🔥 籌碼動向：大戶增持，籌碼集中")
            elif diff < -0.3:
                col3.error("⚠️ 籌碼動向：大戶減持，籌碼流向散戶")
            else:
                col3.info("⚖️ 籌碼動向：大戶觀望中")

        # 5. 繪製圖表
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            subplot_titles=('K 線圖與均線', '千張大戶持股比率 (%)', 'MACD 指標'),
            row_heights=[0.5, 0.25, 0.25]
        )

        # 圖 1: K線
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA', line=dict(color='green', width=1)), row=1, col=1)

        # 圖 2: 大戶趨勢
        if not big_holders.empty:
            fig.add_trace(go.Scatter(
                x=big_holders.index, y=big_holders['percent'],
                mode='lines+markers', name='大戶 %', line=dict(color='crimson', width=2)
            ), row=2, col=1)

        # 圖 3: MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], name='DIF', line=dict(color='purple', width=1)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEM'], name='DEM', line=dict(color='gray', width=1)), row=3, col=1)
        colors = ['red' if v >= 0 else 'green' for v in df['MACD_Hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='柱狀圖', marker_color=colors), row=3, col=1)

        fig.update_layout(height=800, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"系統執行錯誤：{e}")
