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

TOKEN = "_"

bot = telebot.TeleBot(TOKEN)


class MarketMonitor:
    def __init__(self, chat_id=None):
        self.chat_id = chat_id
        self.last_prices = {}
        self.running = False
        self.thread = None

    def set_chat_id(self, chat_id):
        """Устанавливает ID чата для уведомлений"""
        self.chat_id = chat_id
        logging.info(f"Chat ID установлен: {chat_id}")

    def get_current_prices(self):
        """Получает текущие цены для всех монет."""

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "SHIBUSDT", "PEPEUSDT"]
        prices = {}

        for symbol in symbols:
            try:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                response = requests.get(url)
                data = response.json()
                prices[symbol] = float(data["price"])

                print(
                    f"Получилось отыскать: {symbol}, его прайс сейчас -> {data["price"]}."
                )
            except Exception as e:
                logging.error(f"Ошибка получения цены {symbol}: {e}")
                prices[symbol] = None

        return prices

    def check_market_prices(self):
        """Проверяет изменения цен и отправляет уведомления."""

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
                    f"Символа {symbol} не было найдено в last_prices, добавили его, к-в - {current_price}"
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
                    direction = "ВВЕРХ"
                else:
                    emoji = "📉"
                    direction = "ВНИЗ"

                message = (
                    f"{emoji} *СИГНАЛ! {symbol}*\n\n"
                    f"💰 Цена: {price_str}\n"
                    f"📊 Изменение: {change_procent:+.2f}%\n"
                    f"🔄 Движение: {direction}\n"
                    f"📉 Было: {old_price_str}\n"
                    f"📈 Стало: {price_str}\n\n"
                    f"_Мониторинг рынка активен_"
                )

                try:
                    bot.send_message(self.chat_id, message)
                    logging.info(
                        f"Отправлено уведомление о {symbol} ({change_procent:+.2f})"
                    )
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления: {e}")

                self.last_prices[symbol] = current_price

    def start_monitoring(self):
        """Запускает мониторинг в фоновом потоке."""

        if self.running:
            logging.info("⚠️ Мониторинг уже запущен")
            return
        self.running = True

        def monitor_looping():
            logging.info("Мониторинг рынка запущен (проверка каждые 5 минут).")
            while self.running:
                try:
                    self.check_market_prices()
                except Exception as e:
                    logging.error(f"Ошибка в мониторинге: {e}")
                time.sleep(300)

        self.thread = threading.Thread(target=monitor_looping, daemon=True)
        self.thread.start()

    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.running = False
        logging.info("⏹️ Мониторинг рынка остановлен")


market_monitor = MarketMonitor()


