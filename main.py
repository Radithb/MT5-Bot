import time
import logging
import os
from mt5_engine.connection import start_mt5, stop_mt5
from mt5_engine.market_data import get_current_price, get_historical_rates
from mt5_engine.execution import execute_order
from ai_strategy.signal_generator import generate_signal
from config.settings import SYMBOL, LOT_SIZE, TIMEFRAME, EMA_FAST, EMA_SLOW

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MT5_Bot")

def main():
    logger.info('Memulai AI Trading Bot...')
    if not start_mt5():
        return

    logger.info('Bot siap beraksi!')

    # ====================================================================
    # FASE LIVE: Mulai pemantauan harga real-time & Scalping per-siklus
    # ====================================================================
    logger.info(f'Memantau pergerakan harga untuk {SYMBOL} (Tekan Ctrl+C untuk berhenti)...\n')
    
    wait_start_time = time.time()
    
    try:
        while True:
            # 1. Ambil harga real-time (Bid/Ask)
            price = get_current_price(SYMBOL)
            
            if price:
                # 2. Ambil data OHLCV terbaru (Hyper-Scalping M1)
                df_latest = get_historical_rates(SYMBOL, TIMEFRAME, num_bars=50)

                # 3. Hasilkan sinyal dari Algoritma Hyper-Scalping
                signal, atr_val, ema_fast, ema_slow = generate_signal(SYMBOL, price, df_latest)
                
                # 3.5 Tampilkan Status Live
                if ema_fast != 'N/A' and ema_slow != 'N/A':
                    elapsed = int(time.time() - wait_start_time)
                    mins, secs = divmod(elapsed, 60)
                    time_str = f"{mins:02d}m:{secs:02d}s"
                    print(f"\r[LIVE] {SYMBOL} | EMA{EMA_FAST}: {ema_fast:.2f} | EMA{EMA_SLOW}: {ema_slow:.2f} | Status: {signal} (Wait: {time_str})       ", end="", flush=True)

                # 4. Eksekusi Order jika sinyal bukan WAIT
                if signal in ['BUY', 'SELL']:
                    exec_price = price['ask'] if signal == 'BUY' else price['bid']
                    execute_order(SYMBOL, LOT_SIZE, signal, exec_price, atr_value=atr_val)
                    
                    # Reset waktu tunggu setelah order
                    wait_start_time = time.time()
                    # Beri jeda singkat setelah eksekusi
                    time.sleep(2)
            
            # Jeda setiap siklus pemantauan (1 detik = sangat responsif)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n")
        logger.info("Menerima perintah penghentian manual (Ctrl+C).")
    finally:
        logger.info("Menyelesaikan tugas dan menutup program.")
        stop_mt5()

if __name__ == '__main__':
    main()
