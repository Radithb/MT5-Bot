# Konfigurasi Utama Bot
SYMBOL = 'BTCUSDm'
TIMEFRAME = 'M1'
LOT_SIZE = 0.05

# --- MANAJEMEN RISIKO MULTI-POSISI EFISIEN ---
MAX_OPEN_POSITIONS = 5              # Maksimal total posisi aktif bersamaan
CLOSE_ON_REVERSAL = False           # DIMATIKAN! Biarkan bot mengejar hit TP atau SL, jangan panik close posisi.
MIN_ENTRY_DISTANCE_POINTS = 50      # Semula 150. Dipersempit agar bot tidak sering menolak sinyal

# --- PENGATURAN HYPER-SCALPING (CROSSOVER) ---
EMA_FAST = 3            # Garis Cepat (Responsif terhadap pergerakan sesaat)
EMA_SLOW = 9            # Garis Lambat (Basis silang)
ATR_PERIOD = 14
SL_ATR_MULTIPLIER = 1.0            # SL lebih lebar, memberi ruang napas agar tidak mudah tersentuh
TP_ATR_MULTIPLIER = 0.3            # TP sangat sempit, cuan kecil tapi hampir pasti tercapai

