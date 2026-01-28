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
        
        logging.info(f"T212 Auth: API Key length={len(self.api_key_id)}, Secret length={len(self.api_secret_key)}")

        last_exception = None

        for url_base in self.urls:
            endpoint = f"{url_base}/equity/portfolio"
            
            try:
                headers = {**self.base_headers, "Authorization": auth_header}
                
                logging.info(f"T212: Attempting connection to {url_base}...")
                response = requests.get(endpoint, headers=headers, timeout=10)
                
                logging.info(f"T212: Response status={response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"T212: SUCCESS! Received {len(data)} positions")
                    return data
                elif response.status_code == 429:
                    logging.error(f"T212: Rate Limit Hit: {response.text}")
                    raise ValueError("Rate limit exceeded. Try again later.")
                elif response.status_code == 401:
                    logging.error(f"T212: UNAUTHORIZED (401) - Check API Key and Secret")
                    logging.error(f"T212: Response body: {response.text}")
                elif response.status_code == 403:
                    logging.error(f"T212: FORBIDDEN (403) - Check API permissions (Portfolio must be enabled)")
                    logging.error(f"T212: Response body: {response.text}")
                else:
                    logging.warning(f"T212: Failed ({url_base}) -> Status={response.status_code} Body={response.text}")
                    
            except requests.exceptions.Timeout:
                logging.error(f"T212: Connection timeout to {url_base}")
                last_exception = Exception("Connection timeout")
            except requests.exceptions.ConnectionError as e:
                logging.error(f"T212: Connection error to {url_base}: {e}")
                last_exception = e
            except Exception as e:
                last_exception = e
                logging.warning(f"T212: Error ({url_base}): {e}")

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
