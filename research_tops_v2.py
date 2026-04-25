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

def analyze_top_precision(df, name):
    print(f"\n=== Refining {name} Swing Highs ===")
    
    # Indicators
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['MA240'] = df['Close'].rolling(window=240).mean()
    
    df['Dist_MA60'] = (df['Close'] - df['MA60']) / df['MA60']
    df['Dist_MA240'] = (df['Close'] - df['MA240']) / df['MA240']
    
    # Identifying Local Highs
    window = 10
    df['Is_Local_High'] = False
    for i in range(window, len(df) - window):
        subset = df['Close'].iloc[i-window : i+window+1]
        if df['Close'].iloc[i] == subset.max():
            if df['Dist_MA60'].iloc[i] > 0.05:
                df.iloc[i, df.columns.get_loc('Is_Local_High')] = True
    
    local_highs = df[df['Is_Local_High']].copy()
    
    # Calculate days since top until a 5% drop
    # This helps understand if the signal was "early"
    
    print(f"Analyzing {len(local_highs)} peaks...")
    
    # New Indicator Idea: TCS + Trend Filter
    # Only signal Top if Price < MA10 (Initial breakdown) OR RSI starts declining.
    
    # Let's test: Dist_MA240 > 15% AND (VIX < 14 OR RSI60 > 62)
    df['TCS_v2'] = (
        np.clip(df['Dist_MA240'] * 200, 0, 40) + # 20% dist = 40 pts
        np.clip((65 - df['VIX']) * 2, 0, 30) + # VIX 15 = 30 pts
        np.clip((df['RSI60'] - 50) * 3, 0, 30) # RSI 60 = 30 pts
    )
    
    # Add a "Momentum Decay" filter: 
    # Only show Top zone if the 5-day return is slowing down compared to the 20-day return.
    df['ROC5'] = df['Close'].pct_change(5)
    df['ROC20'] = df['Close'].pct_change(20)
    df['Momentum_Decay'] = df['ROC5'] < (df['ROC20'] / 4) # Simplified decay
    
    df['Signal_Top_V2'] = (df['TCS_v2'] > 75) & df['Momentum_Decay']
    
    tops_v1 = df[df['TCS_v2'] > 75]
    tops_v2 = df[df['Signal_Top_V2']]
    
    print(f"V1 Signals (Raw Score > 75): {len(tops_v1)}")
    print(f"V2 Signals (With Momentum Decay): {len(tops_v2)}")
    
    # Check if V2 signals are closer to the actual peaks
    # (Simplified: average distance to local high)

def main():
    twii = load_data('twii_data.json')
    analyze_top_precision(twii, "TWII")
    
    nasdaq = load_data('nasdaq_data.json')
    analyze_top_precision(nasdaq, "NASDAQ")

if __name__ == "__main__":
    main()
