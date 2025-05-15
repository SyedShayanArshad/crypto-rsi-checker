import requests
import pandas as pd
from ta.momentum import RSIIndicator
import os
from datetime import datetime

def send_telegram_message(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Missing Telegram credentials")
        return

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
        print(f"Telegram error: {e}")

def run_check():
    try:
        url_ticker = "https://api.binance.com/api/v3/ticker/24hr"
        tickers = requests.get(url_ticker, timeout=10).json()

        high_change_coins = []
        for ticker in tickers:
            if ticker['symbol'].endswith('USDT'):
                change = float(ticker['priceChangePercent'])
                if change > 10:
                    high_change_coins.append({
                        'symbol': ticker['symbol'],
                        'price': float(ticker['lastPrice']),
                        'change_percent': change,
                        'high_price_24h': float(ticker['highPrice'])
                    })

        filtered = []
        for coin in high_change_coins:
            symbol = coin['symbol']
            url_kline = "https://api.binance.com/api/v3/klines"
            params = {'symbol': symbol, 'interval': '1m', 'limit': 20}
            try:
                klines = requests.get(url_kline, params=params, timeout=10).json()
            except Exception as e:
                print(f"Kline error {symbol}: {e}")
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            if len(closes) < 14:
                continue

            rsi = RSIIndicator(pd.Series(closes)).rsi().iloc[-1]
            recent_high = max(highs[-10:])
            if recent_high >= coin['high_price_24h'] * 0.99:
                coin['rsi'] = rsi
                filtered.append(coin)

        if filtered:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"📊 *Crypto Alert: Overbought Coins*\n🕒 {now}\n\n"
            for coin in filtered:
                msg += (
                    f"*{coin['symbol']}*\n"
                    f"Price: ${coin['price']:.4f}\n"
                    f"Change: {coin['change_percent']:.2f}%\n"
                    f"24h High: ${coin['high_price_24h']:.4f}\n"
                    f"RSI: {coin['rsi']:.2f}\n\n"
                )
            send_telegram_message(msg)
        else:
            print("No signals found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_check()
