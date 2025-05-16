
import time
from datetime import datetime
import pandas as pd
import os
from ta.momentum import RSIIndicator
import requests  # Still needed for Telegram API

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
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'percent_change_24h_desc',
            'per_page': 100,
            'page': 1,
            'sparkline': 'true'  # to get 7d minutely data
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        tickers = response.json()

        filtered_coins = []

        for ticker in tickers:
            if ticker['price_change_percentage_24h'] is None:
                continue

            change_percent = ticker['price_change_percentage_24h']
            if change_percent > 10:
                symbol = ticker['symbol'].upper()
                price = ticker['current_price']
                high_24h = ticker['high_24h']
                sparkline = ticker.get('sparkline_in_7d', {}).get('price', [])

                # Use last 20 sparkline points to simulate RSI
                if len(sparkline) < 20:
                    continue

                close_prices = sparkline[-20:]
                rsi_series = RSIIndicator(pd.Series(close_prices)).rsi()
                current_rsi = rsi_series.iloc[-1]

                recent_high = max(close_prices[-10:])

                if recent_high >= high_24h * 0.99:
                    filtered_coins.append({
                        'symbol': symbol,
                        'price': price,
                        'change_percent': change_percent,
                        'high_price_24h': high_24h,
                        'rsi': current_rsi
                    })

                time.sleep(0.1)  # Be polite to API

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


