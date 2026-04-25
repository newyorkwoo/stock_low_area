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

def calculate_indicators(df):
    # Bottom Score
    hi240 = df['Close'].rolling(window=240, min_periods=1).max()
    dd = (df['Close'] - hi240) / hi240
    dd_score = np.clip(-dd * 200, 0, 40)
    vix_score_b = np.clip((df['VIX'] - 20) * 2, 0, 30)
    vix_roc = df['VIX'].pct_change(5)
    vix_roc_score = np.clip(vix_roc * 50, 0, 30)
    rsi_score_b = np.clip((50 - df['RSI60']) * 2, 0, 30)
    df['BottomScore'] = dd_score + np.maximum(vix_score_b, vix_roc_score) + rsi_score_b
    
    # Top Score
    ma60 = df['Close'].rolling(window=60).mean()
    distMA60 = (df['Close'] - ma60) / ma60
    ma_score_t = np.clip(distMA60 * 400, 0, 40)
    vix_score_t = np.clip((20 - df['VIX']) * 3, 0, 30)
    rsi_score_t = np.clip((df['RSI60'] - 50) * 2, 0, 30)
    df['TopScore'] = ma_score_t + vix_score_t + rsi_score_t
    return df

def simulate_strategy(df, name):
    monthly_budget = 10000
    
    # Strategy 1: Regular DCA (Baseline)
    cash_a = 0
    shares_a = 0
    invested_a = 0
    
    # Strategy 2: Signal-Based Dynamic DCA
    cash_b = 0
    shares_b = 0
    invested_b = 0
    savings_b = 0 # Cash saved during Blue periods
    
    current_month = -1
    
    for date, row in df.iterrows():
        # Only act on the first trading day of the month
        if date.month != current_month:
            current_month = date.month
            price = row['Close']
            b_score = row['BottomScore']
            t_score = row['TopScore']
            
            # --- Strategy A (Regular DCA) ---
            shares_a += monthly_budget / price
            invested_a += monthly_budget
            
            # --- Strategy B (Smart Rebalancing) ---
            invested_b += monthly_budget
            cash_b += monthly_budget
            
            if t_score > 75:
                # Blue Zone: Sell 20% of portfolio to cash
                sell_val = (shares_b * price) * 0.20
                shares_b -= sell_val / price
                cash_b += sell_val
            elif b_score > 75:
                # Red Zone: All-in cash
                shares_b += cash_b / price
                cash_b = 0
            else:
                # Neutral: Regular monthly buy
                shares_b += cash_b / price
                cash_b = 0
                
    final_price = df['Close'].iloc[-1]
    value_a = shares_a * final_price
    value_b = shares_b * final_price + savings_b
    
    print(f"\n=== {name} 策略對比 (每月1萬) ===")
    print(f"基準策略 (無腦定投) 最終市值: ${value_a:,.0f} (報酬率: {((value_a-invested_a)/invested_a*100):.1f}%)")
    print(f"進階策略 (信號動態) 最終市值: ${value_b:,.0f} (報酬率: {((value_b-invested_b)/invested_b*100):.1f}%)")
    print(f"進階策略勝出金額: ${value_b - value_a:,.0f}")

def main():
    twii = calculate_indicators(load_data('twii_data.json'))
    simulate_strategy(twii, "TWII")
    
    nasdaq = calculate_indicators(load_data('nasdaq_data.json'))
    simulate_strategy(nasdaq, "NASDAQ")

if __name__ == "__main__":
    main()
