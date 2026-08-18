import os
import logging
import time
import threading

import requests
import telebot
from telebot import types
from telebot import apihelper
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60

TOKEN = "YOUR_BOT_TOKEN_HERE"

bot = telebot.TeleBot(TOKEN)


class MarketMonitor:
    def __init__(self, chat_id=None):
        self.chat_id = chat_id
        self.last_prices = {}
        self.running = False
        self.thread = None

    def set_chat_id(self, chat_id):
        """Sets the chat ID for notifications"""

        self.chat_id = chat_id
        logging.info(f"The Chat ID is set: {chat_id}")

    def get_current_prices(self):
        """Gets the current prices for all coins."""

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "SHIBUSDT", "PEPEUSDT"]
        prices = {}

        for symbol in symbols:
            try:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                response = requests.get(url)
                data = response.json()
                prices[symbol] = float(data["price"])

                print(
                    f"I managed to find: {symbol}, his price list is now -> {data["price"]}."
                )
            except Exception as e:
                logging.error(f" {symbol}: {e}")
                prices[symbol] = None

        return prices

    def check_market_prices(self):
        """Checks price changes and sends notifications."""

        if self.chat_id is None:
            return

        current_prices = self.get_current_prices()

        for symbol, current_price in current_prices.items():
            if current_price is None:
                continue

            save_price_to_history(symbol, current_price)

            if symbol not in self.last_prices:
                self.last_prices[symbol] = current_price
                print(
                    f"The symbol {symbol} was not found in last_prices, added it, quantity - {current_price}"
                )
                continue

            old_price = self.last_prices[symbol]

            change_procent = ((current_price - old_price) / old_price) * 100

            if abs(change_procent) >= 0.1:
                if symbol in ["DOGEUSDT", "SHIBUSDT"]:
                    price_str = f"${current_price:.4f}"
                    old_price_str = f"${old_price:.4f}"
                else:
                    price_str = f"${current_price:,.2f}"
                    old_price_str = f"${old_price:,.2f}"

                if change_procent > 0:
                    emoji = "🚀"
                    direction = "UP"
                else:
                    emoji = "📉"
                    direction = "DOWN"

                message = (
                    f"{emoji} *SIGNAL! {symbol}*\n\n"
                    f"💰 Pricec: {price_str}\n"
                    f"📊 Changes: {change_procent:+.2f}%\n"
                    f"🔄 Movement: {direction}\n"
                    f"📉 There was: {old_price_str}\n"
                    f"📈 It became: {price_str}\n\n"
                    f"_Market monitoring is active_"
                )

                try:
                    bot.send_message(self.chat_id, message)
                    logging.info(
                        f"A notification has been sent about {symbol} ({change_procent:+.2f})"
                    )
                except Exception as e:
                    logging.error(f"Error sending notification: {e}")

                self.last_prices[symbol] = current_price

    def start_monitoring(self):
        """Starts monitoring in the background thread."""

        if self.running:
            logging.info("⚠️ Monitoring has already been started")
            return
        self.running = True

        def monitor_looping():
            logging.info(
                "Market monitoring has been started (checking every 5 minutes)."
            )
            while self.running:
                try:
                    self.check_market_prices()
                except Exception as e:
                    logging.error(f"Error in monitoring: {e}")
                time.sleep(300)

        self.thread = threading.Thread(target=monitor_looping, daemon=True)
        self.thread.start()

    def stop_monitoring(self):
        """Stops monitoring"""

        self.running = False
        logging.info("⏹️ Market monitoring stopped")


market_monitor = MarketMonitor()


def save_price_to_history(symbol, price):
    """
    Saves the coin price with a timestamp in a CSV file
    """

    filename = "price_history.csv"

    if os.path.exists(filename):
        df = pd.read_csv(filename)
    else:
        df = pd.DataFrame(columns=["timestamp", "symbol", "price"])

    new_row = pd.DataFrame(
        {
            "timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "symbol": [symbol],
            "price": [price],
        }
    )

    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(filename, index=False)
    print(f"The price has been saved {symbol}: {price:.4f}")


