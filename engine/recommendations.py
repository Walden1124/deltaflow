from engine.data_manager import DataManager

class RecommendationsEngine:
    """
    Logic for stock discovery modules: 'Prime LEAPS' and 'Wheelhouse'.
    Focuses on high-quality underlying equities based on profitability metrics.
    """

    def __init__(self):
        self.data_manager = DataManager()

    def analyze_prime_leaps(self, tickers: list, min_roe: float = 0.15, require_fcf: bool = True, target_delta: float = 0.80, progress_callback=None) -> list:
        """
        Scans a list of tickers to find candidates suitable for LEAPS (Long-term Equity Anticipation Securities).
        Criteria: High Return on Equity (ROE), strong Free Cash Flow (FCF), and availability of deep ITM options.
        """
        import concurrent.futures

        candidates = []
        total = len(tickers)
        completed = 0

        def process_ticker(ticker):
            # 1. Fundamental check
            data = self.data_manager.get_stock_data(ticker)
            if "error" in data: return None
            
            roe = data.get("roe")
            fcf = data.get("fcf")
            
            if roe is None or roe < min_roe:
                return None
            if require_fcf and (fcf is None or fcf <= 0):
                return None
                
            # 2. Options check
            leaps_data = self.data_manager.get_leaps_metrics(ticker, target_delta=target_delta)
            if "error" in leaps_data:
                return None
                
            # Combine data for final output
            return {
                "symbol": ticker,
                "current_price": data.get("current_price"),
                "target_strike": leaps_data["target_strike"],
                "delta": leaps_data["delta"],
                "entry_cost": leaps_data["entry_cost"],
                "leaps_iv": leaps_data["leaps_iv"],
                "dte": leaps_data["dte"],
                "score": roe * 100
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(process_ticker, t): t for t in tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                res = future.result()
                if res:
                    candidates.append(res)
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                    
        # Sort by score descending (or could sort by lowest IV)
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        return candidates
        
    def analyze_fallen_angels(self, tickers: list, min_drop_pct: float = -25.0, timeframe: str = "Intraday", progress_callback=None) -> list:
        """
        Scans for Fallen Angels (Discounted Options/Stocks).
        If Intraday: Scans for options that fell intraday.
        If Historical: Scans for underlying stocks that fell X% over timeframe, returns their LEAPS.
        """
        import concurrent.futures
        import pandas as pd
        from datetime import datetime

        candidates = []
        total = len(tickers)
        completed = 0
        
        # Map timeframe strings to yfinance period strings
        period_map = {
            "1 Week": "5d",
            "1 Month": "1mo",
            "6 Months": "6mo",
            "52 Weeks": "1y"
        }

        def process_ticker(ticker):
            stock = self.data_manager.yf.Ticker(ticker)
            
            if timeframe == "Intraday":
                # 1. Fetch nearest options chain
                expirations = self.data_manager.get_options_expirations(ticker)
                if not expirations:
                    return None
                    
                # Scan the first 3 expirations for liquid discounted contracts
                for exp in expirations[:3]:
                    chain = self.data_manager.get_options_chain(ticker, exp)
                    if "error" in chain:
                        continue
                        
                    calls = chain.get("calls", pd.DataFrame())
                    if calls.empty or "percentChange" not in calls.columns:
                        continue
                        
                    # Filter for massive drops
                    discounted = calls[
                        (calls["percentChange"] <= min_drop_pct) & 
                        (calls["volume"] > 10) & 
                        (calls["openInterest"] > 50)
                    ]
                    
                    if not discounted.empty:
                        # Grab the most discounted liquid contract
                        best_contract = discounted.sort_values(by="percentChange").iloc[0]
                        return {
                            "symbol": ticker,
                            "type": "Call Option",
                            "contract": best_contract["contractSymbol"],
                            "strike": best_contract["strike"],
                            "dte": (datetime.strptime(exp, "%Y-%m-%d") - datetime.now()).days,
                            "current_price": best_contract["lastPrice"],
                            "drop_pct": best_contract["percentChange"]
                        }
                return None
                
            else:
                # Historical Drop: Scan underlying stock
                period = period_map.get(timeframe, "1y")
                hist = stock.history(period=period)
                if hist.empty or len(hist) < 2:
                    return None
                    
                start_price = hist.iloc[0]["Close"]
                end_price = hist.iloc[-1]["Close"]
                drop_pct = ((end_price - start_price) / start_price) * 100
                
                # If stock fell by at least min_drop_pct (e.g. -25%)
                if drop_pct <= min_drop_pct:
                    # Stock crashed! Pull its LEAPS as a discount play
                    leaps_data = self.data_manager.get_leaps_metrics(ticker, target_delta=0.70)
                    if "error" in leaps_data:
                        return None
                        
                    return {
                        "symbol": ticker,
                        "type": "Stock Drop -> LEAPS",
                        "contract": "LEAPS Call (~0.70 Delta)",
                        "strike": leaps_data["target_strike"],
                        "dte": leaps_data["dte"],
                        "current_price": leaps_data["entry_cost"],
                        "drop_pct": drop_pct # This is the UNDERLYING drop
                    }
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(process_ticker, t): t for t in tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                res = future.result()
                if res:
                    candidates.append(res)
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                    
        candidates.sort(key=lambda x: x.get("drop_pct", 0)) # Sort by most negative drop
        return candidates

    def analyze_wheelhouse(self, tickers: list, min_dividend: float = 0.0, sector: str = "All") -> list:
        """
        Scans for 'Wheelhouse' candidates (ideal for the Wheel strategy).
        Criteria: Lower beta, stable blue-chip characteristics, and optional dividend yield.
        """
        candidates = []
        for ticker in tickers:
            data = self.data_manager.get_stock_data(ticker)
            
            if "error" in data:
                continue
                
            beta = data.get("beta")
            div = data.get("dividend_yield", 0.0)
            stock_sector = data.get("sector", "Unknown")
            
            # Filter logic
            if beta is not None and 0.5 < beta < 1.3:
                if div >= min_dividend:
                    if sector == "All" or sector == stock_sector:
                        data["strategy"] = "Wheelhouse"
                        candidates.append(data)
                
        return candidates
