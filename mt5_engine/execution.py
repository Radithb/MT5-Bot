import MetaTrader5 as mt5
import logging
import datetime
from config import settings

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
        for ticket in closed_tickets:
            info = tracked_positions.pop(ticket)
            
            # Cari deal penutupan untuk tiket posisi ini menggunakan ID posisi secara langsung
            pos_deals = mt5.history_deals_get(position=ticket)
            pos_deals = [d for d in (pos_deals or []) if d.entry in (1, 3)]
            
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

def close_position(position, comment="Close by Bot"):
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
        "comment": comment[:31], # MT5 membatasi komentar maksimal 31 karakter
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

    # 2. Tutup Posisi Berlawanan (Reversal) jika diizinkan
    if settings.CLOSE_ON_REVERSAL:
        for pos in open_positions:
            if pos.type == opposite_pos_type:
                close_position(pos)
        # Refresh daftar posisi setelah penutupan
        open_positions = get_open_positions(symbol)
    else:
        # Jika tidak otomatis ditutup, cek ALLOW_HEDGING
        if getattr(settings, 'ALLOW_HEDGING', False):
            pass # Biarkan saja, kita boleh buka posisi berlawanan sekaligus!
        else:
            # pastikan kita TIDAK MEMBUKA posisi baru berlawanan arah (Anti-Hedging)
            opposite_positions = [p for p in open_positions if p.type == opposite_pos_type]
            if len(opposite_positions) > 0:
                logger.debug(f"Lewati {signal_type}: Sedang ada {len(opposite_positions)} posisi berlawanan arah yang aktif. Menunggu hingga Hit TP/SL.")
                return None

    # 3. Cek jumlah maksimal open posisi
    if len(open_positions) >= settings.MAX_OPEN_POSITIONS:
        logger.debug(f"Lewati {signal_type}: Maksimal open posisi tercapai ({settings.MAX_OPEN_POSITIONS})")
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
    same_dir_positions = [p for p in open_positions if p.type == target_pos_type]
    for pos in same_dir_positions:
        price_diff = abs(price - pos.price_open)
        # Ubah poin ke harga sebenarnya
        min_distance = settings.MIN_ENTRY_DISTANCE_POINTS * point
        if price_diff < min_distance:
            logger.debug(f"Lewati {signal_type}: Jarak ke posisi aktif terakhir terlalu dekat ({int(price_diff/point)} points < min {settings.MIN_ENTRY_DISTANCE_POINTS} points).")
            return None

    # 4. Hitung SL (Stop Loss) dan TP (Take Profit) secara Dinamis menggunakan ATR
    sl = 0.0
    tp = 0.0
    if atr_value > 0:
        sl_dist = atr_value * settings.SL_ATR_MULTIPLIER
        tp_dist = atr_value * settings.TP_ATR_MULTIPLIER
        
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
    return result.order

# Variabel global untuk menyimpan profit tertinggi setiap posisi
trailing_max_profit = {}

