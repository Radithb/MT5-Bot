import MetaTrader5 as mt5

# --- PENGATURAN UMUM ---
SYMBOL = "BTCUSDm"
TIMEFRAME = "M15"      # NAIK LEVEL: Dari M1 (Noise) ke M15 (Trend Jelas)
LOT_SIZE = 0.05

# --- MANAJEMEN RISIKO MULTI-POSISI EFISIEN ---
MAX_OPEN_POSITIONS = 2              # Maksimal posisi bersamaan
CLOSE_ON_REVERSAL = False           
MIN_ENTRY_DISTANCE_POINTS = 500     # Diperlebar karena M15 pergerakannya jauh lebih besar

# --- PENGATURAN INDIKATOR BARU (M15 DAY-TRADING) ---
EMA_200 = 200           # Indikator Arus Utama Jangka Panjang (Trend)
RSI_PERIOD = 14         # Indikator Kejenuhan Pasar (Oversold/Overbought)
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ATR_PERIOD = 14

# Pengaman Sistem Broker (Jarang tersentuh karena ada Flash Close)
SL_ATR_MULTIPLIER = 1.0            
TP_ATR_MULTIPLIER = 2.0            

# --- MODE FLASH CLOSE (Proteksi Akun dari Spread & Volatilitas) ---
USE_FLASH_CLOSE = True             
FLASH_PROFIT_USD = 5.00            # Target cuan $5.00 per transaksi!
FLASH_LOSS_USD = -2.50             # Cut-loss di -$2.50 (Risk 1 : Reward 2)

# --- PILIHAN ALGORITMA ---
# 1 = Mode A (RSI Mean Reversion), 2 = Mode B (MACD Trend Following), 3 = Gabungan Keduanya
ALGO_MODE = 3
