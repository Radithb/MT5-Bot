//+------------------------------------------------------------------+
//|                                                    Main_EA.mq5   |
//|                        Radith's Day-Trading Master EA             |
//|                  Refactored from Python to Native MQL5            |
//+------------------------------------------------------------------+
#property copyright "Radith"
#property link      ""
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//+------------------------------------------------------------------+
//| ENUM: Pilihan Strategi                                           |
//+------------------------------------------------------------------+
enum EStrategyMode
  {
   MODE_EKSISTING_SAYA = 1,  // Mode 1: RSI + MACD + EMA200 (Strategi Lama)
   MODE_VWAP_SCALPER   = 2   // Mode 2: VWAP Breakout + Volume Validation
  };

//+------------------------------------------------------------------+
//| INPUT PARAMETERS (Bisa diatur dari menu Properties MT5)          |
//+------------------------------------------------------------------+

//--- Pengaturan Umum
input EStrategyMode  InpStrategyMode       = MODE_EKSISTING_SAYA;  // Pilih Strategi
input double         InpLotSize            = 0.05;                 // Ukuran Lot
input int            InpMagicNumber        = 234000;               // Magic Number (ID Bot)

//--- Manajemen Risiko Multi-Posisi
input int            InpMaxOpenPositions    = 2;                   // Maks Posisi Bersamaan
input bool           InpCloseOnReversal     = false;               // Tutup Posisi Saat Reversal?
input int            InpMinEntryDistance    = 500;                  // Jarak Min Antar Entry (Points)

//--- Indikator Mode 1: RSI + MACD + EMA200
input int            InpEMA200_Period      = 200;                  // [M1] Periode EMA Trend
input int            InpRSI_Period         = 14;                   // [M1] Periode RSI
input int            InpMACD_Fast          = 12;                   // [M1] MACD Fast EMA
input int            InpMACD_Slow          = 26;                   // [M1] MACD Slow EMA
input int            InpMACD_Signal        = 9;                    // [M1] MACD Signal Line
input int            InpRSI_Oversold       = 30;                   // [M1] Batas RSI Oversold
input int            InpRSI_Overbought     = 70;                   // [M1] Batas RSI Overbought

//--- Indikator Mode 2: VWAP Scalper
input int            InpVWAP_Period        = 20;                   // [M2] Periode VWAP (bar)
input double         InpVWAP_BandMult      = 1.5;                 // [M2] Multiplier Band VWAP (ATR)
input double         InpVolMultiplier      = 1.3;                  // [M2] Volume Spike Multiplier

//--- SL/TP Berbasis ATR
input int            InpATR_Period         = 14;                   // Periode ATR
input double         InpSL_ATR_Mult        = 1.0;                 // SL = ATR x Multiplier
input double         InpTP_ATR_Mult        = 2.0;                 // TP = ATR x Multiplier

//--- Flash Close (Proteksi USD)
input bool           InpUseFlashClose      = true;                 // Aktifkan Flash Close?
input double         InpFlashProfitUSD     = 5.00;                 // Flash Profit Target ($)
input double         InpFlashLossUSD       = -2.50;                // Flash Loss Limit ($)

//--- Trailing Stop (Fitur Baru)
input bool           InpUseTrailingStop    = true;                 // Aktifkan Trailing Stop?
input double         InpTrailATR_Mult      = 1.5;                 // Trailing Distance = ATR x Mult
input double         InpBreakEvenATR_Mult  = 1.0;                 // Aktifkan BE setelah profit ATR x Mult
input int            InpBreakEvenOffset    = 5;                    // Offset Break-Even (Points)

//--- Cooldown
input int            InpCooldownSeconds    = 900;                  // Jeda Min Antar Trade (Detik)

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                 |
//+------------------------------------------------------------------+
CTrade            Trade;
CPositionInfo     PosInfo;

//--- Handle Indikator
int               hRSI, hMACD, hEMA200, hATR;