def get_price_history(symbol, hours=24):
    """
    Loads the price history for the specified coin for the last N hours.
    If there is no file or it is empty, it creates a new one with the correct columns.
    Returns a DataFrame or None if there is not enough data.
    """

    filename = "price_history.csv"

    # Checking if there is a file
    if not os.path.exists(filename):
        print(f"The file: {filename} not found, creating a new one.")

        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None

    # Checking if the file is empty.
    if os.path.getsize(filename) == 0:
        print(f"The file: {filename} is empty. Writing down the headlines.")

        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None

    try:
        df = pd.read_csv(filename)

    except pd.errors.EmptyDataError:
        print(f"The file: {filename} is empty or damaged - re-creating.")

        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None
    except Exception as e:
        print(f"Unknown reading error {filename}: {e}")
        return None

    required_columns = ["timestamp", "symbol", "price"]
    if not (all in df.columns for col in required_columns):
        print(f"In the file {filename} recreate them.")
        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df_symbol = df[df["symbol"] == symbol]

    if len(df_symbol) == 0:
        print(f"There is no data on the symbol {symbol} in history.")
        return None

    cutoff = datetime.now() - pd.Timedelta(hours=hours)
    df_symbol = df_symbol[df_symbol["timestamp"] >= cutoff]

    if len(df_symbol) < 2:
        print(
            f"Insufficient data on {symbol} for the last {hours} hours (need >= 2 points)."
        )
        return None

    return df_symbol


def get_daily_stats(symbol):
    """
    Returns full coin statistics for the last 24 hours:
    - The initial price.
    - Current price.
    - Percentage change.
    - Maximum.
    - Minimum.
    - Average price
    """

    df = get_price_history(symbol, 24)
    if df is None or len(df) < 2:
        return None

    first_price = df.iloc[0]["price"]
    last_price = df.iloc[-1]["price"]
    change_percent = ((last_price - first_price) / first_price) * 100
    max_price = df["price"].max()
    min_price = df["price"].min()
    avg_price = df["price"].mean()

    if change_percent > 1.0:
        trend = "🟢 Uptrend (+)"
    elif change_percent < -1.0:
        trend = "🔴 Downtrend (-)"
    else:
        trend = "🟡 Sidewall (flat)"

    message = (
        f"📊 *Daily report {symbol}*\n\n"
        f"🔹 The first price in the period {first_price:,.2f}\n"
        f"🔸 Current price {last_price:,.2f}\n"
        f"📈 Changes {change_percent:+.2f}%\n"
        f"📊 Ang price {avg_price:,.2f}\n"
        f"📈 Maximum {max_price:,.2f}\n"
        f"📉 Minimum {min_price:,.2f}\n\n"
        f"🧠 Trend {trend}"
    )

    return message


def create_price_chart(symbol, hours=24):
    """
    Plots the price chart for the specified coin over the last N hours.
    Returns the path to the graph file.
    """

    df = get_price_history(symbol, hours)

    if df is None or len(df) < 2:
        print(f"⚠️ Not enough data for the graph {symbol}. You need at least 2 points.")
        return None

    plt.figure(figsize=(12, 6))
    plt.plot(
        df["timestamp"],
        df["price"],
        marker="o",
        linestyle="-",
        linewidth=2,
        color="#f7931a",
    )
    plt.title(f"{symbol} Price Chart (Last {hours} Hours)", fontsize=14)
    plt.xlabel("Time")
    plt.ylabel("Price (USDT)")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = f"chart_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png"
    plt.savefig(filename)
    plt.close()

    print(get_daily_stats(symbol))

    return filename


def handle_error(error_type, e):
    """Centralized error handling"""

    errors_map = {
        requests.exceptions.ConnectionError: "There is no internet connection.",
        KeyError: "Data error from the exchange.",
        requests.exceptions.Timeout: "The exchange does not respond for a long time.",
    }

    user_message = errors_map.get(error_type, "Unknown error.")

    print(f"{error_type.__name__}: {e}")
    return user_message


def get_bitcoin_status(symbol):
    """
    Gets the status of any cryptocurrency with Binance.
    Arguments:
        symbol (str): For example, 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'
    Returns:
        str: Ready message for the user
    """

    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        responce = requests.get(url)
        data = responce.json()

        current_price = float(data["lastPrice"])
        price_change_percent = float(data["priceChangePercent"])

        if price_change_percent > 3.0:
            status = "🚀 STRONG GROWTH (Bulls) - You can look closely"
        elif price_change_percent > 0.5:
            status = "📈 EASY GROWTH - Calm, possible upward movement"
        elif price_change_percent < -3.0:
            status = (
                "📉 HEAVY FALL (Bears) - It's too early to buy, wait for the bottom"
            )
        elif price_change_percent < -0.5:
            status = "📉 A SLIGHT DROP IS A Correction"
        else:
            status = "⏸️ SIDEWAYS (Flat) - We don't do anything, just watch"

        message = (
            f"📊 *Analytics {symbol}* 📊\n\n"
            f"💰 Price: `${current_price:,.4f}`\n"
            f"📊 Changes: за 24ч: `{price_change_percent:+.2f}%`\n\n"
            f"🧠 The signal: {status}\n\n"
            f"_Data from Binance. This is not a financial recommendation!_"
        )

        save_price_to_history(symbol, current_price)

        return message
    except Exception as e:
        return handle_error(type(e), e)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Hello, investor!\n"
        "I'm your crypto assistant. I am able to analyze the current bitcoin situation.\n\n"
        "Press - /status to find out what is happening on the market right now.",
    )


