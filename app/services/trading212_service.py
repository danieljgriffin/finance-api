import requests
from typing import List, Dict, Optional
import logging

class Trading212Service:
    BASE_URL = "https://live.trading212.com/api/v0"

    def __init__(self, api_key_id: str, api_secret_key: str):
        self.api_key_id = api_key_id.strip()
        self.api_secret_key = api_secret_key.strip()
        self.base_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.urls = [
            "https://live.trading212.com/api/v0",
            "https://demo.trading212.com/api/v0"
        ]

    def _auth_header(self) -> str:
        """Build the Trading 212 Basic Auth header without logging credentials."""
        import base64

        if not self.api_key_id or not self.api_secret_key:
            raise ValueError("Both API Key ID and Secret Key are required for Basic Auth")

        credentials = f"{self.api_key_id}:{self.api_secret_key}"
        encoded_creds = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded_creds}"

    def _fetch_json(self, endpoint_path: str, description: str):
        """Fetch one account-scoped Trading 212 resource from live or demo."""
        auth_header = self._auth_header()
        last_exception = None

        for url_base in self.urls:
            endpoint = f"{url_base}{endpoint_path}"
            try:
                headers = {**self.base_headers, "Authorization": auth_header}
                logging.info(f"T212: Fetching {description} from {url_base}...")
                response = requests.get(endpoint, headers=headers, timeout=10)
                logging.info(f"T212: {description} response status={response.status_code}")

                if response.status_code == 200:
                    return response.json()
                if response.status_code == 429:
                    raise ValueError("Trading 212 rate limit exceeded. Try again later.")
                if response.status_code == 401:
                    logging.error("T212: UNAUTHORIZED (401) - Check API Key and Secret")
                elif response.status_code == 403:
                    logging.error(
                        "T212: FORBIDDEN (403) - Check Account Data and Portfolio permissions"
                    )
                else:
                    logging.warning(
                        f"T212: Failed ({url_base}) -> Status={response.status_code}"
                    )
            except requests.exceptions.Timeout:
                logging.error(f"T212: Connection timeout to {url_base}")
                last_exception = Exception("Connection timeout")
            except requests.exceptions.ConnectionError as exc:
                logging.error(f"T212: Connection error to {url_base}: {exc}")
                last_exception = exc
            except ValueError:
                raise
            except Exception as exc:
                last_exception = exc
                logging.warning(f"T212: Error ({url_base}): {exc}")

        message = (
            f"Failed to fetch Trading 212 {description}. Verify the key was generated "
            "for the intended account and has Account Data and Portfolio permissions."
        )
        if last_exception:
            message += f" (Error: {last_exception})"
        raise ValueError(message)

    def fetch_portfolio(self) -> List[Dict]:
        """Fetch open positions, preferring the current API's wallet values."""
        try:
            positions = self._fetch_json("/equity/positions", "positions")
            data = []
            for position in positions:
                instrument = position.get("instrument") or {}
                wallet_impact = position.get("walletImpact") or {}
                data.append({
                    "_source": "positions",
                    "ticker": instrument.get("ticker", ""),
                    "name": instrument.get("name") or instrument.get("shortName"),
                    "quantity": position.get("quantity", 0),
                    "averagePrice": position.get("averagePricePaid", 0),
                    "currentPrice": position.get("currentPrice", 0),
                    "currency": (
                        instrument.get("currency")
                        or instrument.get("currencyCode")
                        or ""
                    ),
                    "ppl": wallet_impact.get("unrealizedProfitLoss", 0),
                    "walletImpact": wallet_impact,
                })
        except ValueError:
            # Existing ISA keys may still expose only the legacy endpoint.
            data = self._fetch_json("/equity/portfolio", "portfolio")
        logging.info(f"T212: Received {len(data)} positions")
        return data

    def fetch_account_summary(self) -> Dict:
        """Fetch account ID, total value, cash and investment totals."""
        data = self._fetch_json("/equity/account/summary", "account summary")
        if not isinstance(data, dict) or data.get("id") is None:
            raise ValueError("Trading 212 account summary did not include an account ID")
        return data

    def fetch_all_orders(self) -> List[Dict]:
         """
         Fetch orders to potentially calculate realized P/L or cost basis more accurately if needed.
         (Not strictly required if utilizing the portfolio 'averagePrice' field).
         """
         pass # Placeholder for future expansion