//--- State Internal
datetime          lastTradeTime  = 0;
datetime          lastBarTime    = 0;
double            prevRSI        = 50.0;
double            prevMACDHist   = 0.0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   //--- Setup CTrade
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(10);
   Trade.SetTypeFilling(ORDER_FILLING_IOC);

   //--- Buat handle indikator
   hRSI    = iRSI(_Symbol, PERIOD_CURRENT, InpRSI_Period, PRICE_CLOSE);
   hMACD   = iMACD(_Symbol, PERIOD_CURRENT, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
   hEMA200 = iMA(_Symbol, PERIOD_CURRENT, InpEMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   hATR    = iATR(_Symbol, PERIOD_CURRENT, InpATR_Period);

   if(hRSI == INVALID_HANDLE || hMACD == INVALID_HANDLE ||
      hEMA200 == INVALID_HANDLE || hATR == INVALID_HANDLE)
     {
      Print("❌ FATAL: Gagal membuat handle indikator!");
      return(INIT_FAILED);
     }

   Print("============================================================");
   Print("🤖 EA AKTIF | Strategi: ", EnumToString(InpStrategyMode));
   Print("   Lot: ", InpLotSize, " | Maks Posisi: ", InpMaxOpenPositions);
   Print("   Flash Close: ", InpUseFlashClose ? "ON" : "OFF",
         " (Profit: $", InpFlashProfitUSD, " / Loss: $", InpFlashLossUSD, ")");
   Print("   Trailing Stop: ", InpUseTrailingStop ? "ON" : "OFF");
   Print("============================================================");

   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(hRSI    != INVALID_HANDLE) IndicatorRelease(hRSI);
   if(hMACD   != INVALID_HANDLE) IndicatorRelease(hMACD);
   if(hEMA200 != INVALID_HANDLE) IndicatorRelease(hEMA200);
   if(hATR    != INVALID_HANDLE) IndicatorRelease(hATR);

   Print("🛑 EA dihentikan. Alasan: ", reason);
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   //--- 1. Flash Close: Cek setiap tick (eksekusi kilat)
   if(InpUseFlashClose)
      CheckFlashClose();

   //--- 2. Trailing Stop: Cek setiap tick
   if(InpUseTrailingStop)
      ManageTrailingStop();

   //--- 3. Hanya proses sinyal pada bar baru (hemat CPU)
   if(!IsNewBar())
      return;

   //--- 4. Ambil data indikator
   double rsiNow, rsiPrev;
   double macdLine[], macdSignal[], macdHist[];
   double ema200Now, atrNow;

   if(!GetIndicatorValues(rsiNow, rsiPrev, macdHist, ema200Now, atrNow))
      return;

   double macdHistNow  = macdHist[0];
   double macdHistPrev = (ArraySize(macdHist) > 1) ? macdHist[1] : 0.0;

   //--- 5. Tentukan sinyal berdasarkan mode
   int signal = 0; // 0=WAIT, 1=BUY, -1=SELL

   switch(InpStrategyMode)
     {
      case MODE_EKSISTING_SAYA:
         signal = SignalMode1_Eksisting(rsiNow, rsiPrev, macdHistNow, macdHistPrev,
                                         ema200Now, atrNow);
         break;

      case MODE_VWAP_SCALPER:
         signal = SignalMode2_VWAPScalper(atrNow);
         break;
     }

   //--- 6. Cooldown check
   if(signal != 0)
     {
      if((TimeCurrent() - lastTradeTime) < InpCooldownSeconds)
        {
         signal = 0; // Paksa WAIT
        }
     }

   //--- 7. Eksekusi order
   if(signal != 0)
     {
      string signalStr = (signal == 1) ? "BUY" : "SELL";
      if(ExecuteOrder(signalStr, atrNow))
        {
         lastTradeTime = TimeCurrent();
        }
     }

   //--- 8. Tampilkan status live di Comment chart
   DisplayLiveStatus(rsiNow, macdHistNow, signal, atrNow);
  }

//+------------------------------------------------------------------+
//| MODE 1: Strategi Eksisting (RSI Mean-Rev + MACD Trend)           |
//| Terjemahan persis dari signal_generator.py                       |
//+------------------------------------------------------------------+
int SignalMode1_Eksisting(double rsiNow, double rsiPrev,
                           double macdHistNow, double macdHistPrev,
                           double ema200Now, double atrNow)
  {
   double closeNow = iClose(_Symbol, PERIOD_CURRENT, 1); // Close bar terakhir yg sudah selesai

   //--- LOGIKA A: RSI Mean Reversion ---
   bool rsiBuy  = false;
   bool rsiSell = false;

   // Beli jika RSI baru saja keluar dari zona oversold (< 30) ke atas
   if(rsiPrev < InpRSI_Oversold && rsiNow >= InpRSI_Oversold)
      rsiBuy = true;
   // Jual jika RSI baru saja keluar dari zona overbought (> 70) ke bawah
   else if(rsiPrev > InpRSI_Overbought && rsiNow <= InpRSI_Overbought)
      rsiSell = true;

   //--- LOGIKA B: MACD + EMA 200 ---
   bool macdBuy  = false;
   bool macdSell = false;

   // Beli jika harga di atas EMA 200 (Uptrend) DAN MACD Histogram menyeberang ke positif
   if(closeNow > ema200Now && macdHistPrev <= 0 && macdHistNow > 0)
      macdBuy = true;
   // Jual jika harga di bawah EMA 200 (Downtrend) DAN MACD Histogram menyeberang ke negatif
   else if(closeNow < ema200Now && macdHistPrev >= 0 && macdHistNow < 0)
      macdSell = true;

   //--- Gabungkan keduanya (jika salah satu menyala, tembak!)
   if(rsiBuy || macdBuy)    return  1; // BUY
   if(rsiSell || macdSell)  return -1; // SELL

   return 0; // WAIT
  }

//+------------------------------------------------------------------+
//| MODE 2: VWAP Scalper (Breakout + Volume Validation)              |
//+------------------------------------------------------------------+
int SignalMode2_VWAPScalper(double atrNow)
  {
   //--- Hitung VWAP secara manual (Typical Price * Volume / Total Volume)
   double vwap = CalculateVWAP(InpVWAP_Period);
   if(vwap <= 0)
      return 0;

   //--- Band VWAP = VWAP ± (ATR * Multiplier)
   double upperBand = vwap + (atrNow * InpVWAP_BandMult);
   double lowerBand = vwap - (atrNow * InpVWAP_BandMult);

   double closeNow  = iClose(_Symbol, PERIOD_CURRENT, 1);
   double closePrev = iClose(_Symbol, PERIOD_CURRENT, 2);

   //--- Cek volume spike (Volume saat ini > rata-rata * multiplier)
   bool volumeValid = IsVolumeSpike(InpVWAP_Period);

   //--- BUY: Harga breakout ke atas VWAP Upper Band + Volume Spike
   if(closePrev <= upperBand && closeNow > upperBand && volumeValid)
      return 1;

   //--- SELL: Harga breakdown ke bawah VWAP Lower Band + Volume Spike
   if(closePrev >= lowerBand && closeNow < lowerBand && volumeValid)
      return -1;

   return 0;
  }

//+------------------------------------------------------------------+
//| Hitung VWAP Manual (Typical Price * Volume / Sum Volume)         |
//+------------------------------------------------------------------+
double CalculateVWAP(int period)
  {
   double sumTPV   = 0.0;
   double sumVol   = 0.0;

   for(int i = 1; i <= period; i++)
     {
      double high  = iHigh(_Symbol, PERIOD_CURRENT, i);
      double low   = iLow(_Symbol, PERIOD_CURRENT, i);
      double close = iClose(_Symbol, PERIOD_CURRENT, i);
      long   vol   = iVolume(_Symbol, PERIOD_CURRENT, i);

      double tp = (high + low + close) / 3.0;
      sumTPV += tp * (double)vol;
      sumVol += (double)vol;
     }

   if(sumVol <= 0)
      return 0.0;

   return sumTPV / sumVol;
  }

//+------------------------------------------------------------------+
//| Cek apakah volume saat ini di atas rata-rata (Volume Spike)      |
//+------------------------------------------------------------------+
bool IsVolumeSpike(int period)
  {
   long currentVol = iVolume(_Symbol, PERIOD_CURRENT, 1);
   double avgVol   = 0.0;

   for(int i = 2; i <= period + 1; i++)
      avgVol += (double)iVolume(_Symbol, PERIOD_CURRENT, i);

   avgVol /= (double)period;

   return ((double)currentVol > avgVol * InpVolMultiplier);
  }

//+------------------------------------------------------------------+
//| EKSEKUSI ORDER                                                   |
//| Terjemahan persis dari execution.py -> execute_order()            |
//+------------------------------------------------------------------+
bool ExecuteOrder(string signalType, double atrValue)
  {
   ENUM_POSITION_TYPE targetType   = (signalType == "BUY") ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   ENUM_POSITION_TYPE oppositeType = (signalType == "BUY") ? POSITION_TYPE_SELL : POSITION_TYPE_BUY;

   //--- 1. Close-on-Reversal: Tutup posisi berlawanan
   if(InpCloseOnReversal)
     {
      ClosePositionsByType(oppositeType);
     }
   else
     {
      // Anti-Hedging: Jangan buka jika ada posisi berlawanan
      if(CountPositionsByType(oppositeType) > 0)
        {
         PrintFormat("⏳ Lewati %s: Ada posisi berlawanan aktif.", signalType);
         return false;
        }
     }

   //--- 2. Cek batas maksimal posisi searah
   int sameCount = CountPositionsByType(targetType);
   if(sameCount >= InpMaxOpenPositions)
     {
      PrintFormat("⏳ Lewati %s: Posisi penuh (%d/%d).", signalType, sameCount, InpMaxOpenPositions);
      return false;
     }

   //--- 3. Cek jarak minimal antar entry
   double currentPrice = (signalType == "BUY") ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                                : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PosInfo.SelectByIndex(i))
        {
         if(PosInfo.Symbol() == _Symbol &&
            PosInfo.Magic()  == InpMagicNumber &&
            PosInfo.PositionType() == targetType)
           {
            double dist = MathAbs(currentPrice - PosInfo.PriceOpen()) / point;
            if(dist < InpMinEntryDistance)
              {
               PrintFormat("⏳ Lewati %s: Jarak terlalu dekat (%.0f < %d pts).",
                           signalType, dist, InpMinEntryDistance);
               return false;
              }
           }
        }
     }

   //--- 4. Hitung SL/TP Dinamis berbasis ATR
   double sl = 0.0, tp = 0.0;
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(atrValue > 0)
     {
      double slDist = atrValue * InpSL_ATR_Mult;
      double tpDist = atrValue * InpTP_ATR_Mult;

      // Cek jarak minimum SL/TP broker
      double minStopDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
      if(minStopDist <= 0)
        {
         double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
         minStopDist = spread * 3.0;
        }

      // Buffer 20%
      if(minStopDist > 0)
        {
         minStopDist *= 1.2;
         if(slDist < minStopDist) slDist = minStopDist;
         if(tpDist < minStopDist) tpDist = minStopDist;
        }

      if(signalType == "BUY")
        {
         sl = NormalizeDouble(currentPrice - slDist, digits);
         tp = NormalizeDouble(currentPrice + tpDist, digits);
        }
      else
        {
         sl = NormalizeDouble(currentPrice + slDist, digits);
         tp = NormalizeDouble(currentPrice - tpDist, digits);
        }
     }

   //--- 5. Kirim order
   PrintFormat("🔫 Mengirim %s %s (%.2f Lot) | Price: %.*f | SL: %.*f | TP: %.*f",
               signalType, _Symbol, InpLotSize,
               digits, currentPrice, digits, sl, digits, tp);

   bool result = false;
   if(signalType == "BUY")
      result = Trade.Buy(InpLotSize, _Symbol, currentPrice, sl, tp, "EA Bot Order");
   else
      result = Trade.Sell(InpLotSize, _Symbol, currentPrice, sl, tp, "EA Bot Order");

   if(result && Trade.ResultRetcode() == TRADE_RETCODE_DONE)
     {
      PrintFormat("✅ Order %s BERHASIL! Tiket: %d", signalType, Trade.ResultOrder());
      return true;
     }
   else
     {
      PrintFormat("❌ Order %s GAGAL! Error: %d - %s",
                  signalType, Trade.ResultRetcode(), Trade.ResultRetcodeDescription());
      return false;
     }
  }

