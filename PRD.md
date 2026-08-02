# Product Requirements Document (PRD)
**Project Name:** MT5 AI Trading Bot
**Platform:** Desktop (Windows) via Python & MetaTrader 5 Terminal
**Current Version:** 1.0 (Phase 1: CLI/Headless)

## 1. Product Overview
Sistem ini adalah perangkat lunak otomasi trading (*algorithmic trading*) yang menghubungkan logika kecerdasan buatan (AI) dengan terminal MetaTrader 5 (MT5). Perangkat lunak ini bertindak sebagai jembatan yang membaca data pasar secara *real-time*, memprosesnya melalui modul analitik/AI, dan mengeksekusi order (Buy/Sell) secara otomatis di akun MT5.

## 2. Goals & Objectives
* **Phase 1 (CLI/Backend):** Membangun mesin (*engine*) utama yang stabil, ringan, dan akurat dalam mengambil data harga dan mengeksekusi order tanpa *delay* melalui terminal.
* **Phase 2 (GUI/UX):** Mengembangkan antarmuka desktop visual (*dashboard*) yang intuitif, memisahkan kompleksitas kode dari pengguna. Desain harus berfokus pada kejelasan informasi (status bot, metrik profit/loss, kontrol lot) dengan tata letak minimalis dan *clean*.

## 3. System Architecture
Sistem menggunakan arsitektur modular (*Separation of Concerns*) untuk memudahkan pemeliharaan dan skalabilitas:
* **MT5 Engine:** Modul yang berinteraksi langsung dengan API lokal `MetaTrader5`. Bertanggung jawab atas koneksi, penarikan data (*Market Data*), dan pengiriman order (*Execution*).
* **AI Strategy / Brain:** Modul terisolasi yang menerima raw data (OHLCV), memproses logika algoritma/AI, dan mengembalikan sinyal keputusan absolut (BUY / SELL / WAIT).
* **Config & Settings:** Pusat kontrol parameter bot (Symbol, Timeframe, Lot Size, Risk Management).

## 4. Core Features (MVP - Phase 1)
1. **Connection Manager:** Auto-connect dan *graceful shutdown* ke terminal MT5 yang sedang berjalan.
2. **Data Ingestion:** Menarik harga saat ini (*Tick/Ask/Bid*) dan riwayat *candlestick* (*Copy Rates*).
3. **Signal Generator:** Fungsi *placeholder* (sementara) yang nantinya akan diisi dengan model ML/AI untuk memprediksi arah pasar.
4. **Order Execution:** Mengirim perintah *Market Order* (Buy/Sell) beserta parameter *Stop Loss* (SL) dan *Take Profit* (TP).
5. **Activity Logging:** Mencatat setiap eksekusi, sinyal, dan *error* ke dalam file teks (.log) untuk keperluan *debugging*.

## 5. UI/UX Requirements (Future Scope - Phase 2)
Untuk mentransisikan bot dari Command Line menjadi aplikasi desktop yang ramah pengguna:
* **Framework:** Menggunakan `CustomTkinter` untuk tampilan *dark-mode* yang modern.
* **Layout Structure:**
  * **Header:** Status koneksi (Indikator warna hijau/merah) dan tombol master "Start/Stop Bot".
  * **Main Panel:** Log aktivitas *real-time* yang mudah dibaca.
  * **Sidebar (Settings):** Input *field* untuk mengubah koin/pair (misal: EURUSD), ukuran Lot, dan parameter risiko tanpa perlu menyentuh kode.
* **Design Principle:** Mengurangi beban kognitif pengguna. Kesalahan koneksi harus menampilkan *feedback* visual yang jelas, bukan sekadar *error traceback* di terminal.

## 6. Tech Stack
* **Language:** Python 3.10+
* **Libraries:** `MetaTrader5`, `pandas` (manipulasi data), `python-dotenv` (keamanan kredensial).
* **Environment:** Virtual Environment (opsional namun disarankan).

## 7. Folder Structure Reference
* `main.py` (Controller Utama)
* `config/` (Pengaturan dan variabel global)
* `mt5_engine/` (Interaksi API MT5)
* `ai_strategy/` (Logika pengambilan keputusan)
* `data/` (Penyimpanan data historis)
* `logs/` (Pencatatan aktivitas)