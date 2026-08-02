# Konfigurasi Utama Bot
SYMBOL = 'BTCUSDm'
TIMEFRAME = 'M1'
LOT_SIZE = 0.01

# --- MANAJEMEN RISIKO MULTI-POSISI EFISIEN ---
MAX_OPEN_POSITIONS = 5              # Maksimal total posisi aktif bersamaan
CLOSE_ON_REVERSAL = True            # Otomatis tutup posisi lama jika ada sinyal pembalikan arah (misal: BUY -> SELL)
MIN_ENTRY_DISTANCE_POINTS = 50      # Semula 150. Dipersempit agar bot tidak sering menolak sinyal

# --- PENGATURAN HYPER-SCALPING (CROSSOVER) ---
EMA_FAST = 3            # Garis Cepat (Responsif terhadap pergerakan sesaat)
EMA_SLOW = 9            # Garis Lambat (Basis silang)
ATR_PERIOD = 14
SL_ATR_MULTIPLIER = 0.5            # Semula 1.5. SL sangat dekat dengan harga entry
TP_ATR_MULTIPLIER = 0.75           # Semula 2.0. TP sangat dekat, cuan kecil tapi cepat
