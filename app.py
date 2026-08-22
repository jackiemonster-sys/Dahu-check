import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from FinMind.data import DataLoader

st.set_page_config(page_title="專業台股籌碼與技術分析", layout="wide")
st.title("📈 台股籌碼大戶 + 法人 + MACD 戰情室")

# 1. 側邊欄參數設定
st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("輸入台股代號", value="2330")
period = st.sidebar.selectbox("時間範圍", ["3mo", "6mo", "1y", "2y"], index=2)

ticker_str = f"{stock_id}.TW"
stock = yf.Ticker(ticker_str)

try:
    # 2. 抓取 yfinance 價格與均線資料
    df = stock.history(period=period)

    if df.empty:
        st.error("查無股票資料，請確認代號。")
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

        # 3. 透過 FinMind 抓取真實千張大戶歷史資料
        dl = DataLoader()
        start_date = df.index[0].strftime('%Y-%m-%d')
        
        # 抓取集保股權分散表 (15 等級代表 1000 張以上大戶)
        df_share = dl.taiwan_stock_holding_shares_per(
            stock_id=stock_id, start_date=start_date
        )
        
        # 過濾千張大戶資料
        big_holders = df_share[df_share['HoldingSharesLevel'] == 15].copy()
        if not big_holders.empty:
            big_holders['date'] = pd.to_datetime(big_holders['date'])
            big_holders = big_holders.set_index('date').sort_index()

        # 4. 頂部籌碼診斷儀表板
        if not big_holders.empty and len(big_holders) >= 2:
            latest_ratio = big_holders['percent'].iloc[-1]
            prev_ratio = big_holders['percent'].iloc[-2]
            diff = latest_ratio - prev_ratio

            col1, col2, col3 = st.columns(3)
            col1.metric("最新股價", f"{df['Close'].iloc[-1]:.1f} 元", f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.1f}")
            col2.metric("千張大戶持股比率", f"{latest_ratio:.2f}%", f"{diff:+.2f}% (較上週)")
            
            # 自動籌碼判斷
            if diff > 0.5:
                col3.success("🔥 籌碼動向：大戶顯著增持，籌碼高度集中")
            elif diff < -0.5:
                col3.error("⚠️ 籌碼動向：大戶持續減持，籌碼正在流向散戶")
            else:
                col3.info("⚖️ 籌碼動向：大戶持股波動不大，處於觀望階段")

        # 5. 繪製 3 欄位互動圖表
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
            subplot_titles=('K 線圖與移動平均線 (MA)', '真實千張大戶持股比率 (%)', 'MACD 技術指標'),
            row_heights=[0.5, 0.25, 0.25]
        )

        # 圖 1: K線 + 均線
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA', line=dict(color='green', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60MA', line=dict(color='blue', width=1)), row=1, col=1)

        # 圖 2: 真實千張大戶趨勢
        if not big_holders.empty:
            fig.add_trace(go.Scatter(
                x=big_holders.index, y=big_holders['percent'],
                mode='lines+markers', name='千張大戶 %', line=dict(color='crimson', width=2)
            ), row=2, col=1)

        # 圖 3: MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], name='DIF (快)', line=dict(color='purple', width=1)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEM'], name='DEM (慢)', line=dict(color='gray', width=1)), row=3, col=1)
        colors = ['red' if v >= 0 else 'green' for v in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD 柱狀圖', marker_color=colors), row=3, col=1)

        fig.update_layout(height=850, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"資料讀取失敗：{e}")
