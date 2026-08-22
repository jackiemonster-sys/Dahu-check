import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 頁面標題與佈局
st.set_page_config(page_title="台股籌碼分析 App", layout="wide")
st.title("📈 台股籌碼與股價觀察 App")

# 側邊欄輸入
st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("輸入台股代號（無需加 .TW）", value="2330")
period = st.sidebar.selectbox("選擇時間範圍", ["1mo", "3mo", "6mo", "1y"], index=1)

# 抓取 Yahoo Finance 資料（台股需加上 .TW）
ticker_str = f"{stock_id}.TW"
stock = yf.Ticker(ticker_str)

try:
    df = stock.history(period=period)
    info = stock.info

    if df.empty:
        st.error("找不到該股票資料，請確認代號是否正確。")
    else:
        # 基本資訊展示
        st.subheader(f"{info.get('longName', stock_id)} ({ticker_str})")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("當前股價", f"{df['Close'].iloc[-1]:.2f} 元")
        col2.metric("昨日成交量", f"{int(df['Volume'].iloc[-1] / 1000):,} 張")
        col3.metric("機構持股比例 (大戶參考)", f"{info.get('institutionalPercentHeld', 0) * 100:.2f}%")
        col4.metric("內部人持股比例", f"{info.get('heldPercentInsiders', 0) * 100:.2f}%")

        # K線圖與成交量繪製
        st.markdown("### 📊 股價與成交量走勢")
        fig = go.Figure()
        
        # K線
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name="K線"
        ))
        
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=500,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        # 籌碼簡易分析邏輯
        st.markdown("### 🔍 籌碼狀態估算")
        inst_held = info.get('institutionalPercentHeld', 0)
        
        if inst_held > 0.4:
            st.success("【大戶主導】機構與法人持股比例超過 40%，籌碼相對集中。")
        elif inst_held < 0.2:
            st.warning("【散戶偏多】機構持股比例低於 20%，籌碼相對分散，波動可能較大。")
        else:
            st.info("【籌碼中性】法人持股比例介於 20% ~ 40% 之間。")

        st.caption("提示：完整的集保每週「千張大戶持股比率」可串接台灣集中保管結算所 (TDCC) 開放 API 取得進階數據。")

except Exception as e:
    st.error(f"資料讀取失敗：{e}")