//+------------------------------------------------------------------+
//| FLASH CLOSE                                                      |
//| Terjemahan persis dari execution.py -> check_flash_close()        |
//+------------------------------------------------------------------+
void CheckFlashClose()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(!PosInfo.SelectByIndex(i))
         continue;
      if(PosInfo.Symbol() != _Symbol || PosInfo.Magic() != InpMagicNumber)
         continue;

      double profit = PosInfo.Profit() + PosInfo.Swap() + PosInfo.Commission();

      if(profit >= InpFlashProfitUSD)
        {
         PrintFormat("⚡ FLASH PROFIT! +$%.2f (Target: $%.2f) | Bungkus Tiket %d",
                     profit, InpFlashProfitUSD, PosInfo.Ticket());
         Trade.PositionClose(PosInfo.Ticket());
        }
      else if(profit <= InpFlashLossUSD)
        {
         PrintFormat("⚡ FLASH LOSS! -$%.2f (Batas: $%.2f) | Cut Loss Tiket %d",
                     MathAbs(profit), InpFlashLossUSD, PosInfo.Ticket());
         Trade.PositionClose(PosInfo.Ticket());
        }
     }
  }

//+------------------------------------------------------------------+
//| TRAILING STOP & BREAK-EVEN (Fitur Baru)                         |
//| Dinamis berbasis ATR, berlaku universal untuk semua mode          |
//+------------------------------------------------------------------+
void ManageTrailingStop()
  {
   double atrBuf[];
   if(CopyBuffer(hATR, 0, 1, 1, atrBuf) <= 0)
      return;
   double atr = atrBuf[0];

   double trailDist   = atr * InpTrailATR_Mult;
   double beThreshold = atr * InpBreakEvenATR_Mult;
   double point       = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits      = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(!PosInfo.SelectByIndex(i))
         continue;
      if(PosInfo.Symbol() != _Symbol || PosInfo.Magic() != InpMagicNumber)
         continue;

      double openPrice = PosInfo.PriceOpen();
      double curSL     = PosInfo.StopLoss();
      double curTP     = PosInfo.TakeProfit();

      if(PosInfo.PositionType() == POSITION_TYPE_BUY)
        {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double profitDist = bid - openPrice;

         // Break-Even: Jika profit sudah >= beThreshold, geser SL ke entry + offset
         if(profitDist >= beThreshold && curSL < openPrice)
           {
            double newSL = NormalizeDouble(openPrice + InpBreakEvenOffset * point, digits);
            if(newSL > curSL)
               Trade.PositionModify(PosInfo.Ticket(), newSL, curTP);
           }

         // Trailing: Geser SL mengikuti harga jika jaraknya sudah cukup
         double trailSL = NormalizeDouble(bid - trailDist, digits);
         if(trailSL > curSL && trailSL > openPrice)
            Trade.PositionModify(PosInfo.Ticket(), trailSL, curTP);
        }
      else // SELL
        {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profitDist = openPrice - ask;

         // Break-Even
         if(profitDist >= beThreshold && (curSL > openPrice || curSL == 0))
           {
            double newSL = NormalizeDouble(openPrice - InpBreakEvenOffset * point, digits);
            if(curSL == 0 || newSL < curSL)
               Trade.PositionModify(PosInfo.Ticket(), newSL, curTP);
           }

         // Trailing
         double trailSL = NormalizeDouble(ask + trailDist, digits);
         if((trailSL < curSL || curSL == 0) && trailSL < openPrice)
            Trade.PositionModify(PosInfo.Ticket(), trailSL, curTP);
        }
     }
  }