def save_price_to_history(symbol, price):
    """
    Сораняет цену монеты с временной меткой в CSV файл
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
    print(f"Сохранена цена {symbol}: {price:.4f}")


def get_price_history(symbol, hours=24):
    """
    Загружает историю цен для указанной монеты за последние N часов.
    Если файла нет, или он пустой - создает новый, с правильными колонками.
    Возвращает DataFrame или None - если данных недостаточно.
    """

    filename = "price_history.csv"

    # Проверка - есть ли файл
    if not os.path.exists(filename):
        print(f"Файл: {filename} не найден - создаю новый.")

        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None

    # Проверка - не пустой ли файл.
    if os.path.getsize(filename) == 0:
        print(f"Файл: {filename} пустой. Записываю заголовки.")

        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None

    try:
        df = pd.read_csv(filename)

    except pd.errors.EmptyDataError:
        print(f"Файл {filename} пуст или поврежден - пересоздаю.")

        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None
    except Exception as e:
        print(f"Неизвестная ошибка при чтении {filename}: {e}")
        return None

    required_columns = ["timestamp", "symbol", "price"]
    if not (all in df.columns for col in required_columns):
        print(f"В файле {filename} нет нужных заголовков - пересоздаю.")
        empty_df = pd.DataFrame(columns=["timestamp", "symbol", "price"])
        empty_df.to_csv(filename, index=False)
        return None

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df_symbol = df[df["symbol"] == symbol]

    if len(df_symbol) == 0:
        print(f"Нет данных по символу {symbol} в истории.")
        return None

    cutoff = datetime.now() - pd.Timedelta(hours=hours)
    df_symbol = df_symbol[df_symbol["timestamp"] >= cutoff]

    if len(df_symbol) < 2:
        print(
            f"Неддостаточно данных по {symbol} за последние {hours} часов (нужно >= 2 точек)."
        )
        return None

    return df_symbol


def get_daily_stats(symbol):
    """
    Возвращает полную статистику по монете за последние 24 часа:
    - Начальная цена.
    - Текущая цена.
    - Изменение в процентах.
    - Максимум.
    - Минимум.
    - Средняя цена
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
        trend = "🟢 Восходящий тренд (+)"
    elif change_percent < -1.0:
        trend = "🔴 Нисходящий тренд (-)"
    else:
        trend = "🟡 Боковик (флэт)"

    message = (
        f"📊 *Ежедневный отчет {symbol}*\n\n"
        f"🔹 Первая цена в периоде {first_price:,.2f}\n"
        f"🔸 Текущая цена {last_price:,.2f}\n"
        f"📈 Изменение {change_percent:+.2f}%\n"
        f"📊 Средняя цена {avg_price:,.2f}\n"
        f"📈 Максимум {max_price:,.2f}\n"
        f"📉 Минимум {min_price:,.2f}\n\n"
        f"🧠 Тренд {trend}"
    )

    return message


def create_price_chart(symbol, hours=24):
    """
    Строит график цены для указанной монеты за последние N часов.
    Возвращает путь к файлу с графиком.
    """

    df = get_price_history(symbol, hours)

    if df is None or len(df) < 2:
        print(f"⚠️ Недостаточно данных для графика {symbol}. Нужно минимум 2 точки.")
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
    """Централизированная обработка ошибок"""
    errors_map = {
        requests.exceptions.ConnectionError: "Нет соединения с интернетом.",
        KeyError: "Ошибка данных от биржи.",
        requests.exceptions.Timeout: "Биржа долго не отвечает.",
    }

    user_message = errors_map.get(error_type, "Неизвестная ошибка.")

    print(f"{error_type.__name__}: {e}")
    return user_message


def get_bitcoin_status(symbol):
    """
    Получает статус любой криптовалюты с Binance.
    Аргументы:
        symbol (str): Например, 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'
    Возвращает:
        str: Готовое сообщение для пользователя
    """
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        responce = requests.get(url)
        data = responce.json()

        current_price = float(data["lastPrice"])
        price_change_percent = float(data["priceChangePercent"])

        if price_change_percent > 3.0:
            status = "🚀 СИЛЬНЫЙ РОСТ (Быки) - Можно присматриваться"
        elif price_change_percent > 0.5:
            status = "📈 ЛЕГКИЙ РОСТ - Спокойно, возможно движение вверх"
        elif price_change_percent < -3.0:
            status = "📉 СИЛЬНОЕ ПАДЕНИЕ (Медведи) - Покупать рано, жди дна"
        elif price_change_percent < -0.5:
            status = "📉 НЕБОЛЬШОЕ ПАДЕНИЕ - Коррекция"
        else:
            status = "⏸️ БОКОВИК (Флэт) - Ничего не делаем, просто наблюдаем"

        message = (
            f"📊 *Аналитика {symbol}* 📊\n\n"
            f"💰 Цена: `${current_price:,.4f}`\n"
            f"📊 Изменение за 24ч: `{price_change_percent:+.2f}%`\n\n"
            f"🧠 Сигнал: {status}\n\n"
            f"_Данные с Binance. Это не финансовая рекомендация!_"
        )

        save_price_to_history(symbol, current_price)

        return message
    except Exception as e:
        return handle_error(type(e), e)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привет, инвестор!\n"
        "Я твой крипто-ассистент. Я умею анализировать текущую ситуацию по биткоину.\n\n"
        "Нажми - /status, чтобы узнать, что сейчас происходит на рынке.",
    )


