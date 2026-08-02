import MetaTrader5 as mt5
import pandas as pd
import logging

logger = logging.getLogger("MT5_Bot")

# Peta konversi string timeframe ke konstanta MT5
TIMEFRAME_MAP = {
    'M1':  mt5.TIMEFRAME_M1,
    'M5':  mt5.TIMEFRAME_M5,
    'M15': mt5.TIMEFRAME_M15,
    'M30': mt5.TIMEFRAME_M30,
    'H1':  mt5.TIMEFRAME_H1,
    'H4':  mt5.TIMEFRAME_H4,
    'D1':  mt5.TIMEFRAME_D1,
}

def get_current_price(symbol):
    """
    Mengambil harga Bid dan Ask secara real-time.
    """
    # Pastikan symbol tampil di Market Watch
    if not mt5.symbol_select(symbol, True):
        logger.error(f"Gagal memilih symbol: {symbol}")
        return None
        
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Gagal mendapatkan data tick untuk: {symbol}")
        return None
        
    return {
        'bid': tick.bid,
        'ask': tick.ask
    }

def get_historical_rates(symbol, timeframe_str, num_bars=500):
    """
    Mengambil data candlestick historis (OHLCV) dari MT5.
    Mengembalikan pandas DataFrame dengan kolom: time, open, high, low, close, tick_volume.
    """
    tf = TIMEFRAME_MAP.get(timeframe_str)
    if tf is None:
        logger.error(f"Timeframe tidak dikenal: {timeframe_str}")
        return None

    if not mt5.symbol_select(symbol, True):
        logger.error(f"Gagal memilih symbol untuk data historis: {symbol}")
        return None

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)

    if rates is None or len(rates) == 0:
        logger.error(f"Gagal menarik data historis untuk {symbol} {timeframe_str}")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    logger.debug(f"Berhasil menarik {len(df)} baris data historis {symbol} ({timeframe_str})")
    return df
