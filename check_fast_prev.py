import yfinance as yf

def check_fast_prev():
    symbols = ['VUAG.L', 'CNX1.L', 'IITU.L', 'SGLN.L']
    print(f"Checking fast_info.previous_close for {symbols}")
    
    for sym in symbols:
        ticker = yf.Ticker(sym)
        try:
            prev = ticker.fast_info.previous_close
            last = ticker.fast_info.last_price
            currency = ticker.fast_info.currency
            print(f"{sym}: Last={last} | Prev={prev} | Cur={currency}")
        except Exception as e:
            print(f"{sym}: Error {e}")

if __name__ == "__main__":
    check_fast_prev()