@bot.message_handler(commands=["help"])
def send_help(message):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_graph_btc = types.InlineKeyboardButton(
        "📈 График BTC", callback_data="graph_btc"
    )
    btn_graph_eth = types.InlineKeyboardButton(
        "📈 График ETH", callback_data="graph_eth"
    )
    btn_graph_sol = types.InlineKeyboardButton(
        "📈 График SOLANA", callback_data="graph_sol"
    )
    btn_graph_doge = types.InlineKeyboardButton(
        "📈 График DOGE", callback_data="graph_doge"
    )
    btn_graph_shib = types.InlineKeyboardButton(
        "📈 График SHIB", callback_data="graph_shib"
    )
    btn_graph_pepe = types.InlineKeyboardButton(
        "📈 График PEPE", callback_data="graph_pepe"
    )

    btn_faq = types.InlineKeyboardButton("❓ О боте", callback_data="faq")
    btn_status = types.InlineKeyboardButton("Текущий курс", callback_data="status")

    btn_btc = types.InlineKeyboardButton("₿ Биткоин", callback_data="btc")
    btn_eth = types.InlineKeyboardButton("⟠ Эфир", callback_data="eth")
    btn_sol = types.InlineKeyboardButton("◎ Солана", callback_data="sol")
    btn_doge = types.InlineKeyboardButton("🐕 Догекоин", callback_data="doge")
    btn_shib = types.InlineKeyboardButton("🐕 Шибкоин", callback_data="shib")
    btn_pepe = types.InlineKeyboardButton("🐍 Пепекоин", callback_data="pepe")

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
 🤖 *Крипто-Ассистент*

 Привет я умею анализировать ситуацию на рынке криптовалют.

 *Доступные Команды:*
 • /start - Запустить бота.
 • /help - Открыть данное меню.
 • /status - Показать курс Биткоина.

 🔄 *Автоматический мониторинг:*
