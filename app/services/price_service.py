import requests
import yfinance as yf
import logging
import time
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class PriceService:
    def __init__(self):
        self.usd_to_gbp_rate = None
        self.last_rate_update = None

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol (stock, ETF, crypto)
        Returns price in GBP
        """
        if not symbol:
            return None
            
        try:
            # Check if it's a crypto symbol
            if symbol.upper() in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'XRP']:
                return self.get_crypto_price(symbol)
            
            # Yahoo Finance lookup
            ticker = yf.Ticker(symbol)
            
            # Try fast info first
            info = ticker.info
            
            # Try different price fields
            price_fields = ['regularMarketPrice', 'price', 'lastPrice', 'bid', 'ask']
            
            price = None
            currency = info.get('currency', 'GBP')
            
            for field in price_fields:
                if field in info and info[field]:
                    price = float(info[field])
                    break
            
            # Fallback to history if info fails
            if price is None:
                hist = ticker.history(period='1d')
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
            
            if price is not None:
                # Convert to GBP if needed
                if currency == 'USD':
                    return self.convert_usd_to_gbp(price)
                elif currency == 'GBP' or currency == 'GBp':
                    # Yahoo often returns GBp (pence) for UK stocks
                    if price > 5000 and symbol.endswith('.L'): # Heuristic for pence
                        return price / 100
                    return price
                    
            return price
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None

    def get_crypto_price(self, symbol: str) -> Optional[float]:
        """Get crypto price from CoinGecko or Yahoo fallback"""
        # Simplified version of the original logic
        try:
            # CoinGecko mapping
            cg_ids = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'SOL': 'solana',
                'ADA': 'cardano',
                'DOT': 'polkadot',
                'XRP': 'ripple'
            }
            
            cg_id = cg_ids.get(symbol.upper())
            if not cg_id:
                return None
                
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=gbp"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if cg_id in data and 'gbp' in data[cg_id]:
                    return float(data[cg_id]['gbp'])
                    
        except Exception as e:
            logger.warning(f"CoinGecko failed for {symbol}: {e}")
            
        return None

    def get_usd_to_gbp_rate(self) -> float:
        """Get current USD to GBP exchange rate"""
        try:
            # Check cache (1 hour)
            if (self.usd_to_gbp_rate and self.last_rate_update and 
                (datetime.now() - self.last_rate_update).seconds < 3600):
                return self.usd_to_gbp_rate
            
            ticker = yf.Ticker('GBPUSD=X')
            hist = ticker.history(period='1d')
            
            if not hist.empty:
                # GBPUSD=X is USD per GBP, so invert
                usd_per_gbp = float(hist['Close'].iloc[-1])
                self.usd_to_gbp_rate = 1 / usd_per_gbp
                self.last_rate_update = datetime.now()
                return self.usd_to_gbp_rate
                
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
            
        return 0.79 # Fallback

    def convert_usd_to_gbp(self, usd_price: float) -> float:
        rate = self.get_usd_to_gbp_rate()
        return usd_price * rate
