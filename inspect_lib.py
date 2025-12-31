import hdwallet
import hdwallet.symbols
from hdwallet import HDWallet

print(f"Version: {hdwallet.__version__}")
print(f"Dir hdwallet: {dir(hdwallet)}")

try:
    import hdwallet.cryptocurrencies
    print(f"Dir cryptocurrencies: {dir(hdwallet.cryptocurrencies)}")
except ImportError:
    print("No hdwallet.cryptocurrencies module")

print(f"Type of symbols.BTC: {type(hdwallet.symbols.BTC)}")
print(f"Value of symbols.BTC: {hdwallet.symbols.BTC}")