//+------------------------------------------------------------------+
//| HELPER FUNCTIONS                                                 |
//+------------------------------------------------------------------+

//--- Deteksi bar baru (agar tidak spam sinyal pada tick yang sama)
bool IsNewBar()
  {
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(currentBarTime == lastBarTime)
      return false;
   lastBarTime = currentBarTime;
   return true;
  }

//--- Ambil semua nilai indikator sekaligus
bool GetIndicatorValues(double &rsiNow, double &rsiPrev,
                        double &macdHistOut[], double &ema200Now, double &atrNow)
  {
   double rsiBuf[], ema200Buf[], atrBuf[];
   double macdLineBuf[], macdSignalBuf[];

   // Copy 2 bar terakhir (index 1 = bar selesai, index 2 = bar sebelumnya)
   if(CopyBuffer(hRSI,    0, 1, 2, rsiBuf)        < 2) return false;
   if(CopyBuffer(hMACD,   0, 1, 2, macdLineBuf)    < 2) return false;
   if(CopyBuffer(hMACD,   1, 1, 2, macdSignalBuf)  < 2) return false;
   if(CopyBuffer(hEMA200, 0, 1, 1, ema200Buf)      < 1) return false;
   if(CopyBuffer(hATR,    0, 1, 1, atrBuf)         < 1) return false;

   rsiNow    = rsiBuf[0];
   rsiPrev   = rsiBuf[1];
   ema200Now = ema200Buf[0];
   atrNow    = atrBuf[0];

   // Hitung histogram MACD = MACD Line - Signal
   ArrayResize(macdHistOut, 2);
   macdHistOut[0] = macdLineBuf[0] - macdSignalBuf[0]; // Sekarang
   macdHistOut[1] = macdLineBuf[1] - macdSignalBuf[1]; // Sebelumnya

   return true;
  }

