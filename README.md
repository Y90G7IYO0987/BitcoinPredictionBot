# 🤖 Crypto Market Monitor Bot

> A Telegram bot for tracking cryptocurrency prices, analyzing trends, and sending alerts

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📖 About

**Crypto Market Monitor Bot** is a Telegram bot that tracks cryptocurrency prices in real-time, provides market analysis, price charts, and automatic alerts for significant price movements. Built with Python using Binance API.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Price Tracking** | Real-time prices for BTC, ETH, SOL, DOGE, SHIB, PEPE |
| 📈 **Price Charts** | 24-hour price charts with matplotlib |
| 🔔 **Alerts** | Automatic notifications on price changes > 1% |
| 📉 **Daily Stats** | Daily reports with trend analysis |
| 🎛️ **Interactive UI** | Inline keyboard buttons for easy navigation |
| 🔄 **Auto-Monitoring** | Background thread checks prices every 5 minutes |
| 💾 **History Storage** | CSV-based price history tracking |

---

## 🤖 Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Interactive menu with all options |
| `/status` | Current Bitcoin price and analysis |
| `/graph` | 24-hour Bitcoin price chart |
| `/start_monitor` | Enable automatic market monitoring |
| `/stop_monitor` | Disable monitoring |
| `/status_monitor` | Show monitoring status |

---

## 🎛️ Interactive Buttons

| Button | Action |
|--------|--------|
| **📈 BTC/ETH/SOL/DOGE/SHIB/PEPE Chart** | Generate 24-hour price chart |
| **₿ Bitcoin / ⟠ Ether / ◎ Solana / 🐕 Doge / 🐕 Shib / 🐍 Pepe** | Get coin status and analysis |
| **❓ About bot** | Bot information |
| **📊 Current Rate** | Get market status |

---

## 🔔 Monitoring System

### How it works:
1. User starts monitoring with `/start_monitor`
2. Bot checks prices every 5 minutes
3. If price changes > 1%, sends alert

### Alert Example:

🚀 SIGNAL! BTCUSDT

💰 Price: $45,234.50
📊 Changes: +2.45%
🔄 Movement: UP
📉 There was: $44,150.00
📈 It became: $45,234.50

Market monitoring is active

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Language** | Python 3.10+ |
| **Bot Framework** | pyTelegramBotAPI |
| **API** | Binance API |
| **Data** | Pandas, CSV |
| **Charts** | Matplotlib |

---

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- Telegram bot token from [@BotFather](https://t.me/BotFather)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Y90G7IYO0987/CryptoMarketMonitorBot.git
   cd CryptoMarketMonitorBot
   ```
2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Configure the bot**
    ```bash
    # Replace with your token in main.py
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    ```
4. **Run the bot**
    ```bash
    python main.py
    ```
## 📝 Usage
### Basic Commands
```
/start          - Launch the bot
/help           - Open interactive menu
/status         - Show Bitcoin exchange rate
/graph          - Show Bitcoin 24-hour chart
```
### Monitoring
```
/start_monitor  - Enable market monitoring
/stop_monitor   - Disable monitoring
/status_monitor - Check monitoring status
```
### 📊 Data Storage
### **price_history.csv**
#### Stores historical price data in the following format:
```
timestamp,symbol,price
2026-08-18 10:00:00,BTCUSDT,45234.50
2026-08-18 10:05:00,BTCUSDT,45250.00
2026-08-18 10:10:00,ETHUSDT,2200.00
```
### 📁 Project Structure
```
CryptoMarketMonitorBot/
├── main.py              # Main bot application
├── price_history.csv    # Historical price data
├── requirements.txt     # Dependencies
└── README.md           # Documentation
```
## 🔜 Roadmap
#### □ Add more cryptocurrencies
#### □ Add price predictions with ML
#### □ Support for multiple users
#### □ Web dashboard
#### □ Export data to Excel
### 🤝 Contributing
- Fork the repository

- Create a feature branch (git checkout -b feature/amazing-feature)

- Commit your changes (git commit -m 'Add some amazing feature')

- Push to the branch (git push origin feature/amazing-feature)

- Open a Pull Request
## 📄 License
#### Distributed under the MIT License. See LICENSE file for details.
#### ⭐ If you found this project helpful, please give it a star on GitHub!
### Made with ❤️ for the crypto community