"""
Investment search service - searches Yahoo Finance and CoinGecko for market instruments.

Returns unified results so the frontend can show autocomplete suggestions
when a user types an investment name in the Add Manual Investment modal.
"""

import logging
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchResult:
    """A single search result for a market instrument"""
    def __init__(self, symbol: str, name: str, instrument_type: str, exchange: str, currency: str = "USD"):
        self.symbol = symbol
        self.name = name
        self.type = instrument_type  # stock, etf, fund, crypto
        self.exchange = exchange
        self.currency = currency

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "type": self.type,
            "exchange": self.exchange,
            "currency": self.currency,
        }


class SearchService:
    """Searches multiple market data sources for instruments by name or ticker"""

    # In-memory cache: { query_key: { "results": [...], "time": datetime } }
    _cache: Dict[str, dict] = {}
    _CACHE_TTL_SECONDS = 300  # 5 minutes

    # Map Yahoo Finance quoteType values to our simplified types
    _YAHOO_TYPE_MAP = {
        "EQUITY": "stock",
        "ETF": "etf",
        "MUTUALFUND": "fund",
        "INDEX": "index",
        "FUTURE": "future",
        "CURRENCY": "currency",
        "CRYPTOCURRENCY": "crypto",
        "OPTION": "option",
    }

    # Top crypto coins for CoinGecko search (symbol -> coingecko_id)
    _CRYPTO_SYMBOLS = {
        "BTC": ("bitcoin", "Bitcoin"),
        "ETH": ("ethereum", "Ethereum"),
        "SOL": ("solana", "Solana"),
        "ADA": ("cardano", "Cardano"),
        "XRP": ("ripple", "XRP"),
        "DOT": ("polkadot", "Polkadot"),
        "DOGE": ("dogecoin", "Dogecoin"),
        "SHIB": ("shiba-inu", "Shiba Inu"),
        "AVAX": ("avalanche-2", "Avalanche"),
        "LINK": ("chainlink", "Chainlink"),
        "MATIC": ("polygon", "Polygon"),
        "ATOM": ("cosmos", "Cosmos"),
        "LTC": ("litecoin", "Litecoin"),
        "UNI": ("uniswap", "Uniswap"),
        "FET": ("fetch-ai", "Fetch.ai"),
        "TRX": ("tron", "TRON"),
        "NEAR": ("near", "NEAR Protocol"),
        "FIL": ("filecoin", "Filecoin"),
        "ICP": ("internet-computer", "Internet Computer"),
        "HBAR": ("hedera-hashgraph", "Hedera"),
    }

    def __init__(self):
        # Use a session to maintain cookies (bypasses basic Yahoo Finance rate limits for datacenter IPs)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self._yahoo_cookie_fetched = False

    def _ensure_yahoo_cookie(self):
        """Fetch a session cookie from Yahoo to bypass 429 rate limits on Render/AWS"""
        if not self._yahoo_cookie_fetched:
            try:
                self.session.get("https://finance.yahoo.com", timeout=10)
                self._yahoo_cookie_fetched = True
            except Exception as e:
                logger.warning(f"Failed to fetch initial Yahoo cookie: {e}")

    def _get_cached(self, cache_key: str) -> Optional[List[dict]]:
        """Return cached results if still valid, else None"""
        cached = self._cache.get(cache_key)
        if cached:
            age = (datetime.now() - cached["time"]).total_seconds()
            if age < self._CACHE_TTL_SECONDS:
                return cached["results"]
        return None

    def _set_cached(self, cache_key: str, results: List[dict]):
        self._cache[cache_key] = {"results": results, "time": datetime.now()}

    def search(self, query: str, limit: int = 15) -> List[dict]:
        """
        Search for market instruments matching the query.
        Combines Yahoo Finance (stocks, ETFs, funds) and CoinGecko (crypto).
        """
        if not query or len(query.strip()) < 1:
            return []

        query = query.strip()
        cache_key = f"{query.lower()}:{limit}"

        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        results: List[SearchResult] = []

        # Ensure we have a cookie before hitting Yahoo search
        self._ensure_yahoo_cookie()

        # 1. Search Yahoo Finance (stocks, ETFs, funds)
        yahoo_results = self._search_yahoo(query)
        results.extend(yahoo_results)

        # 2. Search CoinGecko (crypto) — only if query looks crypto-related
        #    or Yahoo didn't return enough results
        crypto_results = self._search_crypto(query)
        results.extend(crypto_results)

        # 3. Deduplicate by symbol (prefer Yahoo over CoinGecko for overlapping symbols)
        seen_symbols = set()
        deduplicated: List[dict] = []
        for r in results:
            key = r.symbol.upper()
            if key not in seen_symbols:
                seen_symbols.add(key)
                deduplicated.append(r.to_dict())

        # 4. Sort: exact symbol matches first, then by name relevance
        query_upper = query.upper()
        def sort_key(item: dict) -> tuple:
            symbol_exact = 0 if item["symbol"].upper() == query_upper else 1
            symbol_starts = 0 if item["symbol"].upper().startswith(query_upper) else 1
            name_starts = 0 if item["name"].upper().startswith(query_upper) else 1
            return (symbol_exact, symbol_starts, name_starts, item["name"])

        deduplicated.sort(key=sort_key)

        # 5. Limit results
        final = deduplicated[:limit]

        # Cache
        self._set_cached(cache_key, final)

        return final

    def _search_yahoo(self, query: str) -> List[SearchResult]:
        """Search Yahoo Finance autocomplete API for stocks, ETFs, and funds"""
        results = []
        try:
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            params = {
                "q": query,
                "quotesCount": 12,
                "newsCount": 0,
                "listsCount": 0,
                "enableFuzzyQuery": True,
                "quotesQueryId": "tss_match_phrase_query",
            }

            response = self.session.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quotes", [])

                for quote in quotes:
                    symbol = quote.get("symbol", "")
                    name = quote.get("shortname") or quote.get("longname") or quote.get("name", "")
                    quote_type = quote.get("quoteType", "")
                    exchange = quote.get("exchDisp") or quote.get("exchange", "")
                    currency = quote.get("currency", "USD") if quote.get("currency") else "USD"

                    # Skip options and futures — not relevant for portfolio tracking
                    if quote_type in ("OPTION", "FUTURE"):
                        continue

                    # Map type
                    instrument_type = self._YAHOO_TYPE_MAP.get(quote_type, "stock")

                    if symbol and name:
                        results.append(SearchResult(
                            symbol=symbol,
                            name=name,
                            instrument_type=instrument_type,
                            exchange=exchange,
                            currency=currency,
                        ))
            elif response.status_code == 429:
                logger.warning("Yahoo Finance search rate limited (even with cookie)")
                # Force cookie refetch next time
                self._yahoo_cookie_fetched = False
            else:
                logger.warning(f"Yahoo Finance search returned {response.status_code}")

        except Exception as e:
            logger.error(f"Yahoo Finance search failed: {e}")

        return results

    def _search_crypto(self, query: str) -> List[SearchResult]:
        """
        Search for crypto tokens. First checks our known mapping (fast, no API call),
        then falls back to CoinGecko search API for unknown tokens.
        """
        results = []
        query_upper = query.upper()
        query_lower = query.lower()

        # 1. Check known crypto symbols first (instant, no API call)
        for symbol, (cg_id, name) in self._CRYPTO_SYMBOLS.items():
            if (query_upper in symbol or
                query_lower in name.lower() or
                query_lower in cg_id):
                results.append(SearchResult(
                    symbol=f"{symbol}-USD",
                    name=name,
                    instrument_type="crypto",
                    exchange="CoinGecko",
                    currency="USD",
                ))

        # 2. If we found enough from known list, skip API call
        if len(results) >= 5:
            return results

        # 3. CoinGecko search API for broader crypto coverage
        try:
            url = "https://api.coingecko.com/api/v3/search"
            params = {"query": query}
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                coins = data.get("coins", [])[:8]  # Limit CoinGecko results

                # Track symbols we already have from known list
                existing_symbols = {r.symbol for r in results}

                for coin in coins:
                    symbol = coin.get("symbol", "").upper()
                    name = coin.get("name", "")
                    yahoo_symbol = f"{symbol}-USD"

                    if yahoo_symbol not in existing_symbols and symbol and name:
                        results.append(SearchResult(
                            symbol=yahoo_symbol,
                            name=name,
                            instrument_type="crypto",
                            exchange="CoinGecko",
                            currency="USD",
                        ))
                        existing_symbols.add(yahoo_symbol)

            elif response.status_code == 429:
                logger.warning("CoinGecko search rate limited")

        except Exception as e:
            logger.warning(f"CoinGecko search failed: {e}")

        return results
