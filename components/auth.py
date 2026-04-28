import os
import streamlit as st
from supabase import create_client, Client

class AuthManager:
    """
    Manages Supabase authentication, user sessions, and persistent watchlists.
    """

    def __init__(self):
        # In a Streamlit environment, we should prioritize st.secrets, then os.environ
        url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
        key = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))

        self.client_available = False
        if url and key:
            try:
                self.supabase: Client = create_client(url, key)
                self.client_available = True
            except Exception as e:
                st.error(f"Failed to initialize Supabase client: {e}")
        else:
            # Silent fallback to session state for demo purposes
            pass

    def get_watchlist(self, user_id: str) -> list:
        """
        Retrieves the persistent watchlist for a specific user.
        """
        if not self.client_available:
            return st.session_state.get("mock_watchlist", [])
            
        try:
            response = self.supabase.table("watchlists").select("ticker").eq("user_id", user_id).execute()
            if response.data:
                return [row["ticker"] for row in response.data]
            return []
        except Exception as e:
            return []

    def toggle_watchlist(self, user_id: str, ticker: str, is_currently_watched: bool):
        """
        Adds or removes a ticker from the user's watchlist.
        """
        ticker = ticker.upper()
        if not self.client_available:
            if "mock_watchlist" not in st.session_state:
                st.session_state.mock_watchlist = []
            if is_currently_watched:
                st.session_state.mock_watchlist.remove(ticker)
            else:
                st.session_state.mock_watchlist.append(ticker)
            return not is_currently_watched

        try:
            if is_currently_watched:
                self.supabase.table("watchlists").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
                return False
            else:
                self.supabase.table("watchlists").insert({"user_id": user_id, "ticker": ticker}).execute()
                return True
        except Exception as e:
            return is_currently_watched

    def get_alerts(self, user_id: str) -> dict:
        """
        Retrieves price alerts for a specific user. Returns a dict mapping ticker to alert price.
        """
        if not self.client_available:
            return st.session_state.get("mock_alerts", {})
            
        try:
            response = self.supabase.table("alerts").select("ticker, price").eq("user_id", user_id).execute()
            if response.data:
                return {row["ticker"]: row["price"] for row in response.data}
            return {}
        except Exception:
            return {}

    def set_alert(self, user_id: str, ticker: str, price: float):
        """
        Sets or updates a price alert for a ticker.
        """
        ticker = ticker.upper()
        if not self.client_available:
            if "mock_alerts" not in st.session_state:
                st.session_state.mock_alerts = {}
            if price <= 0:
                st.session_state.mock_alerts.pop(ticker, None)
            else:
                st.session_state.mock_alerts[ticker] = price
            return

        try:
            # Simple upsert logic
            self.supabase.table("alerts").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
            if price > 0:
                self.supabase.table("alerts").insert({"user_id": user_id, "ticker": ticker, "price": price}).execute()
        except Exception as e:
            st.error(f"Failed to set alert: {e}")
