#!/usr/bin/env python3
"""
Volume Surge Scanner — IHSG Suite Compatible
=============================================
Scan saham IDX dengan logic yang sama persis seperti signal_engine.py:
- Volume ratio = volume hari ini / avg 20 hari
- Threshold: >1.5x = surge, <0.7x = sepi
- Bisa pilih tanggal target (default: latest trading day)
"""
import yfinance as yf
import json
from datetime import datetime, timedelta
import sys

# IDX ticker universe
IDX_TICKERS = [
    'BBCA', 'BBRI', 'BMRI', 'TLKM', 'ASII', 'UNVR', 'BBNI', 'HMSP', 'GOTO', 'BRIS',
    'INDF', 'KLBF', 'ICBP', 'ANTM', 'CPIN', 'ACES', 'EMTK', 'TOWR', 'MAPI', 'EXCL',
    'BUKA', 'ADRO', 'BYAN', 'PTBA', 'ITMG', 'HRUM', 'INCO', 'TINS', 'MDKA', 'MEDC',
    'BRPT', 'MTEL', 'PGAS', 'ELSA', 'AKRA', 'SRTG', 'AMRT', 'GGRM', 'ERAA', 'ADMR',
    'INKP', 'TPIA', 'SMGR', 'WIKA', 'PTPP', 'ADHI', 'SMBR', 'MNCN', 'SCMA',
    'PWON', 'ESSA', 'BREN', 'SSIA', 'FILM', 'BBTN', 'BMTR', 'CTRA', 'BSDE', 'SMRA',
    'PANI', 'DATA', 'DCII', 'DMAS', 'LPPF', 'MIKA', 'KBLV', 'ARTO', 'NATO',
    'CBDK', 'DSNG', 'FREN', 'HAIS', 'RALS', 'WOOD', 'ASSA', 'AUTO', 'SILO', 'MYOR',
    'STTP', 'ULTJ', 'INDY', 'TRAM', 'TBIG', 'BFIN', 'MEGA', 'NISP', 'PNBS', 'BNLI',
    'BBKP', 'BNGA', 'MAYA', 'BNII', 'MCAS', 'BJTM', 'KREN', 'MPPA', 'DSFI',
    'ARNA', 'BSSR', 'CLEO', 'DEWA', 'DOID', 'EDGE', 'HEAL', 'ISAT', 'JPFA', 'KAEF'
]

def scan_volume_surge(target_date=None, lookback=20, surge_threshold=1.5):
    """
    Scan volume surge dengan logic IHSG Suite.
    
    Args:
        target_date: datetime object atau None (latest)
        lookback: periode rata-rata volume (default 20 hari)
        surge_threshold: minimal ratio untuk surge (default 1.5x)
    
    Returns:
        dict dengan hasil scan
    """
    if target_date is None:
        target_date = datetime.now()
    
    # Fetch data period (target + buffer untuk kalkulasi avg)
    period_days = lookback + 10  # Extra buffer
    
    print(f"🔍 Scanning volume surge untuk {target_date.strftime('%Y-%m-%d')}")
    print(f"   Lookback: {lookback} hari | Threshold: {surge_threshold}x")
    print()
    
    results = []
    failed = []
    
    for ticker_base in IDX_TICKERS:
        ticker = f"{ticker_base}.JK"
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=f"{period_days}d", end=target_date + timedelta(days=1))
            
            if hist.empty or len(hist) < lookback + 1:
                failed.append((ticker_base, "Insufficient data"))
                continue
            
            # Find target date in history (or closest before it)
            hist_dates = hist.index.date
            target_idx = None
            for i in range(len(hist_dates) - 1, -1, -1):
                if hist_dates[i] <= target_date.date():
                    target_idx = i
                    break
            
            if target_idx is None or target_idx < lookback:
                failed.append((ticker_base, "Target date not found"))
                continue
            
            # Calculate volume ratio (LOGIC SAMA DENGAN signal_engine.py)
            latest_vol = hist['Volume'].iloc[target_idx]
            avg_vol_window = hist['Volume'].iloc[target_idx - lookback:target_idx]
            avg_vol = avg_vol_window.mean()
            
            if avg_vol == 0 or pd.isna(avg_vol):
                failed.append((ticker_base, "Zero avg volume"))
                continue
            
            vol_ratio = latest_vol / avg_vol
            
            # Get price data
            latest_close = hist['Close'].iloc[target_idx]
            actual_date = hist.index[target_idx].strftime('%Y-%m-%d')
            
            # Price change
            if target_idx > 0:
                prev_close = hist['Close'].iloc[target_idx - 1]
                price_change_pct = ((latest_close - prev_close) / prev_close) * 100
            else:
                price_change_pct = 0
            
            # Classify volume signal (SAMA DENGAN signal_engine.py line 159-166)
            if vol_ratio > surge_threshold:
                vol_signal = "SURGE"
            elif vol_ratio < 0.7:
                vol_signal = "SEPI"
            else:
                vol_signal = "NORMAL"
            
            results.append({
                'ticker': ticker_base,
                'date': actual_date,
                'volume': int(latest_vol),
                'avg_volume': int(avg_vol),
                'vol_ratio': round(vol_ratio, 2),
                'price': round(latest_close, 0),
                'price_change_pct': round(price_change_pct, 2),
                'vol_signal': vol_signal
            })
            
        except Exception as e:
            failed.append((ticker_base, str(e)[:40]))
    
    # Filter surge only
    surged = [r for r in results if r['vol_signal'] == 'SURGE']
    surged.sort(key=lambda x: x['vol_ratio'], reverse=True)
    
    # Stats
    green_count = sum(1 for r in surged if r['price_change_pct'] > 0)
    red_count = sum(1 for r in surged if r['price_change_pct'] < 0)
    
    return {
        'scan_time': datetime.now().isoformat(),
        'target_date': target_date.strftime('%Y-%m-%d'),
        'total_scanned': len(IDX_TICKERS),
        'success_count': len(results),
        'failed_count': len(failed),
        'surge_threshold': surge_threshold,
        'surge_count': len(surged),
        'green_count': green_count,
        'red_count': red_count,
        'top_surges': surged[:30],
        'all_results': results,
        'failed': failed
    }

if __name__ == '__main__':
    import pandas as pd
    
    # Parse date from command line or use latest
    if len(sys.argv) > 1:
        target_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
    else:
        target_date = None  # Latest
    
    # Run scan
    data = scan_volume_surge(target_date=target_date)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"VOLUME SURGE SCAN — {data['target_date']}")
    print(f"{'='*70}")
    print(f"Total scanned: {data['total_scanned']}")
    print(f"Success: {data['success_count']} | Failed: {data['failed_count']}")
    print(f"Surge detected (≥{data['surge_threshold']}x): {data['surge_count']}")
    print(f"   Green (naik): {data['green_count']}")
    print(f"   Red (turun): {data['red_count']}")
    print()
    
    # Print top 15
    print(f"{'#':>3} {'TICKER':<8} {'SURGE':>8} {'VOLUME':>15} {'PRICE':>12} {'CHANGE':>8}")
    print("="*70)
    for i, r in enumerate(data['top_surges'][:15], 1):
        emoji = "🟢" if r['price_change_pct'] > 0 else "🔴"
        print(f"{i:3d} {r['ticker']:<8} {r['vol_ratio']:>7.2f}x "
              f"{r['volume']:>15,} Rp{r['price']:>10,.0f} "
              f"{emoji} {r['price_change_pct']:>+6.2f}%")
    
    # Save to JSON
    output_file = '/tmp/volume-surge-idx/data.json'
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print()
    print(f"✅ Data saved to: {output_file}")
