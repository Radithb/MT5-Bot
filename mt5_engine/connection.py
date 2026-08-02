import MetaTrader5 as mt5

def start_mt5():
    if not mt5.initialize():
        print('❌ Gagal terhubung ke MT5. Pastikan aplikasi MT5 terbuka.')
        return False
    print('✅ Berhasil terhubung ke MT5!')
    return True

def stop_mt5():
    mt5.shutdown()
    print('🔌 Koneksi MT5 diputus.')
