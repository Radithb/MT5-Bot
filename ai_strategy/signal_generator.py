import logging
from ai_strategy.analyzer import compute_indicators
from config.settings import EMA_FAST, EMA_SLOW

logger = logging.getLogger("MT5_Bot")

def generate_signal(symbol, current_price, price_data_df):
    """
    Menghasilkan sinyal dari Hyper-Scalping EMA Crossover + Filter Momentum.
    Mendeteksi perpotongan (crossover) antara EMA Cepat dan EMA Lambat,
    lalu mengonfirmasi bahwa candle terakhir memiliki momentum searah sinyal.
    """
    if price_data_df is None or price_data_df.empty:
        return 'WAIT', 0.0, 'N/A', 'N/A'

    # 1. Hitung Indikator
    df = compute_indicators(price_data_df)

    if len(df) < 3:
        return 'WAIT', 0.0, 'N/A', 'N/A'

    # Kita butuh tiga candle terakhir untuk crossover + konfirmasi momentum
    prev_row = df.iloc[-2]
    last_row = df.iloc[-1]
    
    if pd_isnull(last_row['EMA_FAST']) or pd_isnull(last_row['EMA_SLOW']) or pd_isnull(last_row['ATR']):
        return 'WAIT', 0.0, 'N/A', 'N/A'

    # Nilai sekarang
    ema_fast_now = last_row['EMA_FAST']
    ema_slow_now = last_row['EMA_SLOW']
    atr_val = last_row['ATR']
    
    # Nilai sebelumnya
    ema_fast_prev = prev_row['EMA_FAST']
    ema_slow_prev = prev_row['EMA_SLOW']

    signal = 'WAIT'
    
    # --- Filter Momentum: Candle harus searah dengan sinyal ---
    candle_body = last_row['close'] - last_row['open']
    is_bullish_candle = candle_body > 0  # Candle hijau (naik)
    is_bearish_candle = candle_body < 0  # Candle merah (turun)

    # Deteksi Crossover UP -> BUY (hanya jika candle hijau = momentum naik)
    if ema_fast_prev <= ema_slow_prev and ema_fast_now > ema_slow_now:
        if is_bullish_candle:
            signal = 'BUY'
        
    # Deteksi Crossover DOWN -> SELL (hanya jika candle merah = momentum turun)
    elif ema_fast_prev >= ema_slow_prev and ema_fast_now < ema_slow_now:
        if is_bearish_candle:
            signal = 'SELL'

    return signal, atr_val, ema_fast_now, ema_slow_now

# Helper untuk handle pd.isna
def pd_isnull(val):
    import pandas as pd
    return pd.isna(val)
