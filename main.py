import time
import logging
import os
import datetime
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

# =====================================================================
# OPSI 4: MONITOR MODE (Pantau EA MQL5 tanpa trading)
# =====================================================================
MONITOR_MAGIC = 234000  # Magic Number yang sama dengan EA MQL5

def monitor_ea():
    """
    Mode Monitor: Hanya memantau aktivitas EA MQL5.
    Tidak melakukan trading apapun. Aman dijalankan bersamaan dengan EA.
    Dashboard bersih yang refresh di tempat tanpa spam.
    """
    if not start_mt5():
        return

    # State tracking
    tracked_positions = {}
    session_profit = 0.0
    session_trades = 0
    session_wins = 0
    session_losses = 0
    monitor_start = time.time()
    event_log = []  # Buffer log event (maks 8 baris terakhir)
    MAX_LOG_LINES = 8

    def add_event(text):
        """Tambah event ke buffer log."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        event_log.append(f"  [{timestamp}] {text}")
        # Buang baris lama jika melebihi batas
        while len(event_log) > MAX_LOG_LINES:
            event_log.pop(0)

    def draw_dashboard(bid, ask, pos_count, total_pnl, elapsed_str):
        """Gambar ulang seluruh layar CMD dengan bersih."""
        os.system('cls')

        # ── Header ──
        print("=" * 56)
        print("  MONITOR EA MQL5 (Read-Only)")
        print("=" * 56)
        print(f"  Symbol : {SYMBOL}")
        print(f"  Uptime : {elapsed_str}")
        print("-" * 56)

        # ── Harga ──
        print(f"  Bid: {bid:<12.2f}  Ask: {ask:<12.2f}")
        print("-" * 56)

        # ── Status Posisi ──
        if pos_count > 0:
            pnl_sign = "+" if total_pnl >= 0 else ""
            print(f"  Posisi Aktif : {pos_count}")
            print(f"  Floating PnL : {pnl_sign}${total_pnl:.2f}")
        else:
            print("  Posisi Aktif : 0 (Menunggu EA...)")
            print("  Floating PnL : $0.00")
        print("-" * 56)

        # ── Statistik Sesi ──
        winrate = (session_wins / session_trades * 100) if session_trades > 0 else 0
        sp_sign = "+" if session_profit >= 0 else ""
        print(f"  Trade: {session_trades}  |  "
              f"W: {session_wins}  L: {session_losses}  |  "
              f"WR: {winrate:.0f}%")
        print(f"  Total P/L Sesi : {sp_sign}${session_profit:.2f}")
        print("=" * 56)

        # ── Event Log ──
        if event_log:
            print("  Riwayat:")
            for line in event_log:
                print(line)
        else:
            print("  Riwayat: (belum ada aktivitas)")
        print("-" * 56)
        print("  Tekan Ctrl+C untuk berhenti.")

    try:
        while True:
            # ── 1. Ambil posisi aktif dari EA ──
            all_positions = mt5.positions_get(symbol=SYMBOL)
            current_tickets = {}

            if all_positions:
                for pos in all_positions:
                    if pos.magic == MONITOR_MAGIC:
                        current_tickets[pos.ticket] = pos

            # ── 2. Deteksi posisi BARU ──
            for ticket, pos in current_tickets.items():
                if ticket not in tracked_positions:
                    pos_type = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
                    open_time = datetime.datetime.fromtimestamp(pos.time).strftime("%H:%M:%S")
                    tracked_positions[ticket] = {
                        'type': pos_type,
                        'open_price': pos.price_open,
                        'open_time': open_time,
                        'volume': pos.volume
                    }
                    add_event(f"BUKA {pos_type} {pos.volume} lot @ {pos.price_open}")

            # ── 3. Deteksi posisi DITUTUP ──
            closed_tickets = [t for t in tracked_positions if t not in current_tickets]

            if closed_tickets:
                now = datetime.datetime.now()
                from_date = now - datetime.timedelta(days=1)
                history_deals = mt5.history_deals_get(from_date, now)

                for ticket in closed_tickets:
                    info = tracked_positions.pop(ticket)
                    session_trades += 1

                    pos_deals = [d for d in (history_deals or [])
                                 if d.position_id == ticket and d.entry in (1, 3)]

                    if pos_deals:
                        deal = pos_deals[-1]
                        pnl = deal.profit + deal.swap + deal.commission
                        close_price = deal.price
                        session_profit += pnl

                        if pnl >= 0:
                            session_wins += 1
                            icon = "+"
                        else:
                            session_losses += 1
                            icon = ""

                        add_event(
                            f"TUTUP {info['type']} | "
                            f"{info['open_price']} > {close_price} | "
                            f"{icon}${pnl:.2f}"
                        )
                    else:
                        add_event(f"TUTUP {info['type']} (Tiket: {ticket})")

            # ── 4. Hitung data dashboard ──
            elapsed = int(time.time() - monitor_start)
            hrs, remainder = divmod(elapsed, 3600)
            mins, secs = divmod(remainder, 60)
            elapsed_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

            total_pnl = 0.0
            for pos in current_tickets.values():
                total_pnl += pos.profit + pos.swap + pos.commission

            tick = mt5.symbol_info_tick(SYMBOL)
            bid = tick.bid if tick else 0.0
            ask = tick.ask if tick else 0.0

            # ── 5. Gambar dashboard ──
            draw_dashboard(bid, ask, len(current_tickets), total_pnl, elapsed_str)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n")
        print("="*60)
        print("📊 RINGKASAN SESI MONITOR")
        print("="*60)
        elapsed = int(time.time() - monitor_start)
        hrs, remainder = divmod(elapsed, 3600)
        mins, secs = divmod(remainder, 60)
        print(f"   Durasi     : {hrs:02d}:{mins:02d}:{secs:02d}")
        print(f"   Total Trade: {session_trades}")
        print(f"   Menang     : {session_wins}")
        print(f"   Kalah      : {session_losses}")
        winrate = (session_wins / session_trades * 100) if session_trades > 0 else 0
        print(f"   Winrate    : {winrate:.1f}%")
        print(f"   Total P/L  : ${session_profit:+.2f}")
        print("="*60)
    finally:
        stop_mt5()


# =====================================================================
# MENU UTAMA
# =====================================================================
def main():
    print("="*60)
    print("🤖 DAY-TRADING MASTER STRATEGY (M15)")
    print("-"*60)
    print("  [TRADING MODE - Bot Python]")
    print("  3. Opsi C: GABUNGAN RSI + MACD (Sangat Direkomendasikan - M15)")
    print("  4. Opsi D: BRUTAL SCALPER (M1 - Eksekusi Super Cepat, Resiko Tinggi)")
    print("  5. Opsi E: CRAZY LAYER (M5 - Tembak Berkali-kali, SnR Lebih Akurat)")
    print("-"*60)
    print("  [MONITOR MODE - Pantau EA MQL5]")
    print("  6. 📡 Monitor EA MQL5 (Read-Only, tanpa trading)")
    print("="*60)
    
    global TIMEFRAME
    active_timeframe = TIMEFRAME
    cooldown_seconds = 900 # 15 menit
    
    while True:
        try:
            pilihan = input("Masukkan pilihan Anda (3/4/5/6): ").strip()
            if pilihan == '3':
                settings.ALGO_MODE = 3
                mode_str = "Kombinasi RSI + MACD"
                print(f"✅ Anda memilih Mode 3 ({mode_str}). Memulai sistem...\n")
                break
            elif pilihan == '4':
                settings.ALGO_MODE = 4
                active_timeframe = "M1"
                cooldown_seconds = 5 # Cooldown super cepat, hanya 5 detik
                settings.SL_ATR_MULTIPLIER = 5.0  # Lebarkan napas SL fisik MT5 (Pengaman terakhir)
                settings.TP_ATR_MULTIPLIER = 4.0  # Lebarkan napas TP fisik MT5
                settings.FLASH_LOSS_USD = -5.00   # Cutloss di -$5.00 (toleransi slippage ke -$6.00)
                settings.FLASH_PROFIT_USD = 7.50  # TP dinaikkan ke $7.50 (RR 1 : 1.5)
                
                # Trailing Stop: Jangan terlalu pelit! Biarkan profit bernapas panjang.
                settings.USE_TRAILING_STOP = True
                settings.TRAILING_STOP_START_USD = 5.00 # Baru aktif jika cuan sudah menyentuh $5.00
                settings.TRAILING_STOP_DIST_USD = 2.00  # Beri jarak $2.00 agar tidak gampang tersentuh noise. Minimal untung $3.00!
                
                # Fitur Reversal Cepat (Putar Balik Darurat)
                settings.ALLOW_HEDGING = False          # Dilarang hedging (bikin bingung dan rugi double)
                settings.CLOSE_ON_REVERSAL = True       # Jika tren berbalik, langsung CUT posisi lama dan buka posisi baru searah arus!
                
                print("⚠️  Anda memilih BRUTAL SCALPER (Timeframe M1). Sabuk pengaman terpasang! Memulai sistem...\n")
                break
            elif pilihan == '5':
                settings.ALGO_MODE = 5
                active_timeframe = "M5"
                cooldown_seconds = 0.2 # Cooldown super gila (5x per detik)
                
                # Fitur Layer Gila!
                settings.MAX_OPEN_POSITIONS = 10         # Buka sampai 10 layer!
                settings.MIN_ENTRY_DISTANCE_POINTS = 1500  # Jarak antar layer diperlebar drastis menjadi 1500 poin ($1.5 di Gold) agar averaging stabil
                
                settings.SL_ATR_MULTIPLIER = 5.0
                settings.TP_ATR_MULTIPLIER = 4.0
                settings.FLASH_LOSS_USD = -50.00  # Jauhkan Flash Loss per layer (hanya sebagai pengaman terakhir akun)
                settings.FLASH_PROFIT_USD = 15.00 # TP juga harus besar
                
                settings.USE_TRAILING_STOP = True
                settings.TRAILING_STOP_START_USD = 10.00
                settings.TRAILING_STOP_DIST_USD = 4.00
                
                # Fitur Averaging / Basket Close
                settings.USE_BASKET_CLOSE = True
                settings.BASKET_PROFIT_USD = 4.00 # Jika total profit semua layer >= $4.00, tutup semua!
                settings.BASKET_LOSS_USD = -50.00 # Nafas keranjang diperlebar ke -$50.00 agar layer bisa bekerja menangkap pantulan
                
                # Mengizinkan Hedging (Bi-Directional)
                # Jika sedang nyangkut BUY, lalu ada sinyal SELL yg solid, bot diizinkan membuka SELL!
                settings.ALLOW_HEDGING = True
                
                # MATIKAN Close on Reversal!
                # Averaging/Layering bot tidak boleh panik cutloss saat arah berbalik sesaat. 
                # Ia harus sabar menunggu pantulan untuk menutup keranjang (Basket Close).
                settings.CLOSE_ON_REVERSAL = False
                
                print("💀  WARNING: Anda memilih CRAZY LAYER SCALPER! Mode brutal multi-posisi. Memulai sistem...\n")
                break
            elif pilihan == '6':
                monitor_ea()
                return
            else:
                print("❌ Pilihan tidak valid. Ketik 1, 2, 3, 4, atau 5.")
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
    logger.info("Bot siap beraksi! Membuka dashboard...")
    time.sleep(1)

    wait_start_time = time.time()
    last_trade_time = 0  # Tambahkan sistem cooldown

    # State tracking untuk UI
    tracked_positions = {}
    session_profit = 0.0
    session_trades = 0
    session_wins = 0
    session_losses = 0
    event_log = []
    MAX_LOG_LINES = 6

    def add_event(text):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        event_log.append(f"  [{timestamp}] {text}")
        while len(event_log) > MAX_LOG_LINES:
            event_log.pop(0)

    add_event(f"Bot Python (Mode {pilihan}) dimulai.")

    try:
        while True:
            # ── 1. Tarik harga saat ini (bid/ask) ──
            price = get_current_price(SYMBOL)
            if not price:
                time.sleep(1)
                continue

            # ── 2. Cek posisi & Deals ──
            all_positions = mt5.positions_get(symbol=SYMBOL)
            current_tickets = {}
            if all_positions:
                for pos in all_positions:
                    if pos.magic == settings.MAGIC_NUMBER:
                        current_tickets[pos.ticket] = pos

            for ticket, pos in current_tickets.items():
                if ticket not in tracked_positions:
                    pos_type = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
                    tracked_positions[ticket] = {
                        'type': pos_type,
                        'open_price': pos.price_open,
                        'volume': pos.volume
                    }
                    add_event(f"BUKA {pos_type} {pos.volume} lot @ {pos.price_open}")

            closed_tickets = [t for t in tracked_positions if t not in current_tickets]
            if closed_tickets:
                for ticket in closed_tickets:
                    info = tracked_positions.pop(ticket)
                    session_trades += 1

                    # Ambil riwayat deal langsung dari tiket posisi (menghindari error zona waktu)
                    pos_deals = mt5.history_deals_get(position=ticket)
                    pos_deals = [d for d in (pos_deals or []) if d.entry in (1, 3)]

                    if pos_deals:
                        deal = pos_deals[-1]
                        pnl = deal.profit + deal.swap + deal.commission
                        session_profit += pnl
                        if pnl >= 0:
                            session_wins += 1
                            icon = "+"
                        else:
                            session_losses += 1
                            icon = ""
                        add_event(f"TUTUP {info['type']} | {icon}${pnl:.2f}")
                    else:
                        add_event(f"TUTUP {info['type']} (Tiket: {ticket})")

            # ── 3. Ambil data OHLCV & Hasilkan Sinyal ──
            df_latest = get_historical_rates(SYMBOL, active_timeframe, num_bars=300)
            signal_str = "WAIT"
            val1_str = "N/A"
            val2_str = "N/A"
            cooldown_aktif = False

            if df_latest is not None:
                signal, atr_val, val1, val2 = generate_signal(SYMBOL, price, df_latest)
                if val1 != 'N/A': val1_str = f"{val1:.1f}"
                if val2 != 'N/A': val2_str = f"{val2:.1f}"

                current_time = time.time()
                if current_time - last_trade_time < cooldown_seconds:
                    signal = 'WAIT'
                    cooldown_aktif = True
                
                signal_str = signal

                # ── 4. Eksekusi Order & Flash Close ──
                # Lakukan flash close diam-diam
                check_flash_close(SYMBOL)

                if signal in ['BUY', 'SELL']:
                    exec_price = price['ask'] if signal == 'BUY' else price['bid']
                    add_event(f"SINYAL {signal}! Mencoba eksekusi...")
                    # Simpan posisi print asli agar tidak mengotori dashboard
                    result_ticket = execute_order(SYMBOL, LOT_SIZE, signal, exec_price, atr_value=atr_val)
                    if result_ticket is not None:
                        last_trade_time = time.time()
                        wait_start_time = time.time()
                    else:
                        # Gagal eksekusi (ditolak broker / max posisi), beri jeda 15 detik agar tidak spam
                        last_trade_time = time.time() - cooldown_seconds + 15

            # ── 5. Gambar Dashboard ──
            os.system('cls')
            elapsed = int(time.time() - wait_start_time)
            hrs, remainder = divmod(elapsed, 3600)
            mins, secs = divmod(remainder, 60)
            elapsed_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

            total_pnl = sum((p.profit + p.swap) for p in current_tickets.values())
            
            print("=" * 56)
            print(f"  TRADING BOT PYTHON (Mode {pilihan})")
            print("=" * 56)
            print(f"  Symbol: {SYMBOL:<9} | Uptime / Wait: {elapsed_str}")
            print("-" * 56)
            print(f"  RSI: {val1_str:<6} | MACD: {val2_str:<6} | Sinyal: {signal_str}")
            if cooldown_aktif:
                mnt = cooldown_seconds // 60
                print(f"  Status : COOLDOWN (Menunggu {mnt} Menit)")
            else:
                print("  Status : MENCARI PELUANG...")
            print("-" * 56)
            print(f"  Bid: {price['bid']:<12.2f}  Ask: {price['ask']:<12.2f}")
            print("-" * 56)
            if len(current_tickets) > 0:
                pnl_sign = "+" if total_pnl >= 0 else ""
                print(f"  Posisi Aktif : {len(current_tickets)}")
                print(f"  Floating PnL : {pnl_sign}${total_pnl:.2f}")
            else:
                print("  Posisi Aktif : 0")
                print("  Floating PnL : $0.00")
            print("-" * 56)
            winrate = (session_wins / session_trades * 100) if session_trades > 0 else 0
            sp_sign = "+" if session_profit >= 0 else ""
            print(f"  Trade: {session_trades}  |  W: {session_wins}  L: {session_losses}  |  WR: {winrate:.0f}%")
            print(f"  Total P/L Sesi : {sp_sign}${session_profit:.2f}")
            print("=" * 56)
            print("  Riwayat Event:")
            for line in event_log:
                print(line)
            print("-" * 56)
            print("  Tekan Ctrl+C untuk berhenti.")

            # Mempercepat loop khusus untuk Mode 5 (Crazy Layer) agar bisa langsung beruntun
            if settings.ALGO_MODE == 5:
                time.sleep(0.2)
            else:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n")
        print("="*60)
        print("📊 RINGKASAN SESI TRADING PYTHON")
        print("="*60)
        print(f"   Total Trade: {session_trades}")
        print(f"   Total P/L  : ${session_profit:+.2f}")
        print("="*60)
        logger.info("Menerima perintah penghentian manual (Ctrl+C).")
    finally:
        logger.info("Menyelesaikan tugas dan menutup program.")
        stop_mt5()

if __name__ == '__main__':
    main()