@bot.message_handler(commands=["help"])
def send_help(message):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_graph_btc = types.InlineKeyboardButton(
        "📈 BTC Chart", callback_data="graph_btc"
    )
    btn_graph_eth = types.InlineKeyboardButton(
        "📈 ETH Chart", callback_data="graph_eth"
    )
    btn_graph_sol = types.InlineKeyboardButton(
        "📈 SOLANA Chart", callback_data="graph_sol"
    )
    btn_graph_doge = types.InlineKeyboardButton(
        "📈 DOGE Chart", callback_data="graph_doge"
    )
    btn_graph_shib = types.InlineKeyboardButton(
        "📈 SHIB Chart", callback_data="graph_shib"
    )
    btn_graph_pepe = types.InlineKeyboardButton(
        "📈 Chart PEPE", callback_data="graph_pepe"
    )

    btn_faq = types.InlineKeyboardButton("❓ About bot", callback_data="faq")
    btn_status = types.InlineKeyboardButton("current course", callback_data="status")

    btn_btc = types.InlineKeyboardButton("₿ Bitcoin", callback_data="btc")
    btn_eth = types.InlineKeyboardButton("⟠ Ether", callback_data="eth")
    btn_sol = types.InlineKeyboardButton("◎ Solana", callback_data="sol")
    btn_doge = types.InlineKeyboardButton("🐕 Dogecoin", callback_data="doge")
    btn_shib = types.InlineKeyboardButton("🐕 Shibcoin", callback_data="shib")
    btn_pepe = types.InlineKeyboardButton("🐍 Pepecoin", callback_data="pepe")

    markup.add(
        btn_graph_btc,
        btn_graph_eth,
        btn_graph_sol,
        btn_graph_doge,
        btn_graph_shib,
        btn_graph_pepe,
    )
    markup.add(btn_faq, btn_status)
    markup.add(btn_btc, btn_eth, btn_sol, btn_doge, btn_shib, btn_pepe)

    help_text = """
 🤖 *Crypto Assistant*

 Hi, I can analyze the situation on the cryptocurrency market.

 *Available Commands:*
 • /start - Launch the bot.
 • /help - Open this menu.
 • /status - Show the Bitcoin exchange rate.

 🔄 *Automatic monitoring:*
• /start_monitor — Enable market monitoring
• /stop_monitor — Turn off monitoring
• /status_monitor — Monitoring status

 *Click on the button below to go to the required section.:*
    """
    bot.send_message(message.chat.id, help_text, reply_markup=markup)


@bot.message_handler(commands=["graph"])
def send_graph(message):
    bot.reply_to(message, "⏳ I'm charting Bitcoin over the last 24 hours...")

    chart_file = create_price_chart("BTCUSDT", 24)

    print(f"CHART FILE IS: {chart_file}")

    if chart_file:
        with open(chart_file, "rb") as f:
            bot.send_photo(message.chat.id, f, caption="📈 BTCUSDT 24-hour chart")
        os.remove(chart_file)
    else:
        bot.send_message(
            message.chat.id,
            "❌ There is not enough data to build a graph. Wait until you have a story.",
        )


@bot.message_handler(commands=["status"])
def send_status(message):
    bot.reply_to(message, "⏳ I'm looking at the stock exchange...")
    time.sleep(1)

    report = get_bitcoin_status("BTCUSDT")
    bot.send_message(message.chat.id, report)


