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

# 2. 直連證交所官方 OpenAPI（超高速、穩定不逾時）
@st.cache_data(ttl=3600)
def get_twse_big_holders(target_id):
    try:
        # 證交所 OpenAPI - 集保戶股權分散表
        url = "https://openapi.twse.com.tw/v1/opendata/t187ap14_L"
        res = requests.get(url, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data)
            
            # 清理與比對代號（部分資料為 Code、部分為 證券代號）
            code_col = [c for c in df.columns if 'Code' in c or '代號' in c][0]
            level_col = [c for c in df.columns if 'Level' in c or '分級' in c][0]
            percent_col = [c for c in df.columns if 'Percent' in c or '%' in c or '比例' in c][0]
            
            # 篩選個股與千張大戶 ( Level 15 / 持股分級 15 )
            df_target = df[
                (df[code_col].astype(str).str.strip() == str(target_id)) & 
                (df[level_col].astype(str).str.strip() == '15')
            ].copy()
            
            if not df_target.empty:
                ratio = float(df_target[percent_col].values[0])
                return ratio
    except Exception as e:
        st.caption(f"除錯記錄: {e}")
    return None

ticker_str = f"{stock_id}.TW"

try:
    stock = yf.Ticker(ticker_str)
    df = stock.history(period=period)

    if df.empty:
        st.error("⚠️ 查無股票資料，請確認代號。")
    else:
        # 計算技術指標
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = exp1 - exp2
        df['DEM'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['DEM']

        # 抓取最新千張大戶比例
        latest_ratio = get_twse_big_holders(stock_id)

        # 頂部儀表板
        col1, col2 = st.columns(2)
        col1.metric("當前股價", f"{df['Close'].iloc[-1]:.1f} 元", f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.1f}")
        
        if latest_ratio is not None:
            col2.metric("最新千張大戶持股比率", f"{latest_ratio:.2f}%")
        else:
            col2.metric("千張大戶持股比率", "無資料 (或該股非上市櫃股票)")

        # 圖表繪製
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            subplot_titles=('K 線圖與 5MA / 20MA', 'MACD 指標'),
            row_heights=[0.65, 0.35]
        )

        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA', line=dict(color='green', width=1)), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], name='DIF', line=dict(color='purple', width=1)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEM'], name='DEM', line=dict(color='gray', width=1)), row=2, col=1)
        colors = ['red' if v >= 0 else 'green' for v in df['MACD_Hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='柱狀圖', marker_color=colors), row=2, col=1)

        fig.update_layout(height=750, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"系統執行錯誤：{e}")