• /start_monitor — Включить мониторинг рынка
• /stop_monitor — Выключить мониторинг
• /status_monitor — Статус мониторинга

 *Нажми на кнопку ниже чтобы перейти к необходимому разделу:*
    """
    bot.send_message(message.chat.id, help_text, reply_markup=markup)


@bot.message_handler(commands=["graph"])
def send_graph(message):
    bot.reply_to(message, "⏳ Строю график Биткоина за последние 24 часа...")

    chart_file = create_price_chart("BTCUSDT", 24)

    print(f"CHART FILE IS: {chart_file}")

    if chart_file:
        with open(chart_file, "rb") as f:
            bot.send_photo(message.chat.id, f, caption="📈 График BTCUSDT за 24 часа")
        os.remove(chart_file)
    else:
        bot.send_message(
            message.chat.id,
            "❌ Недостаточно данных для построения графика. Подождите, пока наберется история.",
        )


@bot.message_handler(commands=["status"])
def send_status(message):
    bot.reply_to(message, "⏳ Смотрю на биржу...")
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
                call.message.chat.id, f"⏳ Строю график {symbol} за 24 часа..."
            )

            chart_file = create_price_chart(symbol, 24)

            if chart_file:
                with open(chart_file, "rb") as f:
                    bot.send_photo(
                        call.message.chat.id,
                        f,
                        caption=f"📈 График {symbol} за последние 24 часа",
                    )

                os.remove(chart_file)
            else:
                bot.send_message(
                    call.message.chat.id,
                    f"❌ Недостаточно данных для {symbol}. Бот только начал собирать историю. Сделайте несколько запросов /status и попробуйте снова.",
                )

            bot.answer_callback_query(call.id)
    elif call.data == "status":
        bot.send_message(call.message.chat.id, "⏳ Смотрю на биржу...")
        time.sleep(1)
        report = get_bitcoin_status("BTCUSDT")
        bot.send_message(call.message.chat.id, report)
        bot.answer_callback_query(call.id)
    elif call.data == "faq":
        bot.answer_callback_query(call.id, "Информация о боте:")
        bot.send_message(
            call.message.chat.id,
            "🤖 *О боте*\n\nЭтот бот написан на Python с использованием библиотеки pyTelegramBotAPI.\n"
            "Данные берутся с биржи Binance.\n\n"
            "🚀 Версия: 1.0\n"
            "📅 Создан в 2026 году русским программистом-разработчиком и одновременно блогером:\n"
            "// ATS PROFI ||",
        )
        bot.answer_callback_query(call.id)
    elif call.data in crypto_map:
        symbol = crypto_map[call.data]
        bot.send_message(call.message.chat.id, f"Анализирую {symbol}...")
        time.sleep(1)
        report = get_bitcoin_status(symbol)
        bot.send_message(call.message.chat.id, report)
        bot.answer_callback_query(call.id)


@bot.message_handler(commands="start_monitor")
def start_monitor(message):
    """Включает автоматический мониооринг."""
    chat_id = message.chat.id

    market_monitor.set_chat_id(chat_id)
    market_monitor.start_monitoring()

    bot.reply_to(
        message,
        "🔍 *Мониторинг рынка включен!*\n\n"
        "Я буду следить за ценами и уведомлять вас о движениях > 1%.\n\n"
        "⚙️ Проверка каждые 5 минут.\n"
        "🔕 Чтобы выключить, используйте /stop_monitor",
    )


@bot.message_handler(commands=["stop_monitor"])
def stop_monitor(message):
    """Выключает автоматический мониторинг"""
    market_monitor.stop_monitoring()
    bot.reply_to(
        message,
        "🔕 *Мониторинг рынка выключен.*\n\n"
        "Чтобы включить снова, используйте /start_monitor",
    )


@bot.message_handler(commands=["status_monitor"])
def status_monitor(message):
    """Показывает статус мониторинга"""
    if market_monitor.running:
        # Показываем последние цены
        prices = market_monitor.get_current_prices()
        status_text = "📊 *Статус мониторинга*\n\n"
        status_text += "🟢 *Активен*\n"
        status_text += "⏱️ Проверка каждые 5 минут\n\n"
        status_text += "*Последние цены:*\n"

        for symbol, price in prices.items():
            if price:
                if symbol in ["DOGEUSDT", "SHIBUSDT"]:
                    status_text += f"• {symbol}: ${price:.4f}\n"
                else:
                    status_text += f"• {symbol}: ${price:,.2f}\n"
            else:
                status_text += f"• {symbol}: ❌ Ошибка\n"
    else:
        status_text = "📊 *Статус мониторинга*\n\n"
        status_text += "🔴 *Выключен*\n"
        status_text += "Чтобы включить, используйте /start_monitor"

    bot.reply_to(message, status_text)


@bot.message_handler(commands=["debug_monitor"])
def debug_monitor(message):
    """Полная отладка монитора"""
    text = "🔍 *Отладка монитора*\n\n"
    text += f"🟢 running = {market_monitor.running}\n"
    text += f"📌 chat_id = {market_monitor.chat_id}\n"
    text += f"📦 last_prices = {market_monitor.last_prices}\n"

    if market_monitor.thread and market_monitor.thread.is_alive():
        text += "🧵 Поток мониторинга: **ЖИВ**\n"
    else:
        text += "🧵 Поток мониторинга: **МЕРТВ**\n"

    bot.reply_to(message, text, parse_mode="Markdown")


def health_check():
    """Каждые 30 секунд выводит 'Бот жив' в консоль."""
    while True:
        time.sleep(30)
        logging.info("💚 Бот жив и работает")


thread = threading.Thread(target=health_check, daemon=True)
thread.start()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_bot():
    while True:
        try:
            logging.info("🚀 Бот запущен!")
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logging.error(f"❌ Ошибка: {e}")
            logging.info("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)
            continue
        break


if __name__ == "__main__":
    run_bot()
