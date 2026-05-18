# Stock-Price-Prediction-Dashboard
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import ta

# ================== PAGE CONFIG ==================
st.set_page_config(layout="wide", page_title="Stock Dashboard") ##page_icon="📈"##)
st.title('Real-Time Stock Dashboard')

# ================== FIXED FUNCTION ==================
def fetch_stock_data(ticker, period, interval):
    try:
        
        if not ticker.endswith('.NS') and not ticker.endswith('.BO'):
            ticker = ticker.upper() + '.NS'
        
        if period == '1wk':
            end = datetime.now()
            start = end - timedelta(days=7)
            data = yf.download(ticker, start=start, end=end, interval=interval,
                             auto_adjust=True, progress=False)
        else:
            data = yf.download(ticker, period=period, interval=interval,
                             auto_adjust=True, progress=False)
        
        if data.empty:
            return pd.DataFrame()
        
        # Handle MultiIndex columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # Reset index and standardize datetime column
        data.reset_index(inplace=True)
        
        # Standardize column name to 'Datetime'
        if 'Datetime' in data.columns:
            pass  # already good
        elif 'Date' in data.columns:
            data.rename(columns={'Date': 'Datetime'}, inplace=True)
        else:
            # Fallback
            data.rename(columns={data.columns[0]: 'Datetime'}, inplace=True)
        
        # Convert to IST (Delhi)
        if data['Datetime'].dtype == 'datetime64[ns]':
            if data['Datetime'].dt.tz is None:
                data['Datetime'] = data['Datetime'].dt.tz_localize('UTC')
            data['Datetime'] = data['Datetime'].dt.tz_convert('Asia/Kolkata')
        
        return data
    except Exception as e:
        st.error(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()


def add_technical_indicators(data):
    if len(data) >= 20:
        data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
        data['EMA_20'] = ta.trend.ema_indicator(data['Close'], window=20)
    return data


# ================== SIDEBAR ==================
st.sidebar.header('Chart Parameters')

ticker_input = st.sidebar.text_input('Ticker Symbol (e.g. RELIANCE, SBIN)', 'RELIANCE', key='ticker')
time_period = st.sidebar.selectbox('Time Period', ['1d', '1wk', '1mo', '3mo', '6mo', '1y', 'max'])
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20'])

interval_mapping = {
    '1d': '5m',
    '1wk': '15m',
    '1mo': '1d',
    '3mo': '1d',
    '6mo': '1d',
    '1y': '1wk',
    'max': '1mo'
}

# Live Prices
st.sidebar.header('Live NSE Prices')
indian_stocks = ['RELIANCE', 'SBIN', 'TCS', 'HDFCBANK', 'INFY', 
                 'TATAMOTORS', 'ICICIBANK', 'BHARTIARTL', 'ITC', 'HINDUNILVR']

for symbol in indian_stocks:
    data = fetch_stock_data(symbol, '1d', '5m')
    if not data.empty:
        last_price = float(data['Close'].iloc[-1])
        open_price = float(data['Open'].iloc[0])
        change = last_price - open_price
        pct_change = (change / open_price) * 100 if open_price != 0 else 0

        st.sidebar.metric(
            label=symbol,
            value=f"₹{last_price:.2f}",
            delta=f"{change:.2f} ({pct_change:.2f}%)"
        )

# ================== MAIN DASHBOARD ==================
if st.sidebar.button('Update Chart', type='primary'):
    with st.spinner(f'Fetching latest data for {ticker_input}...'):
        data = fetch_stock_data(ticker_input, time_period, interval_mapping[time_period])
        
        if data.empty:
            st.error(f"Could not fetch data for **{ticker_input}**. Please check the symbol.")
            st.stop()
        
        data = add_technical_indicators(data)
        
        last_close = float(data['Close'].iloc[-1])
        open_price_main = float(data['Open'].iloc[0])
        
        change = last_close - open_price_main
        pct_change = (change / open_price_main) * 100 if open_price_main != 0 else 0
        
        st.metric(
            label=f"{ticker_input.upper()} Last Price", 
            value=f"₹{last_close:.2f}", 
            delta=f"{change:.2f} ({pct_change:.2f}%)"
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("High", f"₹{data['High'].max():.2f}")
        col2.metric("Low", f"₹{data['Low'].min():.2f}")
        col3.metric("Volume", f"{int(data['Volume'].sum()):,}")

        # Plot Chart - uses 'Datetime'
        if chart_type == 'Candlestick':
            fig = go.Figure(data=[go.Candlestick(
                x=data['Datetime'],
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                increasing_line_color='green',
                decreasing_line_color='red'
            )])
        else:
            fig = px.line(data, x='Datetime', y='Close')

        # Indicators
        for ind in indicators:
            if ind == 'SMA 20' and 'SMA_20' in data.columns:
                fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'], 
                                       name='SMA 20', line=dict(dash='dash', color='orange')))
            elif ind == 'EMA 20' and 'EMA_20' in data.columns:
                fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'], 
                                       name='EMA 20', line=dict(dash='dot', color='blue')))

        fig.update_layout(
            title=f'{ticker_input.upper()} - {time_period.upper()} Chart (NSE)',
            xaxis_title='Time (IST - Delhi)',
            yaxis_title='Price (₹ INR)',
            height=650,
            template='plotly_dark'
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Historical Data")
        st.dataframe(
            data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']].style.format({
                'Open': '₹{:.2f}', 'High': '₹{:.2f}', 'Low': '₹{:.2f}', 'Close': '₹{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )

st.sidebar.subheader("About")
st.sidebar.info("Indian Stock Dashboard\n• Real-time NSE Data\n• Timezone: IST (Delhi)")