@bot.callback_query_handler(func=lambda call: True)
def buttons_interacte(call):
    crypto_map = {
        "btc": "BTCUSDT",
        "eth": "ETHUSDT",
        "sol": "SOLUSDT",
        "doge": "DOGEUSDT",
        "shib": "SHIBUSDT",
        "pepe": "PEPEUSDT",
    }
    if call.data.startswith("graph_"):
        coin_key = call.data.replace("graph_", "")

        if coin_key in crypto_map:
            symbol = crypto_map[coin_key]

            bot.send_message(
                call.message.chat.id, f"⏳ I'm building a graph {symbol} in 24 hours..."
            )

            chart_file = create_price_chart(symbol, 24)

            if chart_file:
                with open(chart_file, "rb") as f:
                    bot.send_photo(
                        call.message.chat.id,
                        f,
                        caption=f"📈 Chart {symbol} in the last 24 hours",
                    )

                os.remove(chart_file)
            else:
                bot.send_message(
                    call.message.chat.id,
                    f"❌ Not enough data for {symbol}. The bot has just started collecting history. Make a few requests /status and try again.",
                )

            bot.answer_callback_query(call.id)
    elif call.data == "status":
        bot.send_message(call.message.chat.id, "⏳ looking at the stock exchange...")
        time.sleep(1)
        report = get_bitcoin_status("BTCUSDT")
        bot.send_message(call.message.chat.id, report)
        bot.answer_callback_query(call.id)
    elif call.data == "faq":
        bot.answer_callback_query(call.id, "Information about the bot:")
        bot.send_message(
            call.message.chat.id,
            "🤖 *О боте*\n\nThis bot is written in Python using the pyTelegramBotAPI library.\n"
            "\n\n"
            "🚀 Version: 1.0\n"
            "📅 It was created in 2026 by a Russian programmer-developer and at the same time a blogger.:\n"
            "// ATS PROFI ||",
        )
        bot.answer_callback_query(call.id)
    elif call.data in crypto_map:
        symbol = crypto_map[call.data]
        bot.send_message(call.message.chat.id, f"Analyzing {symbol}...")
        time.sleep(1)
        report = get_bitcoin_status(symbol)
        bot.send_message(call.message.chat.id, report)
        bot.answer_callback_query(call.id)


@bot.message_handler(commands="start_monitor")
def start_monitor(message):
    """Enables automatic monitoring."""
    chat_id = message.chat.id

    market_monitor.set_chat_id(chat_id)
    market_monitor.start_monitoring()

    bot.reply_to(
        message,
        "🔍 *Market monitoring is enabled!*\n\n"
        "I will keep an eye on the prices and notify you of the movements. > 1%.\n\n"
        "⚙️ Check every 5 minutes.\n"
        "🔕 To turn it off, use /stop_monitor",
    )


@bot.message_handler(commands=["stop_monitor"])
def stop_monitor(message):
    """Disables automatic monitoring"""

    market_monitor.stop_monitoring()
    bot.reply_to(
        message,
        "🔕 *Market monitoring is disabled.*\n\n"
        "To enable it again, use /start_monitor",
    )


@bot.message_handler(commands=["status_monitor"])
def status_monitor(message):
    """Shows the monitoring status"""

    if market_monitor.running:
        # Showing the latest prices
        prices = market_monitor.get_current_prices()
        status_text = "📊 *Monitoring status*\n\n"
        status_text += "🟢 *Active*\n"
        status_text += "⏱️ Check every 5 minutes\n\n"
        status_text += "*Recent prices:*\n"

        for symbol, price in prices.items():
            if price:
                if symbol in ["DOGEUSDT", "SHIBUSDT"]:
                    status_text += f"• {symbol}: ${price:.4f}\n"
                else:
                    status_text += f"• {symbol}: ${price:,.2f}\n"
            else:
                status_text += f"• {symbol}: ❌ Ошибка\n"
    else:
        status_text = "📊 *Monitoring status*\n\n"
        status_text += "🔴 *Turned off*\n"
        status_text += "To enable it, use /start_monitor"

    bot.reply_to(message, status_text)


@bot.message_handler(commands=["debug_monitor"])
def debug_monitor(message):
    """Full debugging of the monitor"""

    text = "🔍 *Debugging the monitor*\n\n"
    text += f"🟢 running = {market_monitor.running}\n"
    text += f"📌 chat_id = {market_monitor.chat_id}\n"
    text += f"📦 last_prices = {market_monitor.last_prices}\n"

    if market_monitor.thread and market_monitor.thread.is_alive():
        text += "🧵 Monitoring flow: **ALIVE**\n"
    else:
        text += "🧵 Monitoring flow: **DEAD**\n"

    bot.reply_to(message, text, parse_mode="Markdown")


def health_check():
    """Every 30 seconds it outputs 'The bot is alive' to the console."""

    while True:
        time.sleep(30)
        logging.info("💚 The bot is alive and working")


thread = threading.Thread(target=health_check, daemon=True)
thread.start()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_bot():
    while True:
        try:
            logging.info("🚀 The bot is running!")
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logging.error(f"❌ Mistake: {e}")
            logging.info("🔄 Restart after 10 seconds...")
            time.sleep(10)
            continue
        break


if __name__ == "__main__":
    run_bot()
