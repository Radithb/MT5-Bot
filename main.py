import time
import logging
import os
import MetaTrader5 as mt5
from mt5_engine.connection import start_mt5, stop_mt5
from mt5_engine.market_data import get_current_price, get_historical_rates
from mt5_engine.execution import execute_order, check_closed_positions, check_flash_close
from ai_strategy.signal_generator import generate_signal
import config.settings as settings
from config.settings import SYMBOL, LOT_SIZE, TIMEFRAME

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
    print("="*60)
    print("🤖 DAY-TRADING MASTER STRATEGY (M15)")
    print("1. Opsi A: RSI Mean-Reversion (Beli saat oversold)")
    print("2. Opsi B: MACD + EMA 200 (Ikuti tren raksasa)")
    print("3. Opsi C: GABUNGAN KEDUANYA (Sangat Direkomendasikan)")
    print("="*60)
    
    while True:
        try:
            pilihan = input("Masukkan pilihan Anda (1 / 2 / 3): ").strip()
            if pilihan in ['1', '2', '3']:
                settings.ALGO_MODE = int(pilihan)
                mode_str = "RSI" if pilihan == '1' else "MACD" if pilihan == '2' else "Kombinasi RSI + MACD"
                print(f"✅ Anda memilih Mode {pilihan} ({mode_str}). Memulai sistem...\n")
                break
            else:
                print("❌ Pilihan tidak valid. Ketik 1, 2, atau 3.")
        except KeyboardInterrupt:
            print("\nDibatalkan.")
            return

    logger.info('Memulai AI Trading Bot...')
    if not start_mt5():
        return

    logger.info('Bot siap beraksi!')

    # ====================================================================
    # FASE LIVE: Mulai pemantauan harga real-time & Scalping per-siklus
    # ====================================================================
    logger.info(f"Memantau pergerakan harga untuk {SYMBOL} (Tekan Ctrl+C untuk berhenti)...")
    logger.info("="*50)
    
    wait_start_time = time.time()
    last_trade_time = 0  # Tambahkan sistem cooldown
    
    try:
        while True:
            # 1. Tarik harga saat ini (bid/ask)
            price = get_current_price(SYMBOL)
            if not price:
                time.sleep(1)
                continue
            
            # 1.5 Cek target Flash Close
            check_flash_close(SYMBOL)
            
            # 2. Ambil data OHLCV
            df_latest = get_historical_rates(SYMBOL, TIMEFRAME, num_bars=300) # Butuh banyak untuk EMA 200
            
            if df_latest is not None:

                # 3. Hasilkan sinyal dari Algoritma
                signal, atr_val, val1, val2 = generate_signal(SYMBOL, price, df_latest)
                
                # Cek Cooldown (Day-trading butuh jeda panjang, kita buat 15 menit)
                current_time = time.time()
                cooldown_limit = 900 # 15 menit dalam detik
                
                if current_time - last_trade_time < cooldown_limit:
                    signal = 'WAIT'  # Paksa ngerem jika masih dalam masa cooldown
                
                # 3.5 Tampilkan Status Live beserta PnL Terbuka
                if val1 != 'N/A' and val2 != 'N/A':
                    elapsed = int(time.time() - wait_start_time)
                    mins, secs = divmod(elapsed, 60)
                    time_str = f"{mins:02d}:{secs:02d}"
                    
                    # Hitung floating PnL
                    positions = mt5.positions_get(symbol=SYMBOL)
                    if positions:
                        total_pnl = sum(p.profit for p in positions)
                        pnl_str = f" | PnL: {total_pnl:+.2f}"
                    else:
                        pnl_str = ""
                        
                    # Format teks SUPER RINGKAS agar aman di layar Windows sekecil apapun
                    out_str = f"[LIVE] RSI:{val1:.1f} | MACD:{val2:.1f} | {signal} ({time_str}){pnl_str}"
                    # Tambah spasi penimpa di akhir
                    print(f"\r{out_str}          ", end="", flush=True)

                # 4. Eksekusi Order jika sinyal bukan WAIT
                if signal in ['BUY', 'SELL']:
                    print() # Turun 1 baris agar log eksekusi tidak menimpa baris [LIVE]
                    exec_price = price['ask'] if signal == 'BUY' else price['bid']
                    execute_order(SYMBOL, LOT_SIZE, signal, exec_price, atr_value=atr_val)
                    
                    # Reset timer cooldown & wait time
                    last_trade_time = time.time()
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
