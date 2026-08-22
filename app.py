import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="台股籌碼與技術分析", layout="wide")
st.title("📈 台股籌碼大戶 + MACD 戰情室")

st.sidebar.header("參數設定")
stock_id = st.sidebar.text_input("輸入台股代號", value="2330").strip()
period = st.sidebar.selectbox("時間範圍", ["3mo", "6mo", "1y", "2y"], index=2)

# 高成功率的 TDCC 集保開放資料抓取函式
@st.cache_data(ttl=3600)
def get_tdcc_data(target_id):
    url = "https://smart.tdcc.com.tw/openapi/getstat.aspx?fid=1-5"
    
    session = requests.Session()
    # 擬真瀏覽器表頭以防被擋
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })
    
    try:
        # verify=False 避免 SSL 驗證失敗，stream=True 加快串流讀取
        res = session.get(url, verify=False, timeout=15)
        if res.status_code == 200:
            df = pd.read_csv(io.StringIO(res.text))
            df.columns = [c.strip() for c in df.columns]
            
            # 自動鎖定欄位
            code_col = [c for c in df.columns if '代號' in c or 'Code' in c][0]
            level_col = [c for c in df.columns if '分級' in c or 'Level' in c][0]
            ratio_col = [c for c in df.columns if '%' in c or '比例' in c or '佔比' in c][0]
            
            # 轉型態與過濾
            df[code_col] = df[code_col].astype(str).str.strip()
            df[level_col] = pd.to_numeric(df[level_col], errors='coerce')
            
            # 持股分級 15 代表千張大戶
            target_df = df[(df[code_col] == str(target_id)) & (df[level_col] == 15)].copy()
            
            if not target_df.empty:
                ratio = float(target_df[ratio_col].values[0])
                return ratio
    except Exception as e:
        pass
    return None

ticker_str = f"{stock_id}.TW"

try:
    stock = yf.Ticker(ticker_str)
    df = stock.history(period=period)

    if df.empty:
        # 上市抓不到改試上櫃 (.TWO)
        ticker_str = f"{stock_id}.TWO"
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

        # 抓取大戶資料
        big_holder_ratio = get_tdcc_data(stock_id)

        # 頂部儀表板
        col1, col2, col3 = st.columns(3)
        col1.metric("當前股價", f"{df['Close'].iloc[-1]:.1f} 元", f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.1f}")
        
        if big_holder_ratio is not None:
            col2.metric("最新千張大戶持股比率", f"{big_holder_ratio:.2f}%")
            if big_holder_ratio > 60:
                col3.success("🔥 籌碼結構：千張大戶高度集中 (>60%)")
            elif big_holder_ratio < 40:
                col3.warning("⚠️ 籌碼結構：千張大戶持股偏低 (<40%)")
            else:
                col3.info("⚖️ 籌碼結構：籌碼中性/觀望")
        else:
            col2.metric("千張大戶持股比率", "無資料")
            col3.caption("💡 提示：TDCC 每週五傍晚更新數據。")

        # 圖表繪製
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            subplot_titles=('K 線圖與 5MA / 20MA', 'MACD 指標'),
            row_heights=[0.65, 0.35]
        )

        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='orange', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA', line=dict(color='green', width=1)), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['DIF'], name='DIF', line=dict(color='purple', width=1)), row=3 if False else 2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['DEM'], name='DEM', line=dict(color='gray', width=1)), row=2, col=1)
        colors = ['red' if v >= 0 else 'green' for v in df['MACD_Hist'].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='柱狀圖', marker_color=colors), row=2, col=1)

        fig.update_layout(height=750, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"系統執行錯誤：{e}")
