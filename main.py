from mt5_engine.connection import start_mt5, stop_mt5

def main():
    print('Memulai AI Trading Bot...')
    if start_mt5():
        # Nanti logika utama bot akan berjalan di sini
        print('Bot siap beraksi!')
        
        # Putus koneksi saat selesai
        stop_mt5()

if __name__ == '__main__':
    main()
