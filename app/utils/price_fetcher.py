import yfinance as yf
import logging
import requests
import re
from typing import Optional, Dict, List
import trafilatura
from datetime import datetime
import time
import asyncio

logger = logging.getLogger(__name__)

class PriceFetcher:
    """Handles fetching live prices from various sources"""
    
    def __init__(self):
        self.usd_to_gbp_rate = None
        self.last_rate_update = None
        
        # CoinGecko cryptocurrency mappings
        self.crypto_mappings = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'FET': 'fetch-ai',
            'TRX': 'tron',
            'ADA': 'cardano',
            'DOT': 'polkadot',
            'LINK': 'chainlink',
            'MATIC': 'polygon',
            'AVAX': 'avalanche-2',
            'ATOM': 'cosmos',
            'XRP': 'ripple',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'UNI': 'uniswap',
            'AAVE': 'aave',
            'COMP': 'compound-governance-token',
            'SUSHI': 'sushi',
            'YFI': 'yearn-finance',
            'MKR': 'maker',
            'SNX': 'synthetix-network-token',
            'CRV': 'curve-dao-token',
            'BAL': 'balancer',
            'LUNA': 'terra-luna-2',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'FTM': 'fantom',
            'NEAR': 'near',
            'HBAR': 'hedera-hashgraph',
            'ICP': 'internet-computer',
            'THETA': 'theta-token',
            'XTZ': 'tezos',
            'EOS': 'eos',
            'FLOW': 'flow',
            'FIL': 'filecoin',
            'MANA': 'decentraland',
            'SAND': 'the-sandbox',
            'AXS': 'axie-infinity',
            'CRO': 'crypto-com-chain',
            'SHIB': 'shiba-inu',
            'DOGE': 'dogecoin'
        }
        
        # Special fund mappings for funds that don't work with yfinance
        self.special_funds = {
            'GB00BYVGKV59': {
                'name': 'Baillie Gifford Positive Change Class B - Acc',
                'hl_url': 'https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/b/baillie-gifford-positive-change-class-b-accumulation',
                'ft_url': 'https://markets.ft.com/data/funds/tearsheet/summary?s=GB00BYVGKV59:GBX'
            },
            'LU1033663649': {
                'name': 'Fidelity Global Technology Class W - Acc',
                'hl_url': 'https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/f/fidelity-global-technology-w-gbp-accumulation',
                'ft_url': 'https://markets.ft.com/data/funds/tearsheet/summary?s=LU1033663649:GBP'
            },
            'LU0345781172': {
                'name': 'Ninety One GSF Global Natural Resources Class I - Acc',
                'hl_url': 'https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/n/ninety-one-gsf-global-natural-resources-class-i-accumulation',
                'ft_url': 'https://markets.ft.com/data/funds/tearsheet/performance?s=LU0954591375:GBP'
            },
            'GB00BMN91T34': {
                'name': 'UBS S&P 500 Index Class C - Acc',
                'hl_url': 'https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/u/ubs-s-and-p-500-index-accumulation',
                'ft_url': 'https://markets.ft.com/data/funds/tearsheet/summary?s=GB00BMN91T34:GBP'
            }
        }
        
        # Fallback prices (manually updated periodically)
        self.fallback_prices = {
            'GB00BYVGKV59': 3.5510,   # Baillie Gifford Positive Change (355.10p)
            'LU1033663649': 9.334,    # Fidelity Global Technology (933.40p)
            'LU0345781172': 48.24,    # Ninety One Natural Resources
            'GB00BMN91T34': 2.1106    # UBS S&P 500 (211.06p)
        }
    
    def get_crypto_price_from_coingecko(self, symbol: str) -> Optional[float]:
        """Fetch cryptocurrency price from CoinGecko"""
        try:
            clean_symbol = symbol.replace('-USD', '').upper()
            if clean_symbol not in self.crypto_mappings:
                return None
                
            coin_id = self.crypto_mappings[clean_symbol]
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=gbp"
            
            for attempt in range(3):
                try:
                    if attempt > 0: time.sleep(1.5 * attempt)
                    headers = {
                        'User-Agent': 'Mozilla/5.0',
                        'Accept': 'application/json'
                    }
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if coin_id in data and 'gbp' in data[coin_id]:
                            return float(data[coin_id]['gbp'])
                    elif response.status_code == 429:
                        continue
                        
                except Exception:
                    continue
                break
        except Exception as e:
            logger.error(f"Error fetching CoinGecko price: {e}")
        return None

    # Simple in-memory cache: {symbol: {'price': float, 'time': datetime}}
    _PRICE_CACHE = {}
    _CACHE_TTL_SECONDS = 300 # 5 Minutes Cache to be safe

    def get_price(self, symbol: str, use_previous_close: bool = False) -> Optional[float]:
        """Fetch current price for a given symbol with caching"""
        try:
            if not symbol: return None
            
            # Check Cache
            now = datetime.now()
            cached = self._PRICE_CACHE.get(symbol)
            if cached:
                age = (now - cached['time']).total_seconds()
                # If cache is valid (abs(age) handles partial clock weirdness, though unexpected)
                if age < self._CACHE_TTL_SECONDS:
                    # logger.info(f"PriceFetcher: Using cached value for {symbol} (Age: {int(age)}s)")
                    return cached['price']

            # Crypto
            is_crypto = False
            clean_symbol = symbol.replace('-USD', '').upper()
            if clean_symbol in self.crypto_mappings:
                is_crypto = True
                price = self.get_crypto_price_from_coingecko(symbol)
                if price:
                    self._PRICE_CACHE[symbol] = {'price': price, 'time': now}
                    return price
                
                # If CoinGecko failed, enforce -USD suffix for fallbacks
                if not symbol.endswith('-USD'):
                    symbol = f"{clean_symbol}-USD"
            
            # Special funds
            if symbol in self.special_funds:
                price = self.get_special_fund_price(symbol)
                if price:
                    self._PRICE_CACHE[symbol] = {'price': price, 'time': now}
                    return price
                
            # Yahoo Finance
            ticker = yf.Ticker(symbol)
            
            price = None
            currency = 'USD' # Default assumption
            
            # Method 1: fast_info (Newer, faster, less prone to breaking)
            try:
                if use_previous_close:
                    price = ticker.fast_info.previous_close
                    currency = ticker.fast_info.currency
                    # logger.info(f"PriceFetcher: Got previous_close for {symbol}: {price} {currency}")
                else:
                    price = ticker.fast_info.last_price
                    currency = ticker.fast_info.currency
                    # logger.info(f"PriceFetcher: Got fast_info for {symbol}: {price} {currency}")
            except Exception as e:
                # logger.warning(f"PriceFetcher: fast_info failed for {symbol}: {e}")
                pass
            
            # Method 2: History (Reliable Fallback)
            if price is None:
                try:
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        price = float(hist['Close'].iloc[-1])
                        meta = ticker.history_metadata
                        if meta and 'currency' in meta:
                            currency = meta['currency']
                        elif symbol.endswith('.L'):
                            currency = 'GBp'
                        # logger.info(f"PriceFetcher: Got history price for {symbol}: {price} {currency}")
                except Exception as e:
                    # logger.warning(f"PriceFetcher: history failed for {symbol}: {e}")
                    pass

            # Method 3: Google Finance Fallback (If Yahoo Failed)
            if price is None:
                # logger.info(f"PriceFetcher: Yahoo failed for {symbol}, trying Google Finance...")
                result = self.scrape_google_finance(symbol)
                if result:
                    price, detected_currency = result
                    if detected_currency:
                        currency = detected_currency
                    elif symbol.endswith('.L'): 
                         # Fallback if Google gave just number without currency symbol
                         # Heuristic: If > 500, assume Pence (GBp)
                         # VUAG.L (98.0) -> GBP (Don't divide)
                         # RR.L (1250) -> GBp (Divide)
                         if float(price) > 500:
                             currency = 'GBp'
                         else:
                             currency = 'GBP'

            # Process Price
            if price is not None:
                final_price = float(price)
                
                # Normalization
                if currency == 'GBp' or currency == 'GBX': 
                    final_price = final_price / 100
                elif symbol.endswith('.L') and final_price > 500 and currency != 'GBP':
                     # Catch-all for UK stocks that look like Pence but currency wasn't set to GBP explicitly
                     final_price = final_price / 100
                    
                if currency == 'USD':
                    final_price = self.convert_usd_to_gbp(final_price)
                
                # Update Cache
                self._PRICE_CACHE[symbol] = {'price': final_price, 'time': now}
                return final_price
                
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            # Fallback to cache even if expired? Optional, but stick to standard for now.
        
        return None

    def get_special_fund_price(self, isin: str) -> Optional[float]:
        """Get price for special funds using multiple sources"""
        fund_info = self.special_funds.get(isin)
        if not fund_info: return None
            
        # 1. Try Yahoo Finance first (if symbol available)
        if 'yahoo_symbol' in fund_info:
            try:
                ticker = yf.Ticker(fund_info['yahoo_symbol'])
                try:
                    price = ticker.fast_info.last_price
                    if price:
                        if isin.startswith('GB') and price > 10:
                            price = price / 100
                        return price
                except:
                    pass
            except Exception as e:
                logger.warning(f"Yahoo Finance failed for special fund {isin}: {e}")
        
        # 2. Try Financial Times web scraping (Prioritized over HL as HL can be delayed)
        if 'ft_url' in fund_info:
             price = self.scrape_ft_price(fund_info['ft_url'])
             if price: 
                 logger.info(f"Got price from FT for {isin}: {price}")
                 return price

        # 3. Try HL web scraping
        if 'hl_url' in fund_info:
            price = self.scrape_hl_price(fund_info['hl_url'])
            if price: return price
             
        # 4. Use fallback price
        if isin in self.fallback_prices:
            logger.info(f"Using fallback price for {fund_info['name']}")
            return self.fallback_prices[isin]
            
        return None
    
    def scrape_hl_price(self, url: str) -> Optional[float]:
        """Scrape price from Hargreaves Lansdown fund page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200: return None
            
            html_content = response.text
            
            # HL displays prices in PENCE (e.g., "355.10p")
            price_patterns = [
                r'Sell:\s*([1-9][\d,]{3,6}\.?\d*)p',
                r'Buy:\s*([1-9][\d,]{3,6}\.?\d*)p',
                r'Price:\s*([1-9][\d,]{3,6}\.?\d*)p',
                r'>([1-9][\d,]{3,6}\.?\d*)p</span>',
                r'Sell:\s*(\d{3,4}\.?\d*)p',
                r'Buy:\s*(\d{3,4}\.?\d*)p',
                r'(\d{3,4}\.?\d*)p\s+(?:Buy|Sell)',
            ]
            
            all_matches = []
            
            for priority, pattern in enumerate(price_patterns):
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    try:
                        clean_match = match.replace(',', '')
                        price_pence = float(clean_match)
                        if 10 <= price_pence <= 500000:
                            all_matches.append((price_pence, priority))
                    except ValueError:
                        continue
            
            if all_matches:
                all_matches.sort(key=lambda x: x[1])
                return all_matches[0][0] / 100
        except Exception as e:
            logger.warning(f"Error scraping HL for {url}: {e}")
        return None

    def scrape_ft_price(self, url: str) -> Optional[float]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            content = response.text
            
            # 1. Try regex on raw HTML (ft.com structure)
            # Pattern: Price (GBP)</span><span class="mod-ui-data-list__value">10.45</span>
            # Also handle GBX (Pence) seen for some funds like UBS
            html_patterns = [
                # GBP Patterns
                (r'Price\s*\(GBP\)</span>\s*<span[^>]*>(\d+\.?\d*)</span>', 1.0),
                (r'Price\s*\(GBP\)\s*(\d+\.?\d*)', 1.0),
                (r'Price\s*</span>\s*<span[^>]*>£?(\d+\.?\d*)</span>', 1.0),
                
                # GBX Patterns (Pence) -> Divide by 100
                (r'Price\s*\(GBX\)</span>\s*<span[^>]*>(\d+\.?\d*)</span>', 100.0),
                (r'Price\s*\(GBX\)\s*(\d+\.?\d*)', 100.0),
            ]
            
            for pattern, divisor in html_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    return float(matches[0]) / divisor

            # 2. Try trafilatura extraction if HTML regex failed
            try:
                extracted = trafilatura.extract(content)
                if extracted:
                    # Check GBP
                    matches = re.findall(r'Price\s*\(GBP\)\s*(\d+\.?\d*)', extracted, re.IGNORECASE)
                    if matches:
                        return float(matches[0])
                        
                    # Check GBX
                    matches = re.findall(r'Price\s*\(GBX\)\s*(\d+\.?\d*)', extracted, re.IGNORECASE)
                    if matches:
                        return float(matches[0]) / 100.0
            except:
                pass
                
        except Exception:
             pass
        return None
    
    def scrape_google_finance(self, symbol: str) -> Optional[tuple]:
        """Scrape price from Google Finance fallback. Returns (price, currency_code)"""
        try:
            # Simple header to look like browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Map common suffixes to Google format if possible
            # Yahoo: RR.L -> Google: RR or LON:RR
            # Try search query generic first: q=symbol
            query = symbol
            if symbol.endswith('.L'):
                # Try explicit LON: prefix for UK
                # RR.L -> LON:RR
                base = symbol.replace('.L', '')
                url = f"https://www.google.com/finance/quote/{base}:LON"
            elif symbol == 'AAPL':
                 url = "https://www.google.com/finance/quote/AAPL:NASDAQ"
            else:
                 # Generic search fallback
                 url = f"https://www.google.com/finance?q={symbol}"

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200: 
                return None
            
            content = response.text
            
            # Regex for the specific class provided by browser agent
            # <div class="YMlKec fxKbKc">185.10</div>
            # We look for YMlKec because fxKbKc might be layout specific
            
            # Look for: class="YMlKec fxKbKc">£10.50</div> or >10.50</div>
            # Content might have currency symbol
            
            matches = re.findall(r'class="YMlKec fxKbKc">([^<]+)</div>', content)
            if matches:
                 raw_text = matches[0]
                 # Detect currency
                 currency = None
                 if 'GBX' in raw_text:
                     currency = 'GBX'
                 elif '£' in raw_text:
                     currency = 'GBP'
                 elif '$' in raw_text:
                     currency = 'USD'
                 elif '€' in raw_text:
                     currency = 'EUR'
                     
                 # Cleanup: Remove currency symbols ($, £, etc) and commas
                 clean = raw_text.replace('$', '').replace('£', '').replace(',', '').replace('GBX', '').strip()
                 return (float(clean), currency)
                 
        except Exception as e:
            logger.warning(f"Google Finance scrape failed for {symbol}: {e}")
        return None

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch prices for multiple symbols"""
        prices = {}
        for symbol in symbols:
            p = self.get_price(symbol)
            if p: prices[symbol] = p
        return prices

    async def get_price_async(self, symbol: str, use_previous_close: bool = False) -> Optional[float]:
        """Fetch current price asynchronously"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_price, symbol, use_previous_close)

    async def get_multiple_prices_async(self, symbols: List[str], use_previous_close: bool = False) -> Dict[str, float]:
        """Fetch prices for multiple symbols in parallel"""
        prices = {}
        # Limit concurrency to avoid rate limits (Reduced from 10 to 4)
        sem = asyncio.Semaphore(4)
        import random

        async def fetch_with_sem(symbol: str):
            async with sem:
                # Add random jitter to avoid burst patterns
                await asyncio.sleep(random.uniform(0.5, 2.0))
                price = await self.get_price_async(symbol, use_previous_close)
                if price:
                    prices[symbol] = price

        await asyncio.gather(*(fetch_with_sem(s) for s in symbols))
        return prices
    
    def get_usd_to_gbp_rate(self) -> float:
        """Get current USD to GBP rate"""
        if (self.usd_to_gbp_rate and self.last_rate_update and 
            (datetime.now() - self.last_rate_update).seconds < 3600):
            return self.usd_to_gbp_rate
            
        try:
            ticker = yf.Ticker('GBPUSD=X')
            hist = ticker.history(period='1d')
            if not hist.empty:
                 rate = 1 / float(hist['Close'].iloc[-1])
                 self.usd_to_gbp_rate = rate
                 self.last_rate_update = datetime.now()
                 return rate
        except Exception:
            pass
        return 0.79 # Fallback

    def convert_usd_to_gbp(self, usd_price: float) -> Optional[float]:
        rate = self.get_usd_to_gbp_rate()
        return usd_price * rate