//--- Hitung jumlah posisi berdasarkan tipe (BUY/SELL)
int CountPositionsByType(ENUM_POSITION_TYPE posType)
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PosInfo.SelectByIndex(i))
        {
         if(PosInfo.Symbol() == _Symbol &&
            PosInfo.Magic()  == InpMagicNumber &&
            PosInfo.PositionType() == posType)
            count++;
        }
     }
   return count;
  }

//--- Tutup semua posisi berdasarkan tipe
void ClosePositionsByType(ENUM_POSITION_TYPE posType)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PosInfo.SelectByIndex(i))
        {
         if(PosInfo.Symbol() == _Symbol &&
            PosInfo.Magic()  == InpMagicNumber &&
            PosInfo.PositionType() == posType)
           {
            Trade.PositionClose(PosInfo.Ticket());
           }
        }
     }
  }

//--- Tampilkan status live di chart
void DisplayLiveStatus(double rsiVal, double macdHistVal, int signal, double atrVal)
  {
   string sigStr;
   switch(signal)
     {
      case  1: sigStr = "🟢 BUY";  break;
      case -1: sigStr = "🔴 SELL"; break;
      default: sigStr = "⏳ WAIT"; break;
     }

   // Hitung total PnL aktif
   double totalPnL = 0.0;
   int    posCount = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PosInfo.SelectByIndex(i))
        {
         if(PosInfo.Symbol() == _Symbol && PosInfo.Magic() == InpMagicNumber)
           {
            totalPnL += PosInfo.Profit() + PosInfo.Swap() + PosInfo.Commission();
            posCount++;
           }
        }
     }

   string modeStr = (InpStrategyMode == MODE_EKSISTING_SAYA)
                     ? "RSI+MACD+EMA200"
                     : "VWAP Scalper";

   string pnlStr = (posCount > 0)
                    ? StringFormat(" | 💰 PnL: $%+.2f (%d pos)", totalPnL, posCount)
                    : "";

   Comment(StringFormat(
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
      "  🤖 Radith EA v2.0 | %s\n"
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
      "  RSI: %.1f | MACD Hist: %.1f\n"
      "  ATR: %.2f | Sinyal: %s\n"
      "  %s\n"
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
      modeStr, rsiVal, macdHistVal, atrVal, sigStr, pnlStr
   ));
  }
//+------------------------------------------------------------------+
