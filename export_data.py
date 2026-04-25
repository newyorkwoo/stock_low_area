import yfinance as yf
import pandas as pd
import json
import time
from datetime import datetime

def calculate_rsi(data, window=60):
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    ema_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    ema_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    rs = ema_gain / ema_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def batch_download(ticker, start_year=2007):
    start_date = f"{start_year}-01-01"
    end_date = (datetime.now() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Downloading {ticker} from {start_date} to {end_date}...")
    
    try:
        t = yf.Ticker(ticker)
        data = t.history(start=start_date, end=end_date)
        if not data.empty:
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            return data.sort_index()
    except Exception as e:
        print(f"Error downloading {ticker}: {e}")
        
    return pd.DataFrame()

def prepare_data(ticker_name, index_symbol):
    print(f"Fetching {ticker_name}...")
    df = batch_download(index_symbol, 2007)
    vix = batch_download("^VIX", 2007)
    
    df['RSI60'] = calculate_rsi(df, 60)
    
    df_merged = df.join(vix['Close'].rename('VIX'), how='left')
    df_merged['VIX'] = df_merged['VIX'].ffill()
    df_merged = df_merged.dropna(subset=['Close', 'VIX', 'RSI60'])
    
    # Pre-format for ECharts
    # [date, open, close, lowest, highest, volume, vix, rsi]
    output_data = []
    for date, row in df_merged.iterrows():
        date_str = date.strftime('%Y-%m-%d')
        output_data.append([
            date_str,
            round(row['Open'], 2),
            round(row['Close'], 2),
            round(row['Low'], 2),
            round(row['High'], 2),
            int(row['Volume']) if 'Volume' in row and not pd.isna(row['Volume']) else 0,
            round(row['VIX'], 2),
            round(row['RSI60'], 2)
        ])
    
    with open(f'{ticker_name}_data.json', 'w') as f:
        json.dump(output_data, f)
    print(f"Saved {ticker_name}_data.json")

def main():
    prepare_data("twii", "^TWII")
    prepare_data("nasdaq", "^IXIC")

if __name__ == "__main__":
    main()