def check_flash_close(symbol=None):
    """
    Fungsi Ultra-Scalping: Menutup posisi secara manual jika profit/loss sudah 
    menyentuh atau melewati target FLASH_PROFIT_USD atau FLASH_LOSS_USD.
    """
    if not settings.USE_FLASH_CLOSE and not getattr(settings, 'USE_TRAILING_STOP', False):
        return

    open_positions = get_open_positions(symbol)
    open_tickets = [p.ticket for p in open_positions]
    
    # Bersihkan memori tiket yang sudah ditutup
    for t in list(trailing_max_profit.keys()):
        if t not in open_tickets:
            del trailing_max_profit[t]

    for pos in open_positions:
        # Update rekor profit tertinggi posisi ini
        if pos.ticket not in trailing_max_profit:
            trailing_max_profit[pos.ticket] = pos.profit
        else:
            if pos.profit > trailing_max_profit[pos.ticket]:
                trailing_max_profit[pos.ticket] = pos.profit

    # --- FITUR BASKET CLOSE (Tutup Semua Jika Total Biru) ---
    if getattr(settings, 'USE_BASKET_CLOSE', False) and len(open_positions) > 0:
        buy_positions = [p for p in open_positions if p.type == mt5.POSITION_TYPE_BUY]
        sell_positions = [p for p in open_positions if p.type == mt5.POSITION_TYPE_SELL]
        
        # Cek Basket BUY
        if len(buy_positions) > 0:
            total_buy_pnl = sum((p.profit + p.swap) for p in buy_positions)
            if total_buy_pnl >= getattr(settings, 'BASKET_PROFIT_USD', 2.0):
                print()
                logger.info(f"[🧺 BASKET CLOSE] Cuan Rombongan BUY Tercapai! Total: +${total_buy_pnl:.2f}. Menutup {len(buy_positions)} layer BUY!")
                for p in buy_positions:
                    close_position(p, comment="Basket BUY Profit")
            elif getattr(settings, 'BASKET_LOSS_USD', None) is not None and total_buy_pnl <= settings.BASKET_LOSS_USD:
                print()
                logger.info(f"[💀 BASKET LOSS] Batas Rugi Rombongan BUY Tersentuh! Total: -${abs(total_buy_pnl):.2f}. Cutloss {len(buy_positions)} layer BUY!")
                for p in buy_positions:
                    close_position(p, comment="Basket BUY Cutloss")
                    
        # Cek Basket SELL
        if len(sell_positions) > 0:
            total_sell_pnl = sum((p.profit + p.swap) for p in sell_positions)
            if total_sell_pnl >= getattr(settings, 'BASKET_PROFIT_USD', 2.0):
                print()
                logger.info(f"[🧺 BASKET CLOSE] Cuan Rombongan SELL Tercapai! Total: +${total_sell_pnl:.2f}. Menutup {len(sell_positions)} layer SELL!")
                for p in sell_positions:
                    close_position(p, comment="Basket SELL Profit")
            elif getattr(settings, 'BASKET_LOSS_USD', None) is not None and total_sell_pnl <= settings.BASKET_LOSS_USD:
                print()
                logger.info(f"[💀 BASKET LOSS] Batas Rugi Rombongan SELL Tersentuh! Total: -${abs(total_sell_pnl):.2f}. Cutloss {len(sell_positions)} layer SELL!")
                for p in sell_positions:
                    close_position(p, comment="Basket SELL Cutloss")
                    
        # Refresh open_positions setelah ada basket yang mungkin tertutup
        open_positions = get_open_positions(symbol)
            
    for pos in open_positions:
        # 1. Cek Trailing Stop
        if getattr(settings, 'USE_TRAILING_STOP', False):
            max_p = trailing_max_profit[pos.ticket]
            if max_p >= getattr(settings, 'TRAILING_STOP_START_USD', 1.0):
                # Jika harga berbalik turun dari puncak profit lebih dari batas jarak
                if (max_p - pos.profit) >= getattr(settings, 'TRAILING_STOP_DIST_USD', 0.5):
                    print()
                    logger.info(
                        f"[🛡️ TRAILING STOP] Mengamankan profit! Harga berbalik turun ${max_p - pos.profit:.2f} "
                        f"dari puncak cuan ${max_p:.2f}. Ditutup pada ${pos.profit:.2f}."
                    )
                    close_position(pos, comment="Trailing Stop Close")
                    continue

        # 2. Cek Flash Profit / Loss
        if not settings.USE_FLASH_CLOSE:
            continue
            
        if pos.profit >= settings.FLASH_PROFIT_USD:
            print() # Reset baris live status
            logger.info(
                f"[⚡ FLASH PROFIT] Cuan kilat +${pos.profit:.2f} (Target: {settings.FLASH_PROFIT_USD})! "
                f"Bungkus Tiket {pos.ticket} sekarang juga."
            )
            close_position(pos, comment="Flash Profit Target")
        elif pos.profit <= settings.FLASH_LOSS_USD:
            print() # Reset baris live status
            logger.info(
                f"[⚡ FLASH LOSS] Minus kilat -${abs(pos.profit):.2f} (Batas: {settings.FLASH_LOSS_USD})! "
                f"Cut loss Tiket {pos.ticket} sekarang juga."
            )
            close_position(pos, comment="Flash Cut Loss")
