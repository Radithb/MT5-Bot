import logging
from ai_strategy.analyzer import compute_indicators
from config.settings import EMA_FAST, EMA_SLOW

logger = logging.getLogger("MT5_Bot")

def generate_signal(symbol, current_price, price_data_df):
    """
    Menghasilkan sinyal dari Hyper-Scalping EMA Crossover.
    Mendeteksi perpotongan (crossover) antara EMA Cepat dan EMA Lambat.
    """
    if price_data_df is None or price_data_df.empty:
        return 'WAIT', 0.0, 'N/A', 'N/A'

    # 1. Hitung Indikator
    df = compute_indicators(price_data_df)

    if len(df) < 2:
        return 'WAIT', 0.0, 'N/A', 'N/A'

    # Kita butuh dua candle terakhir untuk mendeteksi 'crossover'
    # prev_row = candle sebelum candle terakhir yang sudah close
    # last_row = candle terbaru yang sedang berjalan / baru close
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
    
    # Deteksi Crossover UP -> BUY
    # Jika sebelumnya FAST di bawah SLOW, lalu sekarang FAST di atas SLOW
    if ema_fast_prev <= ema_slow_prev and ema_fast_now > ema_slow_now:
        signal = 'BUY'
        
    # Deteksi Crossover DOWN -> SELL
    # Jika sebelumnya FAST di atas SLOW, lalu sekarang FAST di bawah SLOW
    elif ema_fast_prev >= ema_slow_prev and ema_fast_now < ema_slow_now:
        signal = 'SELL'

    if signal != 'WAIT':
        print() # Enter agar baris live log tidak tertimpa
        logger.info(
            f"Hyper-Scalp Signal: {signal} {symbol} | "
            f"EMA{EMA_FAST}: {ema_fast_now:.2f} | EMA{EMA_SLOW}: {ema_slow_now:.2f} | ATR: {atr_val:.4f}"
        )

    return signal, atr_val, ema_fast_now, ema_slow_now

# Helper untuk handle pd.isna
def pd_isnull(val):
    import pandas as pd
    return pd.isna(val)
