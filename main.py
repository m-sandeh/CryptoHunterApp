import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import threading
import requests
import time

def calculate_ema(prices, period):
    ema = []
    multiplier = 2 / (period + 1)
    for i, p in enumerate(prices):
        if i == 0:
            ema.append(p)
        else:
            ema.append((p - ema[-1]) * multiplier + ema[-1])
    return ema

def calculate_rsi(prices, period=14):
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(-diff if diff < 0 else 0)
    avg_gain = sum(gains[:period])/period
    avg_loss = sum(losses[:period])/period
    rs = avg_gain/avg_loss if avg_loss !=0 else 100
    return 100 - (100/(1+rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast))]
    signal_line = calculate_ema(macd_line, signal)
    return macd_line[-1], signal_line[-1]

def analyze_symbol(symbol):
    try:
        price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        price = float(requests.get(price_url).json()['price'])
        klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=200"
        data = requests.get(klines_url).json()
        closes = [float(c[4]) for c in data]
        volumes = [float(c[5]) for c in data]
        if len(closes) < 50:
            return None
        ema50 = calculate_ema(closes, 50)[-1]
        ema200 = calculate_ema(closes, 200)[-1]
        rsi = calculate_rsi(closes, 14)
        macd, macd_signal = calculate_macd(closes)
        avg_vol = sum(volumes[-20:])/20 if len(volumes)>=20 else 1
        vol_ratio = volumes[-1]/avg_vol if avg_vol>0 else 1
        score = 0
        if ema50 > ema200: score += 30
        if rsi > 55: score += 20
        if macd > macd_signal: score += 30
        if vol_ratio > 1.5: score += 20
        if score >= 70:
            signal = "BUY"
        elif score <= 30:
            signal = "SELL"
        else:
            signal = "WAIT"
        return {"symbol": symbol, "price": price, "score": score, "signal": signal, "rsi": round(rsi,2)}
    except:
        return None

def get_top_symbols():
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT"]

class CryptoApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.status = Label(text="Press SCAN", size_hint_y=0.1)
        layout.add_widget(self.status)
        btn = Button(text="SCAN MARKET", size_hint_y=0.1)
        btn.bind(on_press=self.start_scan)
        layout.add_widget(btn)
        self.scroll = ScrollView()
        self.result = Label(text="", size_hint_y=None, markup=True)
        self.result.bind(texture_size=self.result.setter('size'))
        self.scroll.add_widget(self.result)
        layout.add_widget(self.scroll)
        return layout

    def start_scan(self, instance):
        threading.Thread(target=self.do_scan).start()

    def do_scan(self):
        self.update_status("Scanning... please wait (20-30s)")
        symbols = get_top_symbols()
        results = []
        for sym in symbols:
            r = analyze_symbol(sym)
            if r: results.append(r)
        buys = [r for r in results if r["signal"] == "BUY"]
        sells = [r for r in results if r["signal"] == "SELL"]
        text = "[b]TOP SCORES[/b]\n\n[color=00FF00]BUY[/color]\n"
        for b in buys[:5]:
            text += f"{b['symbol']} Score:{b['score']} ${b['price']:.2f}\n"
        text += "\n[color=FF0000]SELL[/color]\n"
        for s in sells[:5]:
            text += f"{s['symbol']} Score:{s['score']} ${s['price']:.2f}\n"
        if not buys and not sells:
            text += "No strong signals."
        self.update_status(text)

    def update_status(self, msg):
        Clock.schedule_once(lambda dt: setattr(self.result, 'text', msg), 0)

if __name__ == '__main__':
    CryptoApp().run()