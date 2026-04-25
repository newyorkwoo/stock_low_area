import yfinance as yf
import pandas as pd
import mplfinance as mpf
import time
from datetime import datetime
import os

def check_and_create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def calculate_rsi(data, window=60):
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Use Exponential Moving Average with alpha = 1 / window for Wilder's Smoothing
    ema_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    ema_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    rs = ema_gain / ema_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def batch_download(ticker, start_year=2007):
    current_year = datetime.now().year
    all_data = []
    
    # Download year by year slowly
    for year in range(start_year, current_year + 1):
        try:
            print(f"Downloading {ticker} for year {year}...")
            start_date = f"{year}-01-01"
            end_date = f"{year+1}-01-01"
            if year == current_year:
                end_date = (datetime.now() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            
            t = yf.Ticker(ticker)
            data = t.history(start=start_date, end=end_date)
            
            if not data.empty:
                if data.index.tz is not None:
                    data.index = data.index.tz_localize(None)
                all_data.append(data)
            
            # Sleep to avoid rate limiting / IP bans
            time.sleep(2)
        except Exception as e:
            print(f"Error downloading {ticker} for {year}: {e}")
            
    if all_data:
        full_df = pd.concat(all_data)
        # Drop duplicates in case of overlap
        full_df = full_df[~full_df.index.duplicated(keep='first')]
        # Sort index
        full_df = full_df.sort_index()
        return full_df
    return pd.DataFrame()

def main():
    out_dir = 'output_charts'
    check_and_create_dir(out_dir)
    
    print("=== Downloading Historical Data ===")
    twii = batch_download("^TWII", 2007)
    print(f"TWII Data fetched: {len(twii)} rows.")
    
    nasdaq = batch_download("^IXIC", 2007)
    print(f"NASDAQ Data fetched: {len(nasdaq)} rows.")
    
    vix = batch_download("^VIX", 2007)
    print(f"VIX Data fetched: {len(vix)} rows.")
    
    if twii.empty or nasdaq.empty or vix.empty:
        print("Missing data, cannot proceed.")
        return
        
    print("=== Processing Indicators ===")
    twii['RSI60'] = calculate_rsi(twii, 60)
    nasdaq['RSI60'] = calculate_rsi(nasdaq, 60)
    
    # Align VIX with the index data
    twii_merged = twii.join(vix['Close'].rename('VIX'), how='left')
    # Fill missing VIX values with previous valid ones (holidays might differ)
    twii_merged['VIX'] = twii_merged['VIX'].ffill()
    
    nasdaq_merged = nasdaq.join(vix['Close'].rename('VIX'), how='left')
    nasdaq_merged['VIX'] = nasdaq_merged['VIX'].ffill()

    # Drop NA to avoid empty plotting regions at start (first 60 rows for RSI)
    twii_merged = twii_merged.dropna(subset=['Close', 'VIX', 'RSI60'])
    nasdaq_merged = nasdaq_merged.dropna(subset=['Close', 'VIX', 'RSI60'])
    
    print("=== Generating Charts ===")
    # Customise matplotlib style for Taiwan (red up, green down)
    mc = mpf.make_marketcolors(up='r', down='g', edge='inherit', wick='inherit', volume='in', inherit=True)
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=":", y_on_right=False)

    # Plot TWII
    print("Plotting TWII chart...")
    ap0 = [
        mpf.make_addplot(twii_merged['VIX'], panel=1, color='purple', ylabel='VIX'),
        mpf.make_addplot(twii_merged['RSI60'], panel=2, color='orange', ylabel='RSI (60)')
    ]
    
    mpf.plot(twii_merged, type='candle', addplot=ap0,
             volume=False, figratio=(16, 10), figscale=1.5,
             title='\nTaiwan Weighted Index (^TWII) + VIX + RSI60 (2007-Present)',
             style=s, panel_ratios=(4, 1, 1), returnfig=False,
             savefig=f'{out_dir}/twii_chart_full.png')
             
    # Plot NASDAQ
    print("Plotting NASDAQ chart...")
    ap1 = [
        mpf.make_addplot(nasdaq_merged['VIX'], panel=1, color='purple', ylabel='VIX'),
        mpf.make_addplot(nasdaq_merged['RSI60'], panel=2, color='orange', ylabel='RSI (60)')
    ]
    
    mpf.plot(nasdaq_merged, type='candle', addplot=ap1,
             volume=False, figratio=(16, 10), figscale=1.5,
             title='\nNASDAQ Composite (^IXIC) + VIX + RSI60 (2007-Present)',
             style=s, panel_ratios=(4, 1, 1), returnfig=False,
             savefig=f'{out_dir}/nasdaq_chart_full.png')
             
    print(f"Done. Charts successfully saved to {out_dir}/ folder.")

if __name__ == '__main__':
    main()
