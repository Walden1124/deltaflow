import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, timedelta
from engine.data_manager import DataManager
from engine.calculator import calculate_greeks
from engine.recommendations import RecommendationsEngine
from engine.backtester import Backtester
from components.auth import AuthManager
from components.visuals import create_pl_stress_test, create_volatility_surface, create_volatility_smile, create_volatility_surface_placeholder

# Set page config for DeltaFlow terminal
st.set_page_config(
    page_title="DeltaFlow | Options Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .pro-badge {
        background: linear-gradient(90deg, #d4af37 0%, #ffdf73 100%);
        color: #000 !important;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 8px;
        box-shadow: 0 0 5px rgba(212, 175, 55, 0.5);
    }
    .stButton>button.broker-btn {
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        width: 100%;
    }
    .metric-card {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #00ffcc;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Services
@st.cache_resource
def init_services_v18():
    dm = DataManager()
    return dm, RecommendationsEngine(), AuthManager(), Backtester(dm)

data_manager, rec_engine, auth_manager, backtester = init_services_v18()

# Session State for User (Mocking Login if Supabase is unavailable)
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

@st.dialog("Company Profile")
def show_company_profile(ticker: str):
    with st.spinner("Fetching profile..."):
        profile = data_manager.get_company_profile(ticker)
        news = data_manager.get_company_news(ticker)
        
    if "error" in profile:
        st.error(profile["error"])
        return
        
    st.subheader(profile.get("name", ticker))
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Sector**<br>{profile.get('sector', 'N/A')}", unsafe_allow_html=True)
    c2.markdown(f"**P/E Ratio**<br>{profile.get('pe_ratio', 'N/A')}", unsafe_allow_html=True)
    
    employees = profile.get("employees", "N/A")
    emp_str = f"{employees:,}" if isinstance(employees, int) else employees
    c3.markdown(f"**Employees**<br>{emp_str}", unsafe_allow_html=True)
    
    with st.expander("About Company", expanded=False):
        st.write(profile.get("summary", "No summary available."))
        website = profile.get("website", "")
        if website:
            st.markdown(f"[Website]({website})")
            
    st.divider()
    
    with st.expander("Options IV Analysis", expanded=True):
        hv = data_manager.calculate_historical_volatility(ticker, window=30)
        leaps_data = data_manager.get_leaps_metrics(ticker, target_delta=0.80)
        
        if "error" not in leaps_data and hv > 0:
            leaps_iv = leaps_data["leaps_iv"]
            ratio = leaps_iv / hv
            
            if ratio < 0.95:
                signal = "🟢 Low (Discount)"
            elif ratio > 1.3:
                signal = "🔴 High (Premium)"
            else:
                signal = "🟡 Neutral"
                
            c_iv1, c_iv2 = st.columns(2)
            c_iv1.metric("30D HV", f"{hv*100:.1f}%")
            c_iv2.metric("LEAPS IV", f"{leaps_iv*100:.1f}%")
            st.markdown(f"**Pricing Status:** {signal}")
        else:
            st.info("IV Analysis not available for this ticker.")
            
    st.divider()
    st.markdown("#### 📰 Recent News")
    
    if not news:
        st.info("No recent news available.")
    else:
        for article in news:
            st.markdown(f"**[{article['title']}]({article['link']})**")
            date_str = article.get("timestamp_str", "Unknown Date")
            if " " in date_str:
                date_str = date_str.split(" ")[0] # Just show the date for a cleaner look
            st.caption(f"{article['publisher']} • {date_str}")
            st.write("---")

def render_sidebar():
    """Renders the sidebar navigation."""
    with st.sidebar:
        st.title("🌊 DeltaFlow")
        st.caption("Professional Options Terminal")
        
        st.divider()
        
        # Search component
        st.subheader("Universal Ticker Search")
        ticker = st.text_input("Enter Ticker", value="SPY").upper()
        
        st.divider()
        
        # Navigation
        st.subheader("Modules")
        module = st.radio(
            "Select View",
            options=["Dashboard", "Volatility Lab", "Discovery (LEAPS/Wheel)", "Backtesting Lab", "Watchlist"]
        )
        
        st.divider()
        
        # Auth Component
        st.markdown("### Authentication")
        if not auth_manager.client_available:
            st.info("💡 **Demo Mode Active**\nWatchlist & Alerts will reset on refresh.")

        if not st.session_state.logged_in:
            if st.button("Login (Demo)", use_container_width=True):
                st.session_state.logged_in = True
                st.rerun()
        else:
            st.success("Authenticated")
            if st.button("Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.rerun()
        st.divider()
        
        # Affiliate Broker Links
        st.markdown("### 🏦 Recommended Brokers")
        st.caption("Open an account to start trading LEAPS & options.")
        
        brokers = [
            {
                "name": "Tastytrade",
                "tagline": "Best for options traders",
                "badge": "⭐ Top Pick",
                "url": "https://start.tastytrade.com/#/",
                "color": "#ff6b35"
            },
            {
                "name": "Webull",
                "tagline": "Commission-free options",
                "badge": "🎁 Free Stocks",
                "url": "https://a.webull.com/i/DeltaFlowApp",
                "color": "#00b4d8"
            },
            {
                "name": "IBKR",
                "tagline": "Lowest margin rates",
                "badge": "💼 Pro Level",
                "url": "https://www.interactivebrokers.com/mkt/?src=deltaflow",
                "color": "#ef233c"
            },
            {
                "name": "moomoo",
                "tagline": "Advanced charting tools",
                "badge": "📊 Data Rich",
                "url": "https://j.moomoo.com/00mF3K",
                "color": "#7b2d8b"
            }
        ]
        
        for broker in brokers:
            with st.container():
                st.markdown(
                    f"""<a href="{broker['url']}" target="_blank" style="text-decoration:none;">
                    <div style="background:#1e2130;border:1px solid #2d3250;border-radius:8px;padding:10px 12px;margin-bottom:8px;cursor:pointer;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-weight:700;color:#f0f2f6;font-size:14px;">{broker['name']}</span>
                            <span style="background:{broker['color']}22;color:{broker['color']};border:1px solid {broker['color']}44;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:600;">{broker['badge']}</span>
                        </div>
                        <div style="color:#a0a8c0;font-size:12px;margin-top:2px;">{broker['tagline']}</div>
                    </div></a>""",
                    unsafe_allow_html=True
                )
        
        st.caption("*Affiliate links — we may earn a commission at no cost to you.*")
                
        return ticker, module

def render_broker_bridge():
    """Renders the Broker Bridge execution section."""
    st.markdown("### 🌉 Broker Bridge")
    st.caption("Execute strategies directly with our integrated partners.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("Execute on Interactive Brokers", key="broker_ibkr", use_container_width=True, type="primary")
    with col2:
        st.button("Execute on tastytrade", key="broker_tasty", use_container_width=True, type="secondary")

def render_dashboard(ticker: str):
    st.subheader(f"Market Overview: {ticker}")
    
    with st.spinner("Fetching data..."):
        stock_data = data_manager.get_stock_data(ticker)
        hv = data_manager.calculate_historical_volatility(ticker)
        
    if "error" in stock_data:
        st.error(stock_data["error"])
        return
        
    price = stock_data.get("current_price", 0.0)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${price:,.2f}")
    col2.metric("Historical Vol (30d)", f"{hv*100:.2f}%")
    col3.metric("Dividend Yield", f"{stock_data.get('dividend_yield', 0)*100:.2f}%")
    
    # Watchlist Toggle
    is_watched = ticker in auth_manager.get_watchlist(st.session_state.user_id)
    if col4.button("Remove from Watchlist" if is_watched else "Add to Watchlist", type="primary" if not is_watched else "secondary"):
        auth_manager.toggle_watchlist(st.session_state.user_id, ticker, is_watched)
        st.rerun()
        
    st.divider()
    
    st.subheader("Interactive Options Chain & Dynamic Greeks")
    expirations = data_manager.get_options_expirations(ticker)
    
    if not expirations:
        st.warning("No options data available for this ticker.")
        return
        
    c1, c2 = st.columns([1, 3])
    with c1:
        expiry = st.selectbox("Expiration Date", options=expirations)
        opt_type = st.radio("Option Type", ["Calls", "Puts"], horizontal=True)
        strike_view = st.selectbox("Strikes Displayed", ["Near The Money (±15%)", "Wide (±30%)", "All Strikes"])
    
    chain = data_manager.get_options_chain(ticker, expiry)
    if "error" in chain:
        st.error(chain["error"])
        return
        
    df = chain["calls"] if opt_type == "Calls" else chain["puts"]
    
    # Filter strikes based on user selection
    if "15%" in strike_view:
        df = df[(df['strike'] >= price * 0.85) & (df['strike'] <= price * 1.15)].copy()
    elif "30%" in strike_view:
        df = df[(df['strike'] >= price * 0.70) & (df['strike'] <= price * 1.30)].copy()
    
    df = df.reset_index(drop=True)
    
    # Format the display dataframe
    display_df = df[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].copy()
    display_df['impliedVolatility'] = display_df['impliedVolatility'].apply(lambda x: f"{x*100:.1f}%")
    display_df.columns = ['Strike', 'Last', 'Bid', 'Ask', 'Vol', 'OI', 'IV']
    
    with c2:
        st.caption("Select a row in the chain to calculate dynamic Greeks.")
        event = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            height=250
        )
        
    # Determine the selected strike (default to ATM if no row selected)
    if len(event.selection.rows) > 0:
        selected_idx = event.selection.rows[0]
        # In case the index is out of bounds due to a weird re-render
        if selected_idx < len(df):
            strike = df.iloc[selected_idx]['strike']
            iv = df.iloc[selected_idx]['impliedVolatility']
        else:
            atm_idx = (df['strike']-price).abs().argsort()[:1].values[0]
            strike = df.iloc[atm_idx]['strike']
            iv = df.iloc[atm_idx]['impliedVolatility']
    else:
        atm_idx = (df['strike']-price).abs().argsort()[:1].values[0]
        strike = df.iloc[atm_idx]['strike']
        iv = df.iloc[atm_idx]['impliedVolatility']
    
    # Calculate DTE
    dte = (datetime.strptime(expiry, "%Y-%m-%d") - datetime.now()).days
    if dte <= 0: dte = 1
    
    iv_hv_ratio = iv / hv if hv > 0 else 1.0
    st.markdown(f"**Selected Contract:** {expiry} ${strike} {opt_type[:-1]} | **IV:** {iv*100:.2f}% | **IV/HV Ratio:** {iv_hv_ratio:.2f}")
    
    if iv_hv_ratio > 1.2:
        st.success("💎 Options are currently EXPENSIVE relative to historical movement (Good for Sellers).")
    elif iv_hv_ratio < 0.8:
        st.warning("🔥 Options are currently CHEAP relative to historical movement (Good for Buyers).")
    
    # Calculate actual Greeks
    greeks = calculate_greeks(opt_type[:-1].lower(), price, strike, dte/365.0, 0.05, iv)
    
    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Delta (Δ)", f"{greeks['delta']:.4f}")
    g2.metric("Gamma (Γ)", f"{greeks['gamma']:.4f}")
    g3.metric("Theta (Θ)", f"{greeks['theta']:.4f}")
    g4.metric("Vega (ν)", f"{greeks['vega']:.4f}")
    g5.metric("Rho (ρ)", f"{greeks['rho']:.4f}")
    
    st.markdown("### Advanced Greeks <span class='pro-badge'>PRO PREVIEW</span>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Vanna**: {greeks['vanna']:.4f} \n\n*Sensitivity of Delta to Volatility.*")
    with c2:
        st.info(f"**Charm**: {greeks['charm']:.4f} \n\n*Sensitivity of Delta to Time.*")


def render_vol_lab(ticker: str):
    st.subheader(f"Volatility Lab: {ticker}")
    
    with st.expander("📖 How to use the Volatility Lab", expanded=False):
        st.markdown("""
        **The Goal:** Find where options are 'overpriced' (High IV) or 'underpriced' (Low IV).
        
        1. **The 3D Surface:** Shows IV across *all* strikes and *all* timeframes.
           - **Peaks (Yellow/Green):** High demand/fear. Options are **Expensive**.
           - **Valleys (Purple/Blue):** Low demand/calm. Options are **Cheap**.
        2. **The 2D Smile:** Shows the IV for the *closest* expiration date.
           - If it looks like a 'Smile' (higher at the edges), the market expects a big move.
           - If it's tilted (Skewed), the market is more worried about one direction (usually Down).
        """)

    stock_data = data_manager.get_stock_data(ticker)
    current_price = stock_data.get("current_price", 100.0) if "error" not in stock_data else 100.0
    
    # Fetch Data once
    with st.spinner("Analyzing market volatility..."):
        surface_data = data_manager.get_volatility_surface_data(ticker)

    tab1, tab2 = st.tabs(["3D Surface Analysis", "2D Smile Analysis"])
    
    with tab1:
        st.markdown("#### Global IV Surface")
        fig_surface = create_volatility_surface(surface_data, current_price)
        st.plotly_chart(fig_surface, use_container_width=True)
        
    with tab2:
        st.markdown("#### Near-Term Volatility Smile")
        fig_smile = create_volatility_smile(surface_data, current_price)
        st.plotly_chart(fig_smile, use_container_width=True)

    st.divider()
    
    st.markdown("#### P/L Stress Test")
    st.caption("How much money will you make or lose if the stock moves?")
    c1, c2 = st.columns([1, 2])
    with c1:
        strike = st.number_input("Target Strike", value=float(current_price))
        premium = st.number_input("Premium Paid/Received", value=5.0)
        opt_type = st.selectbox("Option Type", ["Call", "Put"])
    
    with c2:
        fig_pl = create_pl_stress_test(current_price, strike, premium, opt_type)
        st.plotly_chart(fig_pl, use_container_width=True)

def render_discovery():
    st.subheader("Discovery Engine")
    
    tabs = st.tabs(["Prime LEAPS", "Wheelhouse", "Fallen Angels"])
    
    with tabs[0]:
        st.markdown("### Prime LEAPS Candidates")
        st.caption("Filters for Strong Fundamentals and identifies Deep ITM Call Options.")
        
        with st.expander("⚙️ Scanner Configuration", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                selected_universe = st.selectbox("Sector Filter", ["Mega-Cap Tech", "Financials", "Healthcare", "Consumer Defensive", "Energy"])
                sample_size = st.slider("Number of Candidates", 10, 40, 25, 5)
            with c2:
                min_roe = st.slider("Minimum ROE (%)", 0, 50, 15) / 100.0
                target_delta = st.slider("Target Option Delta", 0.50, 0.95, 0.80, 0.05)
            with c3:
                require_fcf = st.checkbox("Require Positive FCF", value=True)
                st.write("")
                st.write("")
                run_scan = st.button(f"🚀 Generate Candidates", type="primary", use_container_width=True)
        
        if run_scan:
            progress_bar = st.progress(0, text="Initializing multithreaded scanner...")
            
            # Fetch random list ONLY when button is clicked to prevent UI state drift
            scan_list = data_manager.get_market_universe(selected_universe, sample_size)
            
            def update_progress(completed, total):
                progress = int((completed / total) * 100)
                progress_bar.progress(progress, text=f"Scanning {completed}/{total} options chains concurrently...")

            st.session_state.leaps_results = rec_engine.analyze_prime_leaps(
                scan_list, 
                min_roe=min_roe, 
                require_fcf=require_fcf, 
                target_delta=target_delta, 
                progress_callback=update_progress
            )
            progress_bar.empty()
            
        if "leaps_results" in st.session_state and st.session_state.leaps_results:
            results = st.session_state.leaps_results
            df = pd.DataFrame(results)
            
            display_df = df[["symbol", "current_price", "target_strike", "delta", "entry_cost", "leaps_iv", "dte"]].copy()
            display_df.columns = ["Symbol", "Price", "Strike", "Delta", "Cost", "LEAPS IV", "DTE"]
            
            display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:,.2f}")
            display_df["Strike"] = display_df["Strike"].apply(lambda x: f"${x:,.2f}")
            display_df["Delta"] = display_df["Delta"].apply(lambda x: f"{x:.3f}")
            display_df["Cost"] = display_df["Cost"].apply(lambda x: f"${x:,.2f}")
            display_df["LEAPS IV"] = display_df["LEAPS IV"].apply(lambda x: f"{x*100:.1f}%")
            
            st.success(f"Found {len(results)} Prime LEAPS Candidates! Click a row to view the company profile.")
            event = st.dataframe(display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            
            if len(event.selection.rows) > 0:
                selected_idx = event.selection.rows[0]
                ticker_to_show = df.iloc[selected_idx]["symbol"] # Use original df to avoid formatted string issues
                show_company_profile(ticker_to_show)
        elif "leaps_results" in st.session_state and not st.session_state.leaps_results:
            st.warning("No candidates found meeting all fundamental and options criteria.")
                    
    with tabs[1]:
        st.markdown("### Wheelhouse Candidates")
        st.caption("Filters for lower volatility (Beta < 1.3) and income stability.")
        
        c1, c2 = st.columns(2)
        with c1:
            min_div = st.slider("Min Dividend Yield (%)", 0.0, 10.0, 1.0) / 100.0
        with c2:
            wh_sector = st.selectbox("Sector Filter ", ["Mega-Cap Tech", "Financials", "Healthcare", "Consumer Defensive", "Energy"])

        if st.button("🚀 Generate 25 Wheelhouse Candidates", use_container_width=True):
            with st.spinner("Analyzing income profiles..."):
                wh_scan_list = data_manager.get_market_universe(wh_sector, 25)
                st.session_state.wheelhouse_results = rec_engine.analyze_wheelhouse(wh_scan_list, min_dividend=min_div, sector="All")
                
        if "wheelhouse_results" in st.session_state and st.session_state.wheelhouse_results:
            results = st.session_state.wheelhouse_results
            df_res = pd.DataFrame(results)
            display_df = df_res[["symbol", "current_price", "dividend_yield", "sector", "beta"]].copy()
            display_df['dividend_yield'] = display_df['dividend_yield'].apply(lambda x: f"{x*100:.2f}%")
            
            st.caption("Click a row to view the company profile.")
            event = st.dataframe(display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            
            if len(event.selection.rows) > 0:
                selected_idx = event.selection.rows[0]
                ticker_to_show = df_res.iloc[selected_idx]["symbol"]
                show_company_profile(ticker_to_show)
        elif "wheelhouse_results" in st.session_state and not st.session_state.wheelhouse_results:
            st.warning("No candidates found with the current filters.")
            
    with tabs[2]:
        st.markdown("### Fallen Angels (Discounted Options)")
        st.caption("Scans for options or underlying stocks that have crashed, providing deeply discounted entry points.")
        
        with st.expander("⚙️ Scanner Configuration", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                fa_sector = st.selectbox("Sector", ["Mega-Cap Tech", "Financials", "Healthcare", "Consumer Defensive", "Energy"], key="fa_sec")
                fa_sample = st.slider("Stocks to Analyze", 10, 40, 25, 5, key="fa_samp")
            with c2:
                fa_timeframe = st.selectbox("Drop Timeframe", ["Intraday", "1 Week", "1 Month", "6 Months", "52 Weeks"])
            with c3:
                fa_min_drop = st.slider("Minimum Drop (%)", -90, -10, -25, 5)
                st.write("")
                st.write("")
                run_fa = st.button(f"🚀 Hunt for Fallen Angels", type="primary", use_container_width=True)
                
        if run_fa:
            progress_bar = st.progress(0, text="Initializing multithreaded scanner...")
            fa_scan_list = data_manager.get_market_universe(fa_sector, fa_sample)
            
            def update_progress(completed, total):
                progress = int((completed / total) * 100)
                progress_bar.progress(progress, text=f"Hunting {completed}/{total} stocks concurrently...")

            st.session_state.fa_results = rec_engine.analyze_fallen_angels(
                fa_scan_list, 
                min_drop_pct=float(fa_min_drop), 
                timeframe=fa_timeframe, 
                progress_callback=update_progress
            )
            progress_bar.empty()
            
        if "fa_results" in st.session_state and st.session_state.fa_results:
            results = st.session_state.fa_results
            df = pd.DataFrame(results)
            
            # Use original df to maintain formatting consistency
            display_df = df[["symbol", "timeframe", "type", "contract", "strike", "dte", "current_price", "drop_pct"]].copy()
            display_df.columns = ["Symbol", "Timeframe", "Type", "Contract", "Strike", "DTE", "Entry Cost", "Price Drop"]
            
            display_df["Strike"] = display_df["Strike"].apply(lambda x: f"${x:,.2f}")
            display_df["Entry Cost"] = display_df["Entry Cost"].apply(lambda x: f"${x:,.2f}")
            display_df["Price Drop"] = display_df["Price Drop"].apply(lambda x: f"{x:.1f}%")
            
            st.success(f"Found {len(results)} Fallen Angels! Click a row to view the company profile.")
            event = st.dataframe(display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            
            if len(event.selection.rows) > 0:
                selected_idx = event.selection.rows[0]
                ticker_to_show = df.iloc[selected_idx]["symbol"]
                show_company_profile(ticker_to_show)
        elif "fa_results" in st.session_state and not st.session_state.fa_results:
            st.warning(f"No options found that dropped {fa_min_drop}% over the {fa_timeframe} timeframe.")

def render_watchlist():
    st.subheader("Persistent Watchlist & Alerts")
    
    if not st.session_state.logged_in:
        st.info("Please login to view your watchlist.")
        return
        
    tickers = auth_manager.get_watchlist(st.session_state.user_id)
    alerts = auth_manager.get_alerts(st.session_state.user_id)
    
    if not tickers:
        st.write("Your watchlist is empty. Search for a ticker and add it from the Dashboard.")
    else:
        for t in tickers:
            with st.container(border=True):
                stock_data = data_manager.get_stock_data(t)
                curr_price = stock_data.get("current_price", 0.0)
                alert_price = alerts.get(t, 0.0)
                
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                with col1:
                    if st.button(f"🔍 {t}", key=f"prof_{t}", help="View Company Profile"):
                        show_company_profile(t)
                    st.caption(f"Price: ${curr_price:,.2f}")
                
                with col2:
                    new_alert = st.number_input("Target Alert", value=float(alert_price), key=f"alert_{t}")
                    if new_alert != alert_price:
                        auth_manager.set_alert(st.session_state.user_id, t, new_alert)
                        st.rerun()
                
                with col3:
                    if alert_price > 0:
                        diff = ((curr_price - alert_price) / alert_price) * 100
                        if abs(diff) < 2:
                            st.warning(f"🎯 Target Near! ({diff:+.2f}%)")
                        elif curr_price >= alert_price and alert_price > 0:
                            st.success(f"🚀 Target Hit!")
                        else:
                            st.info(f"Dist: {diff:+.2f}%")
                            
                with col4:
                    if st.button(f"Remove", key=f"rm_{t}"):
                        auth_manager.toggle_watchlist(st.session_state.user_id, t, True)
                        st.rerun()

def render_backtester(sidebar_ticker: str):
    st.subheader("Backtesting Lab")
    st.info("Simulate historical strategy performance using Black-Scholes pricing.")
    
    strategy_map = {
        "Short Put (Sell to Open)": "short_put",
        "Long Call (Buy to Open)": "long_call",
        "Short Call (Sell to Open)": "short_call",
        "Long Put (Buy to Open)": "long_put"
    }
    
    with st.container(border=True):
        st.markdown("#### ⚙️ Strategy Configuration")
        c1, c2, c3 = st.columns(3)
        with c1:
            local_ticker = st.text_input("Asset Ticker", value=sidebar_ticker).upper()
            strategy_display = st.selectbox("Options Strategy", list(strategy_map.keys()))
        with c2:
            start_date = st.date_input("Historical Entry Date", value=datetime.now() - timedelta(days=90))
            dte = st.slider("Trade Duration (Days to Expiration)", 7, 730, 365 if "long" in strategy_display.lower() else 30)
        with c3:
            # Fetch real-world strike prices from the live options chain
            expirations = data_manager.get_options_expirations(local_ticker)
            target_strike = None
            
            if expirations:
                # Find expiration closest to the configured DTE
                from datetime import datetime as _dt
                sorted_exps = sorted(expirations, key=lambda e: abs((_dt.strptime(e, "%Y-%m-%d") - _dt.now()).days - dte))
                best_exp = sorted_exps[0]
                chain = data_manager.get_options_chain(local_ticker, best_exp)
                
                is_put = "Put" in strategy_display
                contracts = chain.get("puts" if is_put else "calls", None)
                
                if contracts is not None and not contracts.empty:
                    strikes = sorted(contracts["strike"].dropna().unique().tolist())
                    
                    # Pre-select the strike nearest to ATM as default
                    current_price = data_manager.get_stock_data(local_ticker).get("current_price", strikes[len(strikes)//2])
                    nearest_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - current_price))
                    
                    target_strike = st.selectbox(
                        f"Target Strike Price (${current_price:,.2f} Current)",
                        options=strikes,
                        index=nearest_idx,
                        format_func=lambda x: f"${x:,.2f}"
                    )
                    
                    # Show ITM/OTM label
                    if target_strike and current_price:
                        if not is_put:
                            moneyness = "ITM ✅" if target_strike < current_price else ("ATM ➡️" if target_strike == current_price else "OTM ⚠️")
                        else:
                            moneyness = "ITM ✅" if target_strike > current_price else ("ATM ➡️" if target_strike == current_price else "OTM ⚠️")
                        st.caption(f"Selected strike is **{moneyness}** relative to current price.")
                else:
                    st.warning("No options chain available for this ticker.")
            else:
                st.warning("No options data available. Check the ticker.")
                
            st.write("")
            run_sim = st.button("🚀 Run Backtest Simulation", use_container_width=True, type="primary", disabled=(target_strike is None))

    if run_sim and target_strike is not None:
        strategy_val = strategy_map[strategy_display]
        with st.spinner(f"Simulating {strategy_display} trade path..."):
            result = backtester.run_simple_backtest(local_ticker, start_date.strftime("%Y-%m-%d"), dte, float(target_strike), strategy_val)
            
            if "error" in result:
                st.error(result["error"])
                return
                
            data = result["data"]
            
            st.divider()
            st.markdown("#### 📊 Simulation Results")
            
            final_pl = result["final_pl"]
            max_drawdown = result["max_drawdown"]
            roc = result["roc"]
            entry_cost = result["entry_cost"]
            
            pl_color = "normal" if final_pl >= 0 else "inverse"
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Final Realized P/L", f"${final_pl:,.2f}", delta=f"${final_pl:,.2f}", delta_color=pl_color)
            m2.metric("Return on Risk (ROC)", f"{roc:.1f}%")
            m3.metric("Entry Premium", f"${entry_cost:,.2f}")
            m4.metric("Max Drawdown", f"${max_drawdown:,.2f}", delta=f"${max_drawdown:,.2f}", delta_color="inverse")
            
            st.caption(f"**Entry Strike Price:** ${result['strike']:,.2f}")
            
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            line_color = "#00ffcc" if final_pl >= 0 else "#ff4b4b"
            
            # Add P/L Trace
            fig.add_trace(
                go.Scatter(x=data["Date"], y=data["P/L"], name="Trade P/L ($)", line=dict(color=line_color, width=3)),
                secondary_y=False,
            )
            
            # Add Underlying Price Trace
            fig.add_trace(
                go.Scatter(x=data["Date"], y=data["Underlying"], name="Stock Price ($)", line=dict(color="gray", width=2, dash="dot")),
                secondary_y=True,
            )
            
            fig.update_layout(title_text=f"Historical Trade Path: {strategy_display} on {local_ticker}", template="plotly_dark", hovermode="x unified")
            fig.update_yaxes(title_text="Options P/L ($)", secondary_y=False)
            fig.update_yaxes(title_text="Underlying Price ($)", secondary_y=True, showgrid=False)
            
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("View Daily Ledger Data"):
                st.dataframe(data, use_container_width=True)

def main():
    ticker, selected_module = render_sidebar()
    
    if selected_module == "Dashboard":
        render_dashboard(ticker)
    elif selected_module == "Volatility Lab":
        render_vol_lab(ticker)
    elif selected_module == "Discovery (LEAPS/Wheel)":
        render_discovery()
    elif selected_module == "Backtesting Lab":
        render_backtester(ticker)
    elif selected_module == "Watchlist":
        render_watchlist()
        
    st.divider()
    render_broker_bridge()

if __name__ == "__main__":
    main()
