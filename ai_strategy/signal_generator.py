import logging
from ai_strategy.analyzer import compute_indicators
import config.settings as settings

logger = logging.getLogger("MT5_Bot")

def generate_signal(symbol, current_price, price_data_df):
    """
    Menghasilkan sinyal Day-Trading M15 berakurasi tinggi.
    """
    if price_data_df is None or price_data_df.empty:
        return 'WAIT', 0.0, 'N/A', 'N/A'

    df = compute_indicators(price_data_df)

    if len(df) < 3:
        return 'WAIT', 0.0, 'N/A', 'N/A'

    # Kita butuh dua candle terakhir untuk mendeteksi pergerakan (crossover)
    prev_row = df.iloc[-2]
    last_row = df.iloc[-1]
    
    if pd_isnull(last_row['RSI']) or pd_isnull(last_row['MACD_LINE']) or pd_isnull(last_row['EMA_200']):
        return 'WAIT', 0.0, 'N/A', 'N/A'

    # Nilai sekarang
    rsi_now = last_row['RSI']
    macd_hist_now = last_row['MACD_HISTOGRAM']
    ema_200_now = last_row['EMA_200']
    close_now = last_row['close']
    atr_val = last_row['ATR']
    
    # Nilai sebelumnya
    rsi_prev = prev_row['RSI']
    macd_hist_prev = prev_row['MACD_HISTOGRAM']

    signal = 'WAIT'
    
    # --- LOGIKA OPSI A: RSI Mean Reversion (Beli di Bawah, Jual di Pucuk) ---
    rsi_buy_signal = False
    rsi_sell_signal = False
    
    # Beli jika RSI baru saja keluar dari zona oversold (< 30) ke atas
    if rsi_prev < 30 and rsi_now >= 30:
        rsi_buy_signal = True
    # Jual jika RSI baru saja keluar dari zona overbought (> 70) ke bawah
    elif rsi_prev > 70 and rsi_now <= 70:
        rsi_sell_signal = True

    # --- LOGIKA OPSI B: MACD + EMA 200 (Follow the Trend) ---
    macd_buy_signal = False
    macd_sell_signal = False
    
    # Beli jika harga di atas EMA 200 (Uptrend) DAN MACD Histogram menyeberang ke positif
    if close_now > ema_200_now and macd_hist_prev <= 0 and macd_hist_now > 0:
        macd_buy_signal = True
    # Jual jika harga di bawah EMA 200 (Downtrend) DAN MACD Histogram menyeberang ke negatif
    elif close_now < ema_200_now and macd_hist_prev >= 0 and macd_hist_now < 0:
        macd_sell_signal = True

    # --- PENENTUAN SINYAL BERDASARKAN MODE ---
    if settings.ALGO_MODE == 1:
        # Hanya gunakan RSI
        if rsi_buy_signal: signal = 'BUY'
        elif rsi_sell_signal: signal = 'SELL'
    elif settings.ALGO_MODE == 2:
        # Hanya gunakan MACD
        if macd_buy_signal: signal = 'BUY'
        elif macd_sell_signal: signal = 'SELL'
    elif settings.ALGO_MODE == 3:
        # Gunakan Keduanya (Jika salah satu menyala, tembak!)
        if rsi_buy_signal or macd_buy_signal: signal = 'BUY'
        elif rsi_sell_signal or macd_sell_signal: signal = 'SELL'
    elif settings.ALGO_MODE == 4:
        # BRUTAL SCALPER (SMART PULLBACK + TREND FILTER)
        # Rahasia Win Rate Tinggi: JANGAN PERNAH MELAWAN ARUS BESAR!
        # Hanya menembak koreksi (pullback) yang searah dengan tren utama (EMA 200).
        
        # Beli: Harga di atas EMA 200 (Tren Naik), tapi sempat koreksi turun (RSI < 45), lalu mantul naik (RSI naik, Candle hijau)
        if close_now > ema_200_now and rsi_prev < 45 and close_now > prev_row['close'] and rsi_now > rsi_prev:
            signal = 'BUY'
            
        # Jual: Harga di bawah EMA 200 (Tren Turun), tapi sempat koreksi naik (RSI > 55), lalu mantul turun (RSI turun, Candle merah)
        elif close_now < ema_200_now and rsi_prev > 55 and close_now < prev_row['close'] and rsi_now < rsi_prev:
            signal = 'SELL'
            
    elif settings.ALGO_MODE == 5:
        # CRAZY LAYER SCALPER (MOMENTUM ACCELERATOR + S/R FILTER)
        # Menembak BERKALI-KALI dan menambah layer selama momentum masih membesar!
        # TAPI DIBATASI: Hanya menembak jika harga berada di sekitar Support/Resistance terdekat.
        
        macd_hist_prev = prev_row['MACD_HISTOGRAM']
        supp = df.iloc[-1]['SUPPORT']
        resis = df.iloc[-1]['RESISTANCE']
        
        # Toleransi kedekatan dengan S/R (2.0x ATR) agar masuknya benar-benar di area SnR yang solid
        near_support = (close_now - supp) <= (atr_val * 2.0)
        near_resistance = (resis - close_now) <= (atr_val * 2.0)
        
        # Beli: HANYA di area Support + Momentum arus mulai berbalik NAIK (MACD Hist menaik)
        if near_support and macd_hist_now > macd_hist_prev:
            signal = 'BUY'
            
        # Jual: HANYA di area Resistance (Pucuk) + Momentum arus mulai berbalik TURUN (MACD Hist menurun)
        elif near_resistance and macd_hist_now < macd_hist_prev:
            signal = 'SELL'

    return signal, atr_val, rsi_now, macd_hist_now

# Helper untuk handle pd.isna
def pd_isnull(val):
    import pandas as pd
    return pd.isna(val)
