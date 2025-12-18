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

    def fetch_portfolio(self) -> List[Dict]:
        """Fetch all open positions from Trading212 using Basic Auth"""
        import base64
        
        if not self.api_key_id or not self.api_secret_key:
            raise ValueError("Both API Key ID and Secret Key are required for Basic Auth")

        # Create Basic Auth header: Basic base64(key_id:secret_key)
        credentials = f"{self.api_key_id}:{self.api_secret_key}"
        encoded_creds = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        auth_header = f"Basic {encoded_creds}"

        last_exception = None

        for url_base in self.urls:
            endpoint = f"{url_base}/equity/portfolio"
            
            try:
                headers = {**self.base_headers, "Authorization": auth_header}
                
                logging.info(f"Attempting Basic Auth connection to {url_base}...")
                response = requests.get(endpoint, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    logging.info(f"Connected to T212 via {url_base} [SUCCESS]")
                    return response.json()
                elif response.status_code == 429:
                    logging.error(f"Rate Limit Hit: {response.text}")
                    raise ValueError("Rate limit exceeded. Try again later.")
                else:
                    logging.warning(f"Failed Basic Auth attempt ({url_base}) -> Status={response.status_code} Body={response.text}")
                    
            except Exception as e:
                last_exception = e
                logging.warning(f"Connection error ({url_base}): {e}")

        # If we get here, nothing worked
        msg = f"Failed to connect to Trading212 (Status 401/403). Please verify your API Key ID and Secret Key are correct."
        if last_exception:
            msg += f" (Error: {str(last_exception)})"
        logging.error(msg)
        raise ValueError(msg)

    def fetch_all_orders(self) -> List[Dict]:
         """
         Fetch orders to potentially calculate realized P/L or cost basis more accurately if needed.
         (Not strictly required if utilizing the portfolio 'averagePrice' field).
         """
         pass # Placeholder for future expansion
