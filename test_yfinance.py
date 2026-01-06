import yfinance as yf
import logging

# Configure logging to see yfinance errors
logging.basicConfig(level=logging.INFO)

symbols = ['NVDA', 'CNX1.L', 'PLTR', 'AAPL']
print(f"Testing yfinance for: {symbols}")

for symbol in symbols:
    print(f"\n--- Fetching {symbol} ---")
    try:
        ticker = yf.Ticker(symbol)
        
        # Test 1: fast_info
        try:
            price = ticker.fast_info.last_price
            currency = ticker.fast_info.currency
            print(f"FAST_INFO: {price} {currency}")
        except Exception as e:
            print(f"FAST_INFO FAILED: {e}")
            
        # Test 2: history
        try:
            hist = ticker.history(period="5d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                print(f"HISTORY: {price}")
            else:
                print("HISTORY: Empty DataFrame")
        except Exception as e:
            print(f"HISTORY FAILED: {e}")
            
    except Exception as e:
        print(f"TICKER INIT FAILED: {e}")
