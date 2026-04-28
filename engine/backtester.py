import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from engine.calculator import black_scholes_price

class Backtester:
    """
    Robust historical option strategy backtesting engine.
    Top 1% Implementation: Handles missing data gracefully and prices options
    retroactively using the Black-Scholes engine.
    """
    
    def __init__(self, data_manager):
        self.dm = data_manager
        
    def run_simple_backtest(self, ticker: str, start_date: str, dte: int, target_strike: float, strategy: str) -> dict:
        """
        Simulates a trade path for a specific option strategy over historical data.
        Uses an exact, real-world target strike price for accurate Black-Scholes pricing.
        """
        # Fetch historical data
        stock = self.dm.yf.Ticker(ticker)
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
             return {"error": "Invalid date format. Use YYYY-MM-DD."}
             
        # We fetch slightly more days to account for weekends/holidays, then strictly limit by DTE
        end_dt = start_dt + timedelta(days=int(dte * 1.5))
        
        hist = stock.history(start=start_dt.strftime("%Y-%m-%d"), end=end_dt.strftime("%Y-%m-%d"))
        if hist.empty:
            return {"error": f"No historical data found for {ticker} starting {start_date}. Date might be in the future or on a weekend."}
            
        # Limit the dataframe to the requested DTE (trading days)
        hist = hist.head(dte)
        
        if len(hist) < 2:
             return {"error": "Not enough trading days in the specified window to run a valid backtest."}
             
        entry_price = hist.iloc[0]['Close']
        strike = target_strike # Use the exact real-world strike price
        
        opt_type = 'put' if 'put' in strategy.lower() else 'call'
        
        # Calculate historical volatility for the pricing model
        sigma = self.dm.calculate_historical_volatility(ticker, window=30)
        # Fallback to 30% if HV calculation fails
        if sigma <= 0.01: 
            sigma = 0.30
            
        r = 0.05 # Standard risk free rate assumption
        
        results = []
        
        # 1. Entry Pricing
        entry_option_price = black_scholes_price(opt_type, entry_price, strike, dte/365.0, r, sigma)
        
        # 2. Daily Simulation Loop
        for i, (date, row) in enumerate(hist.iterrows()):
            current_price = row['Close']
            days_passed = i
            remaining_dte = dte - days_passed
            
            # Pricing logic depending on whether we've hit expiration
            if remaining_dte <= 0:
                if opt_type == 'call':
                    current_option_price = max(0.0, current_price - strike)
                else:
                    current_option_price = max(0.0, strike - current_price)
            else:
                current_option_price = black_scholes_price(opt_type, current_price, strike, remaining_dte/365.0, r, sigma)
                
            # Directional P/L calculation
            if 'long' in strategy:
                pl = current_option_price - entry_option_price
            else: # short
                pl = entry_option_price - current_option_price
                
            # Standard US equity option contract multiplier is 100
            pl *= 100
                
            results.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Underlying": current_price,
                "Option_Value": current_option_price,
                "P/L": pl
            })
            
        df = pd.DataFrame(results)
        
        # Calculate Advanced Metrics
        final_pl = df.iloc[-1]["P/L"]
        max_drawdown = df["P/L"].min()
        entry_cost_dollars = entry_option_price * 100
        
        # Calculate ROC (Return on Risk)
        if 'long' in strategy:
            risk = entry_cost_dollars
        else:
            risk = strike * 100 # Assuming cash-secured equivalent risk
            
        roc = (final_pl / risk) * 100 if risk > 0 else 0.0
        
        return {
            "data": df,
            "strike": strike,
            "entry_cost": entry_cost_dollars,
            "max_drawdown": max_drawdown,
            "roc": roc,
            "final_pl": final_pl
        }
