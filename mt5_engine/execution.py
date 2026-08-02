import MetaTrader5 as mt5
import logging
import datetime
from config.settings import (
    MAX_OPEN_POSITIONS, 
    CLOSE_ON_REVERSAL, 
    MIN_ENTRY_DISTANCE_POINTS,
    SL_ATR_MULTIPLIER,
    TP_ATR_MULTIPLIER
)

logger = logging.getLogger("MT5_Bot")

# Memory tracking untuk mendeteksi penutupan posisi otomatis oleh MT5 (Hit SL / TP)
tracked_positions = {}

def check_closed_positions(symbol=None):
    """
    Memantau posisi yang ditutup secara otomatis oleh broker MT5 (Hit SL / Hit TP)
    dan mencetak laporan profit/loss ke live log.
    """
    global tracked_positions

    current_positions = get_open_positions(symbol)
    current_tickets = {p.ticket: p for p in current_positions}

    # 1. Deteksi posisi yang menghilang (berhasil ditutup oleh SL, TP, atau Manual)
    closed_tickets = [t for t in tracked_positions if t not in current_tickets]
    
    if closed_tickets:
        now = datetime.datetime.now()
        from_date = now - datetime.timedelta(days=1)
        
        # Ambil riwayat deal dari MT5
        history_deals = mt5.history_deals_get(from_date, now)
        
        for ticket in closed_tickets:
            info = tracked_positions.pop(ticket)
            
            # Cari deal penutupan untuk tiket posisi ini (entry == 1: ENTRY_OUT, entry == 3: ENTRY_OUT_BY)
            pos_deals = [d for d in (history_deals or []) if d.position_id == ticket and d.entry in (1, 3)]
            
            if pos_deals:
                deal = pos_deals[-1]
                pnl = deal.profit + deal.swap + deal.commission
                comment = deal.comment.lower()
                close_price = deal.price
                
                print()  # Reset baris live status agar log tidak tertimpa
                if "sl" in comment:
                    logger.info(
                        f"[SL] HIT SL (Stop Loss)! Posisi {info['type']} (Tiket: {ticket}) | "
                        f"Entry: {info['open_price']} → Exit: {close_price} | LOSS: -${abs(pnl):.2f}"
                    )
                elif "tp" in comment:
                    logger.info(
                        f"[TP] HIT TP (Take Profit)! Posisi {info['type']} (Tiket: {ticket}) | "
                        f"Entry: {info['open_price']} → Exit: {close_price} | PROFIT: +${pnl:.2f}"
                    )
                else:
                    label = "PROFIT" if pnl >= 0 else "LOSS"
                    logger.info(
                        f"[{label}] POSISI DITUTUP! Posisi {info['type']} (Tiket: {ticket}) | "
                        f"Entry: {info['open_price']} → Exit: {close_price} | {label}: ${pnl:+.2f} ({deal.comment})"
                    )
            else:
                print()
                logger.info(f"ℹ️ Posisi {info['type']} (Tiket: {ticket}) telah ditutup di MT5.")

    # 2. Daftarkan posisi aktif saat ini ke memory tracker
    for t, p in current_tickets.items():
        if t not in tracked_positions:
            type_str = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
            tracked_positions[t] = {
                'symbol': p.symbol,
                'type': type_str,
                'open_price': p.price_open
            }

def get_open_positions(symbol=None):
    """
    Mengambil daftar posisi aktif yang sedang terbuka.
    """
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()
        
    if positions is None:
        return []
    return list(positions)

def close_position(position):
    """
    Menutup posisi tertentu berdasarkan tiketnya.
    """
    tick = mt5.symbol_info_tick(position.symbol)
    if not tick:
        logger.error(f"Gagal menutup posisi {position.ticket}: Tick tidak ditemukan")
        return False

    # Tentukan tipe penutupan (BUY ditutup dengan SELL di harga Bid, SELL ditutup dengan BUY di harga Ask)
    if position.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "deviation": 10,
        "magic": 234000,
        "comment": "Close by Bot Reversal",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        # Hitung profit/loss dari posisi yang ditutup
        pnl = position.profit
        pnl_type = "PROFIT" if pnl >= 0 else "LOSS"
        pos_type_str = "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL"
        logger.info(
            f"[MANUAL CLOSE] Menutup posisi {pos_type_str} (Tiket: {position.ticket}) | "
            f"Entry: {position.price_open} → Close: {price} | "
            f"{pnl_type}: ${pnl:+.2f}"
        )
        return True
    else:
        err_msg = result.comment if result else "No response"
        logger.error(f"Gagal menutup posisi {position.ticket}: {err_msg}")
        return False

