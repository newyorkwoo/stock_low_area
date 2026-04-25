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

def calculate_bottom_score(df):
    # 1. Drawdown Factor (Max 40)
    hi240 = df['Close'].rolling(window=240, min_periods=1).max()
    dd = (df['Close'] - hi240) / hi240
    dd_score = np.clip(-dd * 200, 0, 40)
    
    # 2. VIX Panic Factor (Max 30)
    vix_score = np.clip((df['VIX'] - 20) * 2, 0, 30)
    vix_roc = df['VIX'].pct_change(5)
    vix_roc_score = np.clip(vix_roc * 50, 0, 30)
    final_vix_score = np.maximum(vix_score, vix_roc_score)
    
    # 3. RSI Oversold Factor (Max 30)
    rsi_score = np.clip((50 - df['RSI60']) * 2, 0, 30)
    
    total_score = dd_score + final_vix_score + rsi_score
    return total_score

def run_backtest(df, name):
    df['Score'] = calculate_bottom_score(df)
    
    invest_per_step = 50000 # 5萬元
    total_invested = 0
    total_shares = 0
    is_buying_cycle = False
    last_buy_price = 0
    
    trades = []
    
    for date, row in df.iterrows():
        price = row['Close']
        score = row['Score']
        
        # 觸發初始投入
        if score > 70 and not is_buying_cycle:
            is_buying_cycle = True
            shares = invest_per_step / price
            total_shares += shares
            total_invested += invest_per_step
            last_buy_price = price
            trades.append({'date': date, 'type': 'Initial Buy', 'price': price, 'invested': invest_per_step})
            
        # 續加碼 (每下跌 5%)
        elif is_buying_cycle:
            if price <= last_buy_price * 0.95:
                shares = invest_per_step / price
                total_shares += shares
                total_invested += invest_per_step
                last_buy_price = price
                trades.append({'date': date, 'type': 'DCA Buy (-5%)', 'price': price, 'invested': invest_per_step})
            
            # 當信心指數回到 50 以下，視為該波段低點結束，重置循環
            if score < 50:
                is_buying_cycle = False
    
    # 計算最終價值
    final_price = df['Close'].iloc[-1]
    final_value = total_shares * final_price
    profit = final_value - total_invested
    return_pct = (profit / total_invested * 100) if total_invested > 0 else 0
    
    print(f"\n=== {name} 策略回測結果 ===")
    print(f"回測時間: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"總投入金額: ${total_invested:,.0f}")
    print(f"買入次數: {len(trades)} 次")
    print(f"最終資產市值: ${final_value:,.0f}")
    print(f"總獲利金額: ${profit:,.0f}")
    print(f"總報酬率: {return_pct:.2f}%")
    
    if len(trades) > 0:
        print("\n最近 3 次交易:")
        for t in trades[-3:]:
            print(f"  {t['date'].date()} | {t['type']} | 價格: {t['price']:.2f}")

def main():
    twii = load_data('twii_data.json')
    run_backtest(twii, "TWII (台股加權指數)")
    
    nasdaq = load_data('nasdaq_data.json')
    run_backtest(nasdaq, "NASDAQ (那斯達克)")

if __name__ == "__main__":
    main()
