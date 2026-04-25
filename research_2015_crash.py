import json

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_2015_crash(data):
    print("=== 2015 TWII Crash Analysis (April to August) ===")
    print(f"{'Date':<12} | {'Close':<6} | {'High':<6} | {'Low':<6} | {'VIX':<5} | {'RSI':<5} | {'Panic Score(VIX/RSI)':<10} | {'10-Day Drop %':<10} | {'Max Drawdown %':<10}")
    print("-" * 110)
    
    max_high = 0
    
    for i in range(120, len(data)):
        date = data[i][0]
        high = data[i][3]
        close = data[i][1]
        
        # Track max high since April
        if '2015-04-01' <= date <= '2015-08-31':
            if high > max_high:
                max_high = high
                
        if '2015-08-10' <= date <= '2015-08-31':
            low = data[i][2]
            vix = data[i][6]
            rsi = data[i][7]
            if rsi == 0: rsi = 1
            
            panic_score = (vix / rsi) * 60
            
            # 10-day drop speed
            close_10d_ago = data[i-10][1]
            drop_10d = ((close - close_10d_ago) / close_10d_ago) * 100
            
            # Max drawdown from peak
            mdd = ((max_high - low) / max_high) * 100
            
            print(f"{date:<12} | {close:<6.0f} | {high:<6.0f} | {low:<6.0f} | {vix:<5.1f} | {rsi:<5.1f} | {panic_score:<20.1f} | {drop_10d:<13.1f} | {mdd:.1f}%")

def main():
    tw = load_data('twii_data.json')
    analyze_2015_crash(tw)

if __name__ == "__main__":
    main()