def execute_order(symbol, lot, signal_type, price=None, atr_value=0.0):
    """
    Mengeksekusi order BUY atau SELL dengan Manajemen Risiko Multi-Posisi Efisien dan SL/TP Dinamis berbasis ATR.
    """
    if signal_type not in ['BUY', 'SELL']:
        return None

    open_positions = get_open_positions(symbol)
    target_pos_type = mt5.POSITION_TYPE_BUY if signal_type == 'BUY' else mt5.POSITION_TYPE_SELL
    opposite_pos_type = mt5.POSITION_TYPE_SELL if signal_type == 'BUY' else mt5.POSITION_TYPE_BUY

    # 1. Close-on-Reversal: Jika ada posisi berlawanan arah, tutup terlebih dahulu agar efisien
    if CLOSE_ON_REVERSAL:
        for pos in open_positions:
            if pos.type == opposite_pos_type:
                close_position(pos)
        # Refresh daftar posisi setelah penutupan
        open_positions = get_open_positions(symbol)
    else:
        # Jika tidak otomatis ditutup, pastikan kita TIDAK MEMBUKA posisi baru berlawanan arah (Anti-Hedging)
        opposite_positions = [p for p in open_positions if p.type == opposite_pos_type]
        if len(opposite_positions) > 0:
            logger.debug(f"Lewati {signal_type}: Sedang ada {len(opposite_positions)} posisi berlawanan arah yang aktif. Menunggu hingga Hit TP/SL.")
            return None

    # 2. Cek apakah jumlah posisi aktif dalam arah yang sama sudah mencapai batas maksimal
    same_dir_positions = [p for p in open_positions if p.type == target_pos_type]
    if len(same_dir_positions) >= MAX_OPEN_POSITIONS:
        logger.debug(f"Lewati {signal_type}: Posisi {signal_type} aktif untuk {symbol} sudah mencapai batas ({len(same_dir_positions)}/{MAX_OPEN_POSITIONS}).")
        return None

    # Dapatkan info symbol untuk kalkulasi point & desimal
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Gagal mendapatkan info symbol: {symbol}")
        return None
        
    point = symbol_info.point

    # Dapatkan harga saat ini jika tidak disediakan
    if price is None:
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"Gagal mengeksekusi {signal_type}: Data harga tidak ditemukan untuk {symbol}")
            return None
        price = tick.ask if signal_type == 'BUY' else tick.bid

    # 3. Filtering Jarak Minimal (Prevent Clustered Entries): Jangan buka posisi baru di harga yang terlalu dekat
    for pos in same_dir_positions:
        price_diff_points = abs(price - pos.price_open) / point
        if price_diff_points < MIN_ENTRY_DISTANCE_POINTS:
            logger.debug(f"Lewati {signal_type}: Jarak ke posisi aktif terakhir terlalu dekat ({int(price_diff_points)} points < min {MIN_ENTRY_DISTANCE_POINTS} points).")
            return None

    # 4. Hitung SL (Stop Loss) dan TP (Take Profit) secara Dinamis menggunakan ATR
    sl = 0.0
    tp = 0.0
    if atr_value > 0:
        sl_dist = atr_value * SL_ATR_MULTIPLIER
        tp_dist = atr_value * TP_ATR_MULTIPLIER
        
        # Cek jarak minimum SL/TP yang ditetapkan broker
        min_stop_dist = symbol_info.trade_stops_level * point
        
        # Jika broker tidak memberikan batas (0 = dinamis), gunakan spread * 3 sebagai fallback
        if min_stop_dist <= 0:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                spread = tick.ask - tick.bid
                min_stop_dist = spread * 3  # 3x spread sebagai jarak aman

        if min_stop_dist > 0:
            # Tambah buffer 20% agar aman
            min_stop_dist *= 1.2
            if sl_dist < min_stop_dist:
                sl_dist = min_stop_dist
            if tp_dist < min_stop_dist:
                tp_dist = min_stop_dist
        
        if signal_type == 'BUY':
            sl = round(price - sl_dist, symbol_info.digits)
            tp = round(price + tp_dist, symbol_info.digits)
        else:  # SELL
            sl = round(price + sl_dist, symbol_info.digits)
            tp = round(price - tp_dist, symbol_info.digits)

    # Struktur request ke MT5
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": mt5.ORDER_TYPE_BUY if signal_type == 'BUY' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 234000,
        "comment": "AI Bot Order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    logger.info(f"Mengirim permintaan {signal_type} {symbol} ({lot} Lot) | Price: {price} | SL: {sl} | TP: {tp}")
    
    # Kirim order
    result = mt5.order_send(request)
    
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        err_msg = result.comment if result else "Tidak ada respon dari MT5"
        err_code = result.retcode if result else "Unknown"
        logger.error(f"Order {signal_type} GAGAL. Error code: {err_code} - {err_msg}")
        return None
        
    logger.info(f"Order {signal_type} BERHASIL! Tiket: {result.order}")
    return result
