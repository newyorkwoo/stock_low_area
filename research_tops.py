import pandas as pd
import json
import numpy as np

def load_data(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data, columns=['Date', 'Open', 'Close', 'Low', 'High', 'Volume', 'VIX', 'RSI60'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df

def analyze_top_indicators(df, name):
    print(f"\n=== Analyzing {name} Swing Highs ===")
    
    # Moving Averages
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA240'] = df['Close'].rolling(window=240).mean()
    
    # Distance from MA
    df['Dist_MA60'] = (df['Close'] - df['MA60']) / df['MA60']
    df['Dist_MA240'] = (df['Close'] - df['MA240']) / df['MA240']
    
    # Identifying Local Highs
    window = 10
    df['Is_Local_High'] = False
    for i in range(window, len(df) - window):
        subset = df['Close'].iloc[i-window : i+window+1]
        if df['Close'].iloc[i] == subset.max():
            # Only consider highs that represent some form of trend exhaustion
            if df['Dist_MA60'].iloc[i] > 0.03: # At least 3% above MA60
                df.iloc[i, df.columns.get_loc('Is_Local_High')] = True
    
    local_highs = df[df['Is_Local_High']].copy()
    print(f"Found {len(local_highs)} significant local highs.")
    
    # Statistics at local highs
    stats = {
        'VIX': local_highs['VIX'].mean(),
        'RSI60': local_highs['RSI60'].mean(),
        'Dist_MA60': local_highs['Dist_MA60'].mean(),
        'Dist_MA240': local_highs['Dist_MA240'].mean(),
    }
    
    print("Average indicator values at local highs:")
    for k, v in stats.items():
        print(f"  {k}: {v:.4f}")
        
    # Proposed "Top Confidence Score (TCS)"
    # 1. Dist_MA60 > 10% or Dist_MA240 > 20%
    # 2. RSI60 > 60
    # 3. VIX < 15
    
    df['TCS'] = (
        np.clip(df['Dist_MA60'] * 300, 0, 40) + # 10% dist = 30 pts
        np.clip((df['RSI60'] - 50) * 2, 0, 30) + # RSI 65 = 30 pts
        np.clip((20 - df['VIX']) * 3, 0, 30) # VIX 10 = 30 pts
    )
    
    tops = df[df['TCS'] > 70]
    print(f"Top Signal (TCS > 70) triggered {len(tops)} times.")
    if len(tops) > 0:
        print("Last 5 top signals:")
        print(tops.index[-5:])

def main():
    twii = load_data('twii_data.json')
    analyze_top_indicators(twii, "TWII")
    
    nasdaq = load_data('nasdaq_data.json')
    analyze_top_indicators(nasdaq, "NASDAQ")

if __name__ == "__main__":
    main()
