import yfinance as yf
import redis
import json
import os
import pandas as pd
import numpy as np

class DataManager:
    """
    Manages financial data ingestion from yfinance with a robust Redis caching layer
    to handle high traffic and prevent API rate limiting.
    """

    def __init__(self):
        self.yf = yf
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("REDIS_PORT", 6379))
        try:
            self.cache = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            self.cache.ping()
            self.cache_enabled = True
        except redis.ConnectionError:
            print("Warning: Redis cache not available. Falling back to direct API calls.")
            self.cache_enabled = False
            
        # Default cache expiration: 15 minutes (900 seconds)
        self.cache_ttl = 900

    def get_stock_data(self, ticker: str) -> dict:
        """
        Fetches core stock data (price, fundamentals) for a given ticker.

        Args:
            ticker (str): The stock ticker symbol.

        Returns:
            dict: Dictionary containing stock data.
        """
        ticker = ticker.upper()
        cache_key = f"deltaflow:stock_data:{ticker}"

        if self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)

        # Fetch from yfinance if not cached
        stock = yf.Ticker(ticker)
        try:
            info = stock.info
        except Exception:
            return {"error": f"Failed to fetch data for {ticker}"}

        # Extract only the necessary data to keep the payload lightweight
        data = {
            "symbol": ticker,
            "current_price": info.get("currentPrice", info.get("previousClose", 0.0)),
            "roe": info.get("returnOnEquity", 0.0),
            "fcf": info.get("freeCashflow", 0.0),
            "market_cap": info.get("marketCap", 0),
            "beta": info.get("beta", 1.0),
            "dividend_yield": info.get("dividendYield", 0.0),
            "sector": info.get("sector", "Unknown")
        }

        if self.cache_enabled:
            self.cache.setex(cache_key, self.cache_ttl, json.dumps(data))

        return data

    def calculate_historical_volatility(self, ticker: str, window: int = 30) -> float:
        """
        Calculates annualized historical volatility (HV) based on the last N days.
        """
        stock = self.yf.Ticker(ticker)
        hist = stock.history(period=f"{window+5}d")
        
        if len(hist) < window:
            return 0.0
            
        # Calculate log returns
        import numpy as np
        close = hist['Close']
        log_returns = np.log(close / close.shift(1)).dropna()
        
        # Annualized Standard Deviation
        hv = log_returns.tail(window).std() * np.sqrt(252)
        return float(hv)

    def get_options_expirations(self, ticker: str) -> list:
        """
        Fetches available options expiration dates.
        """
        ticker = ticker.upper()
        cache_key = f"deltaflow:options_expirations:{ticker}"
        
        if self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
                
        stock = yf.Ticker(ticker)
        try:
            expirations = list(stock.options)
        except Exception:
            return []
            
        if self.cache_enabled:
            # Cache expirations for longer (12 hours) as they don't change frequently intra-day
            self.cache.setex(cache_key, 43200, json.dumps(expirations))
            
        return expirations

    def get_options_chain(self, ticker: str, expiration: str) -> dict:
        """
        Fetches the options chain for a specific ticker and expiration date.

        Args:
            ticker (str): The stock ticker symbol.
            expiration (str): The expiration date string (YYYY-MM-DD).

        Returns:
            dict: Dictionary containing calls and puts DataFrames.
        """
        ticker = ticker.upper()
        cache_key = f"deltaflow:options_chain:{ticker}:{expiration}"

        if self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return {
                    "calls": pd.DataFrame(data["calls"]),
                    "puts": pd.DataFrame(data["puts"])
                }

        stock = yf.Ticker(ticker)
        try:
            chain = stock.option_chain(expiration)
            data = {
                "calls": chain.calls.to_dict(orient="records"),
                "puts": chain.puts.to_dict(orient="records")
            }
        except Exception:
            return {"error": f"Failed to fetch options chain for {ticker} at {expiration}"}

        if self.cache_enabled:
            # Cache chain for 5 minutes (300 seconds) for real-time responsiveness
            self.cache.setex(cache_key, 300, json.dumps(data))

        return {
            "calls": chain.calls,
            "puts": chain.puts
        }

    def get_volatility_surface_data(self, ticker: str, limit: int = 5) -> list:
        """
        Fetches IV data across multiple expirations to build a surface.
        """
        expirations = self.get_options_expirations(ticker)[:limit]
        surface_points = []
        
        from datetime import datetime
        now = datetime.now()
        
        for exp in expirations:
            chain = self.get_options_chain(ticker, exp)
            if "error" in chain: continue
            
            calls = chain["calls"]
            dte = (datetime.strptime(exp, "%Y-%m-%d") - now).days / 365.0
            
            for _, row in calls.iterrows():
                surface_points.append({
                    "dte": dte,
                    "strike": row["strike"],
                    "iv": row["impliedVolatility"]
                })
                
        return surface_points

    def get_market_universe(self, category: str, sample_size: int = 25) -> list:
        """
        Returns a randomized curated list of tickers based on the selected market universe.
        """
        import random
        universes = {
            "Mega-Cap Tech": [
                "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "CSCO", "ORCL", 
                "ADBE", "CRM", "AMD", "INTC", "TXN", "QCOM", "IBM", "NOW", "INTU", "AMAT", 
                "MU", "LRCX", "ADI", "PANW", "KLAC", "SNPS", "CDNS", "CRWD", "FTNT", "MCHP",
                "ON", "NXPI", "MRVL", "WDAY", "ROP", "TEAM", "DDOG", "ZS", "NET", "PLTR", "SMCI"
            ],
            "Financials": [
                "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V", "MA", "PYPL", 
                "BLK", "SPGI", "CME", "SCHW", "CB", "MMC", "PGR", "AON", "ICE", "USB", 
                "PNC", "TFC", "COF", "BK", "AIG", "MET", "PRU", "TRV", "ALL", "DFS",
                "FITB", "MTB", "STT", "NTRS", "SYF", "KEY", "CFG", "RF", "HBAN", "CMA"
            ],
            "Healthcare": [
                "JNJ", "UNH", "LLY", "MRK", "ABBV", "PFE", "TMO", "DHR", "ABT", "AMGN", 
                "ISRG", "SYK", "MDT", "VRTX", "ELV", "REGN", "CI", "ZTS", "BSX", "GILD", 
                "BDX", "MCK", "CVS", "HCA", "BMY", "DHR", "IDXX", "IQV", "A", "MTD",
                "DXCM", "ALGN", "ZBH", "CTLT", "WST", "RMD", "STE", "COO", "HOLX", "XRAY"
            ],
            "Consumer Defensive": [
                "PG", "KO", "PEP", "WMT", "COST", "MCD", "NKE", "SBUX", "HD", "LOW",
                "PM", "MO", "TGT", "DG", "DLTR", "KR", "SYY", "ADM", "GIS", "K",
                "CAG", "SJM", "HRL", "CPB", "TAP", "STZ", "BF.B", "MNST", "CL", "KMB",
                "EL", "CHD", "CLX", "HSY", "MKC", "TSN", "WBA", "RAD", "GPC", "ORLY"
            ],
            "Energy": [
                "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "PXD", 
                "HES", "HAL", "WMB", "KMI", "BKR", "DVN", "FANG", "CTRA", "MRO", "TRGP", 
                "EQT", "AR", "CHK", "SWN", "RRC", "MTDR", "PR", "SM", "CPE", "MUSA",
                "DK", "PBF", "CVI", "PARR", "HP", "NBR", "PTEN", "RES", "LBRT", "NEX"
            ]
        }
        
        full_list = universes.get(category, universes["Mega-Cap Tech"])
        # Ensure we don't try to sample more than what's available
        actual_sample_size = min(sample_size, len(full_list))
        return random.sample(full_list, actual_sample_size)

    def get_leaps_metrics(self, ticker: str, target_delta: float = 0.80) -> dict:
        """
        Fetches the LEAPS options metrics targeting a specific deep ITM delta.
        """
        expirations = self.get_options_expirations(ticker)
        if not expirations:
            return {"error": "No options available"}
            
        from datetime import datetime
        now = datetime.now()
        
        # Find the furthest expiration
        furthest_exp = expirations[-1]
        dte = (datetime.strptime(furthest_exp, "%Y-%m-%d") - now).days
        
        # Usually LEAPS are > 365 days
        if dte < 180:
            return {"error": "No long-term expirations"}
            
        chain = self.get_options_chain(ticker, furthest_exp)
        if "error" in chain:
            return {"error": "Failed to fetch chain"}
            
        calls = chain["calls"]
        if calls.empty or 'impliedVolatility' not in calls.columns:
            return {"error": "Invalid chain data"}
            
        stock_data = self.get_stock_data(ticker)
        current_price = stock_data.get("current_price", 0)
        if current_price == 0:
            return {"error": "No price data"}
            
        from engine.calculator import calculate_greeks
        
        best_strike = None
        best_diff = 1.0
        best_iv = 0.0
        best_cost = 0.0
        best_delta = 0.0
        
        # Filter ITM calls to speed up search (strike < current_price)
        itm_calls = calls[calls['strike'] < current_price]
        
        for _, row in itm_calls.iterrows():
            strike = row['strike']
            iv = row['impliedVolatility']
            cost = row['lastPrice']
            
            greeks = calculate_greeks('call', current_price, strike, dte/365.0, 0.05, iv)
            delta = greeks['delta']
            
            diff = abs(delta - target_delta)
            if diff < best_diff:
                best_diff = diff
                best_strike = strike
                best_iv = iv
                best_cost = cost
                best_delta = delta
                
        if best_strike is None:
            return {"error": "Could not find suitable ITM call"}
            
        return {
            "target_strike": best_strike,
            "delta": best_delta,
            "entry_cost": best_cost,
            "leaps_iv": best_iv,
            "dte": dte
        }

    def get_company_profile(self, ticker: str) -> dict:
        """
        Fetches detailed company profile information for the UI modal.
        """
        ticker = ticker.upper()
        cache_key = f"deltaflow:company_profile:{ticker}"
        
        if self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
                
        stock = yf.Ticker(ticker)
        try:
            info = stock.info
            data = {
                "name": info.get("shortName", info.get("longName", ticker)),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "summary": info.get("longBusinessSummary", "No summary available."),
                "website": info.get("website", ""),
                "employees": info.get("fullTimeEmployees", "N/A"),
                "pe_ratio": info.get("trailingPE", "N/A")
            }
        except Exception:
            return {"error": "Failed to fetch company profile."}
            
        if self.cache_enabled:
            self.cache.setex(cache_key, 86400, json.dumps(data)) # Cache for 24 hours
            
        return data
        
    def get_company_news(self, ticker: str) -> list:
        """
        Fetches recent news articles for the company.
        """
        ticker = ticker.upper()
        cache_key = f"deltaflow:company_news:{ticker}"
        
        if self.cache_enabled:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
                
        stock = yf.Ticker(ticker)
        try:
            news = stock.news
            
            # Attempt to get a short company name for filtering
            try:
                comp_name = stock.info.get("shortName", ticker).split(" ")[0].lower()
            except:
                comp_name = ticker.lower()
                
            articles = []
            for item in news:
                content = item.get("content", item)
                title = content.get("title", "News Article")
                
                # Filter out generic syndicated news (very common with Yahoo Finance)
                # Ensure the ticker or the company name is actually in the title or summary
                searchable_text = (title + " " + content.get("summary", "")).lower()
                if ticker.lower() not in searchable_text and comp_name not in searchable_text:
                    # Allow broad index ETFs to show general market news
                    if ticker not in ["SPY", "QQQ", "DIA", "IWM"]:
                        continue
                        
                provider = content.get("provider", {})
                publisher = provider.get("displayName", "Source") if isinstance(provider, dict) else "Source"
                
                # pubDate is usually ISO format 'YYYY-MM-DDTHH:MM:SSZ'
                pub_date = content.get("pubDate", "")
                if "T" in pub_date:
                    pub_date = pub_date.replace("T", " ")[:16]
                    
                # Safely extract URL since yfinance now returns dictionaries for links
                raw_link = content.get("canonicalUrl", content.get("clickThroughUrl", content.get("link", "#")))
                if isinstance(raw_link, dict):
                    link = raw_link.get("url", "#")
                else:
                    link = raw_link
                    
                articles.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "timestamp_str": pub_date
                })
                
                # Only grab top 5 highly-relevant articles
                if len(articles) >= 5:
                    break
                    
        except Exception:
            return []
            
        if self.cache_enabled:
            self.cache.setex(cache_key, 3600, json.dumps(articles)) # Cache for 1 hour
            
        return articles
