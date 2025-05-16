import time
from datetime import datetime
import pandas as pd
import os
from ta.momentum import RSIIndicator
import requests

def send_telegram_message(message):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram message error: {e}")

def get_coins_with_high_change_and_recent_high():
    try:
        # Bybit base URL
        base_url = "https://api.bybit.com"

        # Step 1: Get 24-hour ticker data
        ticker_url = f"{base_url}/v5/market/tickers"
        params = {'category': 'linear'}  # USDT perpetual contracts
        response = requests.get(ticker_url, params=params, timeout=10)
        response.raise_for_status()
        ticker_data = response.json()
        tickers = ticker_data.get('result', {}).get('list', [])

        filtered_coins = []

        # Filter for USDT pairs with high 24-hour change
        for ticker in tickers:
            if not ticker['symbol'].endswith('USDT'):
                continue  # Only process USDT pairs
            try:
                change_percent = float(ticker['price24hPcnt']) * 100  # Convert to percentage
                if change_percent > 5:  # Relaxed threshold
                    symbol = ticker['symbol'].replace('USDT', '')  # e.g., BTC from BTCUSDT
                    price = float(ticker['lastPrice'])
                    high_24h = float(ticker['highPrice24h'])

                    # Step 2: Get 1-minute kline data for RSI and recent high
                    kline_url = f"{base_url}/v5/market/kline"
                    params = {
                        'category': 'linear',
                        'symbol': ticker['symbol'],
                        'interval': '1',  # 1-minute candles
                        'limit': 14  # 14 candles for RSI
                    }
                    kline_response = requests.get(kline_url, params=params, timeout=10)
                    kline_response.raise_for_status()
                    kline_data = kline_response.json()
                    klines = kline_data.get('result', {}).get('list', [])

                    if len(klines) < 14:
                        print(f"Skipping {symbol}: insufficient kline data ({len(klines)} candles)")
                        continue

                    # Extract close prices for RSI (kline format: [timestamp, open, high, low, close, volume, turnover])
                    close_prices = [float(kline[4]) for kline in klines[::-1]]  # Reverse to chronological order
                    rsi_series = RSIIndicator(pd.Series(close_prices)).rsi()
                    current_rsi = rsi_series.iloc[-1]

                    # Check if recent high (last 10 candles) is near 24-hour high
                    recent_high = max(close_prices[-10:])
                    if recent_high >= high_24h * 0.95:  # Within 5% of 24-hour high
                        filtered_coins.append({
                            'symbol': symbol,
                            'price': price,
                            'change_percent': change_percent,
                            'high_price_24h': high_24h,
                            'rsi': current_rsi
                        })

                    time.sleep(0.1)  # Respect Bybit rate limits (120 requests/10s)
            except (KeyError, ValueError) as e:
                print(f"Error processing {ticker.get('symbol', 'unknown')}: {e}")
                continue

        # Sort by 24-hour change
        filtered_coins.sort(key=lambda x: x['change_percent'], reverse=True)

        if filtered_coins:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\nCoins likely overbought (as of {current_time}):")
            print("-" * 80)
            print(f"{'Symbol':<15} {'Price':<12} {'24h Change %':<15} {'24h High':<12} {'RSI':<8}")
            print("-" * 80)

            message = (
                "📊 *Crypto Alert: Overbought Coins Detected* 📊\n"
                f"🕒 *Time*: {current_time}\n\n"
                "The following coins have high 24-hour price changes and are near their 24-hour highs, indicating potential overbought conditions (RSI included).\n\n"
                "🔍 *Coin Details*:\n"
            )

            for coin in filtered_coins:
                print(f"{coin['symbol']:<15} {coin['price']:<12.6f} {coin['change_percent']:<15.2f} {coin['high_price_24h']:<12.6f} {coin['rsi']:<8.2f}")
                message += (
                    f"• *{coin['symbol']}*\n"
                    f"  💰 Price: ${coin['price']:.6f}\n"
                    f"  📈 24h Change: {coin['change_percent']:.2f}%\n"
                    f"  🎯 24h High: ${coin['high_price_24h']:.6f}\n"
                    f"  ⚖️ RSI: {coin['rsi']:.2f}\n\n"
                )

            message += (
                "📝 *Note*: High RSI (>70) may suggest overbought conditions. Always conduct your own research before trading.\n"
            )
            send_telegram_message(message)
        else:
            print("No coins found with high change and recent high.")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    get_coins_with_high_change_and_recent_high()
