import MetaTrader5 as mt5
import logging

logger = logging.getLogger("MT5_Bot")

def start_mt5():
    if not mt5.initialize():
        logger.error('Gagal terhubung ke MT5. Pastikan aplikasi MT5 terbuka.')
        return False
    logger.info('Berhasil terhubung ke MT5!')
    return True

def stop_mt5():
    mt5.shutdown()
    logger.info('Koneksi MT5 diputus.')
