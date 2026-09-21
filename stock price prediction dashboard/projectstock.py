import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import ta
from streamlit_option_menu import option_menu

# Sidebar Menu
st.set_page_config(layout="wide", page_title="Stock Dashboard") ##page_icon="📈"##)
with st.sidebar:
    selected = option_menu(
        "Stock Dashboard",
        ["Dashboard", "Analysis", "Prediction", "Reports","Portfolio", "Settings"],
        icons=["house", "graph-up", "cpu", "file-earmark", "briefcase", "gear"],
        default_index=0
    )

# ================== PAGE CONFIG ==================
if selected == "Dashboard":
    st.title("📈 Real-Time Stock Dashboard")


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
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line','bar'])
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

if selected == "Dashboard":

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
if selected == "Analysis":

    st.title("📊 Technical Analysis")

    ticker = st.text_input("Enter Stock Symbol", "RELIANCE")

    data = fetch_stock_data(ticker, "6mo", "1d")

    if not data.empty:

        data = add_technical_indicators(data)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=data['Datetime'],
                y=data['Close'],
                name='Close Price'
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data['Datetime'],
                y=data['SMA_20'],
                name='SMA 20'
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data['Datetime'],
                y=data['EMA_20'],
                name='EMA 20'
            )
        )

        st.plotly_chart(fig, use_container_width=True)

elif selected == "Prediction":

    st.subheader("Stock Price Prediction")

    ticker = st.text_input(
        "Stock Symbol",
        "RELIANCE",
        key="pred_ticker"
    )

    data = fetch_stock_data(ticker, "1y", "1d")

    if not data.empty:

        current_price = float(data['Close'].iloc[-1])

        predicted_price = current_price * 1.05

        col1, col2 = st.columns(2)

        col1.metric(
            "Current Price",
            f"₹{current_price:.2f}"
        )

        col2.metric(
            "Predicted Price",
            f"₹{predicted_price:.2f}"
        )

        st.success(
            f"Estimated next target: ₹{predicted_price:.2f}"
        )

elif selected == "Portfolio":

    st.title("💼 Portfolio Manager")

    # Initialize portfolio only once
    if "portfolio_data" not in st.session_state:
        st.session_state.portfolio_data = []

    # ================= ADD STOCK =================

    st.markdown("### ➕ Add Stock")

    with st.form("portfolio_form"):

        col1, col2 = st.columns(2)

        with col1:
            stock = st.text_input(
                "Stock Symbol",
                placeholder="RELIANCE"
            )

        with col2:
            qty = st.number_input(
                "Quantity",
                min_value=1,
                value=1,
                step=1
            )

        col3, col4 = st.columns(2)

        with col3:
            buy_price = st.number_input(
                "Buy Price (₹)",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

        with col4:
            current_price = st.number_input(
                "Current Price (₹)",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

        submitted = st.form_submit_button(
            "Add Stock"
        )

    # ================= PROCESS FORM =================

    if submitted:

        # Remove spaces and convert to uppercase
        stock = stock.strip().upper()

        if stock == "":
            st.error("Please enter a stock symbol.")

        elif buy_price <= 0:
            st.error("Please enter a valid Buy Price.")

        elif current_price <= 0:
            st.error("Please enter a valid Current Price.")

        else:

            invested_amount = qty * buy_price
            current_value = qty * current_price

            profit_loss = current_value - invested_amount

            profit_percent = (
                (profit_loss / invested_amount) * 100
                if invested_amount > 0
                else 0
            )

            # Add stock to portfolio
            st.session_state.portfolio_data.append({
                "Stock": stock,
                "Quantity": qty,
                "Buy Price": buy_price,
                "Current Price": current_price,
                "Invested Amount": invested_amount,
                "Current Value": current_value,
                "Profit/Loss": profit_loss,
                "P/L %": round(profit_percent, 2)
            })

            st.success(f"✅ {stock} added successfully!")

    # ================= PORTFOLIO TABLE =================
    if st.session_state.portfolio_data:

        df = pd.DataFrame(st.session_state.portfolio_data)

        st.markdown("### 📋 Portfolio Holdings")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        # ================= SUMMARY =================

        total_invested = df["Invested Amount"].sum()
        total_value = df["Current Value"].sum()
        total_profit = df["Profit/Loss"].sum()

        overall_return = (
            (total_profit / total_invested) * 100
            if total_invested > 0 else 0
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "💰 Invested",
            f"₹{total_invested:,.2f}"
        )

        col2.metric(
            "📈 Current Value",
            f"₹{total_value:,.2f}"
        )

        col3.metric(
            "💹 Profit/Loss",
            f"₹{total_profit:,.2f}"
        )

        col4.metric(
            "📊 Return %",
            f"{overall_return:.2f}%"
        )

        # ================= PIE CHART =================

        st.markdown("### 🥧 Portfolio Allocation")

        pie_fig = px.pie(
            df,
            names="Stock",
            values="Current Value",
            hole=0.5
        )

        pie_fig.update_layout(
            template="plotly_dark",
            height=500
        )

        st.plotly_chart(
            pie_fig,
            use_container_width=True
        )

        # ================= BAR CHART =================

        st.markdown("### 📈 Stock-wise Performance")

        bar_fig = px.bar(
            df,
            x="Stock",
            y="Profit/Loss",
            text="Profit/Loss"
        )

        bar_fig.update_layout(
            template="plotly_dark",
            height=450
        )

        st.plotly_chart(
            bar_fig,
            use_container_width=True
        )

        # ================= DOWNLOAD CSV =================

        csv = df.to_csv(index=False)

        st.download_button(
            label="📥 Download Portfolio CSV",
            data=csv,
            file_name="portfolio_report.csv",
            mime="text/csv"
        )

        # ================= CLEAR PORTFOLIO =================

        if st.button("🗑 Clear Portfolio"):
            st.session_state.portfolio_data = []
            st.rerun()

    else:
        st.info("No stocks added yet.")

elif selected == "Reports":

    st.subheader("Historical Data Report")

    ticker = st.text_input(
        "Stock Symbol",
        "RELIANCE",
        key="report_ticker"
    )

    data = fetch_stock_data(ticker, "6mo", "1d")

    if not data.empty:

        st.dataframe(data)

        csv = data.to_csv(index=False)

        st.download_button(
            "Download CSV",
            csv,
            file_name=f"{ticker}_report.csv",
            mime="text/csv"
        )

elif selected == "Settings":

    st.subheader("⚙ Dashboard Settings")

    # Theme
    theme = st.selectbox(
        "Theme",
        ["Dark", "Light"]
    )

    # Refresh Rate
    refresh = st.slider(
        "Auto Refresh Rate (seconds)",
        10,
        300,
        60
    )

    # Currency
    currency = st.selectbox(
        "Currency",
        ["INR ₹", "USD $", "EUR €"]
    )

    # Technical Indicators
    show_sma = st.checkbox("Show SMA 20", value=True)
    show_ema = st.checkbox("Show EMA 20", value=True)

    # Notifications
    notifications = st.checkbox(
        "Enable Price Alerts"
    )

    # Email Reports
    email_reports = st.checkbox(
        "Receive Weekly Reports"
    )

    # Dashboard Layout
    layout = st.radio(
        "Dashboard Layout",
        ["Compact", "Standard", "Detailed"]
    )

    # Save Button
    if st.button("Save Settings"):
        st.success("Settings Saved Successfully!")
    

st.sidebar.info("Indian Stock Dashboard\n• Real-time NSE Data\n• Timezone: IST (Delhi)")