import pandas as pd
import numpy as np
import logging
from config.settings import EMA_200, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL, ATR_PERIOD

logger = logging.getLogger("MT5_Bot")

def compute_indicators(df):
    """
    Menghitung indikator pintar untuk Day-Trading (M15 / H1).
    Fitur: EMA_200 (Trend Raksasa), RSI (Kelelahan Pasar), MACD (Momentum Ledakan), ATR.
    """
    data = df.copy()

    # 1. EMA 200 (Trend Besar)
    data['EMA_200'] = data['close'].ewm(span=EMA_200, adjust=False).mean()

    # 2. RSI (Relative Strength Index)
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # 3. MACD
    ema_fast = data['close'].ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = data['close'].ewm(span=MACD_SLOW, adjust=False).mean()
    data['MACD_LINE'] = ema_fast - ema_slow
    data['MACD_SIGNAL'] = data['MACD_LINE'].ewm(span=MACD_SIGNAL, adjust=False).mean()
    data['MACD_HISTOGRAM'] = data['MACD_LINE'] - data['MACD_SIGNAL']

    # Hitung True Range (TR) dan Average True Range (ATR)
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['ATR'] = tr.rolling(window=ATR_PERIOD).mean()

    # Hitung Support & Resistance Terdekat (Swing Low/High 20 Candle Terakhir)
    data['RESISTANCE'] = data['high'].rolling(window=20).max().shift(1)
    data['SUPPORT'] = data['low'].rolling(window=20).min().shift(1)

    return data
