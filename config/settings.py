# Konfigurasi Utama Bot
SYMBOL = 'BTCUSDm'
TIMEFRAME = 'M1'
LOT_SIZE = 0.01

# --- MANAJEMEN RISIKO MULTI-POSISI EFISIEN ---
MAX_OPEN_POSITIONS = 3              # Maksimal total posisi aktif bersamaan
CLOSE_ON_REVERSAL = True            # Otomatis tutup posisi lama jika ada sinyal pembalikan arah (misal: BUY -> SELL)
MIN_ENTRY_DISTANCE_POINTS = 150     # Jarak minimal (points) antar posisi searah agar entry tidak menumpuk di harga yang sama

# --- PENGATURAN HYPER-SCALPING (CROSSOVER) ---
EMA_FAST = 3            # Garis Cepat (Responsif terhadap pergerakan sesaat)
EMA_SLOW = 9            # Garis Lambat (Basis silang)
ATR_PERIOD = 14
SL_ATR_MULTIPLIER = 1.5
TP_ATR_MULTIPLIER = 2.0
