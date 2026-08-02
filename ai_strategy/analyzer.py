import pandas as pd
import numpy as np
import logging
from config.settings import EMA_FAST, EMA_SLOW, ATR_PERIOD

logger = logging.getLogger("MT5_Bot")

def compute_indicators(df):
    """
    Menghitung indikator momentum Hyper-Scalping (M1).
    Fitur: EMA_FAST, EMA_SLOW, ATR
    """
    data = df.copy()

    # Hitung Exponential Moving Average
    data['EMA_FAST'] = data['close'].ewm(span=EMA_FAST, adjust=False).mean()
    data['EMA_SLOW'] = data['close'].ewm(span=EMA_SLOW, adjust=False).mean()

    # Hitung True Range (TR) dan Average True Range (ATR)
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['ATR'] = tr.rolling(window=ATR_PERIOD).mean()

    return data
