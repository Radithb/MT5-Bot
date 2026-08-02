import os

# 1. Daftar folder yang akan dibuat
folders = [
    "config",
    "mt5_engine",
    "ai_strategy",
    "data/raw_data",
    "logs"
]

# 2. Daftar file beserta isi kodenya
files = {
    "requirements.txt": "MetaTrader5\npandas\npython-dotenv\n",
    ".env": "# Simpan kredensial MT5 Anda di sini jika diperlukan nanti\nMT5_LOGIN=\nMT5_PASSWORD=\nMT5_SERVER=\n",
    "config/__init__.py": "",
    "config/settings.py": "# Pengaturan utama bot\nSYMBOL = 'EURUSD'\nTIMEFRAME = 'M15'\nLOT_SIZE = 0.1\n",
    "mt5_engine/__init__.py": "",
    "mt5_engine/connection.py": "import MetaTrader5 as mt5\n\ndef start_mt5():\n    if not mt5.initialize():\n        print('❌ Gagal terhubung ke MT5. Pastikan aplikasi MT5 terbuka.')\n        return False\n    print('✅ Berhasil terhubung ke MT5!')\n    return True\n\ndef stop_mt5():\n    mt5.shutdown()\n    print('🔌 Koneksi MT5 diputus.')\n",
    "mt5_engine/market_data.py": "# Modul untuk mengambil data harga dari MT5\n",
    "mt5_engine/execution.py": "# Modul untuk mengirim order Buy/Sell ke MT5\n",
    "ai_strategy/__init__.py": "",
    "ai_strategy/analyzer.py": "# Modul AI untuk menganalisis data pasar\n",
    "ai_strategy/signal_generator.py": "# Modul untuk menghasilkan keputusan (BUY/SELL/WAIT)\n",
    "main.py": "from mt5_engine.connection import start_mt5, stop_mt5\n\ndef main():\n    print('Memulai AI Trading Bot...')\n    if start_mt5():\n        # Nanti logika utama bot akan berjalan di sini\n        print('Bot siap beraksi!')\n        \n        # Putus koneksi saat selesai\n        stop_mt5()\n\nif __name__ == '__main__':\n    main()\n",
}

# 3. Eksekusi pembuatan folder
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"📁 Folder dibuat: {folder}/")

# 4. Eksekusi pembuatan file (SUDAH DITAMBAHKAN ENCODING UTF-8)
for filepath, content in files.items():
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📄 File dibuat: {filepath}")

print("\n🎉 SETUP SELESAI! Struktur proyek sudah siap digunakan.")